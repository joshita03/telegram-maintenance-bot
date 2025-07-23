import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from app.gemini import parse_message_with_gemini
from app.db import add_task, get_tasks, complete_task, get_summary, check_duplicate
from app.telegram import send_message, extract_message_info
from datetime import datetime, timedelta
from flask_apscheduler import APScheduler
from app.utils import format_task_list, format_summary
import re

load_dotenv()

app = Flask(__name__)
CORS(app)

TELEGRAM_GROUP_ID = int(os.getenv('TELEGRAM_GROUP_ID', '0'))

scheduler = APScheduler()
scheduler.init_app(app)
scheduler.start()

def normalize_description(desc):
    # Remove common tense suffixes, punctuation, and lowercase
    desc = desc.lower()
    desc = re.sub(r"\b(fix|fixed|install|installed|repair|repaired|replace|replaced|paint|painted|clean|cleaned|mark|marked|complete|completed|finish|finished)\b", "", desc)
    desc = re.sub(r"[^a-z0-9 ]", "", desc)
    desc = re.sub(r"\s+", " ", desc).strip()
    return desc

@scheduler.task('cron', id='daily_pending', hour=9, minute=0)
def daily_pending_tasks():
    pending = get_tasks(status='pending')
    msg = '*Daily Pending Tasks*\n' + format_task_list(pending)
    if TELEGRAM_GROUP_ID:
        send_message(TELEGRAM_GROUP_ID, msg)

@scheduler.task('cron', id='weekly_summary', day_of_week='sun', hour=18, minute=0)
def weekly_completed_summary():
    now = datetime.utcnow()
    start = (now - timedelta(days=now.weekday()+1)).replace(hour=0, minute=0, second=0, microsecond=0)
    end = now
    summary = get_summary(start.isoformat(), end.isoformat())
    msg = '*Weekly Completed Tasks*\n' + format_summary(summary)
    if TELEGRAM_GROUP_ID:
        send_message(TELEGRAM_GROUP_ID, msg)

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok'})

@app.route('/webhook', methods=['POST'])
def webhook():
    update = request.json
    info = extract_message_info(update)
    if not info or not info['text']:
        return jsonify({'ok': True})
    chat_id = info['chat_id']
    user_id = info['user_id']
    text = info['text']
    message_id = info['message_id']
    try:
        gemini_result = parse_message_with_gemini(text)
        tasks = gemini_result.get('tasks', [])
        responses = []
        for task in tasks:
            ttype = task.get('type')
            desc = task.get('description')
            prop = task.get('property')
            cost = task.get('cost')
            if ttype == 'new_task':
                # Prevent adding a new pending task if a similar completed or pending task exists
                pending_tasks = get_tasks(status='pending', property=prop)
                completed_tasks = get_tasks(status='completed', property=prop)
                norm_desc = normalize_description(desc)
                pending_match = next((t for t in pending_tasks if normalize_description(t['description']) == norm_desc), None)
                completed_match = next((t for t in completed_tasks if normalize_description(t['description']) == norm_desc), None)
                if pending_match:
                    responses.append(f"Duplicate: '{desc}' for {prop} already pending.")
                elif completed_match:
                    responses.append(f"Task '{desc}' for {prop} is already completed.")
                else:
                    add_task({
                        'telegram_user_id': user_id,
                        'property': prop,
                        'description': desc,
                        'cost': cost,
                        'status': 'pending'
                    })
                    responses.append(f"Added: '{desc}' for {prop} (cost: {cost})")
            elif ttype == 'completed_task':
                # Use normalized description for matching
                pending_tasks = get_tasks(status='pending', property=prop)
                completed_tasks = get_tasks(status='completed', property=prop)
                norm_desc = normalize_description(desc)
                pending_match = next((t for t in pending_tasks if normalize_description(t['description']) == norm_desc), None)
                completed_match = next((t for t in completed_tasks if normalize_description(t['description']) == norm_desc), None)
                if pending_match:
                    result = complete_task(pending_match['description'], prop)
                    if getattr(result, 'data', None):
                        responses.append(f"Marked completed: '{pending_match['description']}' for {prop}")
                    else:
                        responses.append(f"Could not mark as completed: '{pending_match['description']}' for {prop}")
                elif completed_match:
                    responses.append(f"Task '{desc}' for {prop} is already completed.")
                else:
                    # If no matching task, add as completed
                    add_task({
                        'telegram_user_id': user_id,
                        'property': prop,
                        'description': desc,
                        'cost': cost,
                        'status': 'completed',
                        'completed_at': datetime.utcnow().isoformat()
                    })
                    responses.append(f"Added and marked completed: '{desc}' for {prop} (cost: {cost})")
            elif ttype == 'query':
                query_text = desc.lower()
                if any(word in query_text for word in ['pending', 'yet', 'to be done', 'incomplete', 'open']):
                    pending = get_tasks(status='pending')
                    if pending:
                        responses.append("Pending tasks:\n" + '\n'.join([f"- {t['description']} ({t['property']}) [cost: {t.get('cost', 'N/A')}]" for t in pending]))
                    else:
                        responses.append("No pending tasks.")
                elif any(word in query_text for word in ['completed', 'done', 'finished', 'closed']):
                    completed = get_tasks(status='completed')
                    if completed:
                        responses.append("Completed tasks:\n" + '\n'.join([f"- {t['description']} ({t['property']}) [cost: {t.get('cost', 'N/A')}] on {t.get('completed_at', 'N/A')}" for t in completed]))
                    else:
                        responses.append("No completed tasks.")
                elif 'central' in query_text:
                    completed = get_tasks(status='completed', property='Central')
                    if completed:
                        responses.append("Completed for Central:\n" + '\n'.join([f"- {t['description']} (cost: {t['cost']})" for t in completed]))
                    else:
                        responses.append("No completed tasks for Central.")
                else:
                    responses.append("Query not recognized.")
            else:
                responses.append("Task type not recognized.")
        reply = '\n'.join(responses) if responses else 'No tasks found.'
        send_message(chat_id, reply, reply_to_message_id=message_id)
    except Exception as e:
        send_message(chat_id, f"Error: {e}", reply_to_message_id=message_id)
    return jsonify({'ok': True})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 5000))) 