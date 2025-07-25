import os
import requests
from typing import Any, Dict

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_API_URL = f'https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}'

def send_message(chat_id: int, text: str, reply_to_message_id: int = None) -> Dict[str, Any]:
    url = f'{TELEGRAM_API_URL}/sendMessage'
    payload = {
        'chat_id': chat_id,
        'text': text,
        'parse_mode': 'Markdown',
        'disable_web_page_preview': True
    }
    if reply_to_message_id:
        payload['reply_to_message_id'] = reply_to_message_id
    response = requests.post(url, json=payload)
    response.raise_for_status()
    return response.json()

def extract_message_info(update: Dict[str, Any]) -> Dict[str, Any]:
    # Handles both message and edited_message
    message = update.get('message') or update.get('edited_message')
    if not message:
        return {}
    user = message['from']
    user_name = user.get('username')
    if not user_name:
        # Fallback to first_name + last_name if username not present
        user_name = (user.get('first_name', '') + ' ' + user.get('last_name', '')).strip() or None
    return {
        'chat_id': message['chat']['id'],
        'user_id': str(user['id']),
        'user_name': user_name,
        'text': message.get('text', ''),
        'message_id': message['message_id']
    } 