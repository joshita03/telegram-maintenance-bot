import os
import requests
from typing import List, Dict, Any

GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
GEMINI_API_URL = 'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-pro:generateContent'

PROMPT_TEMPLATE = '''You are a maintenance task assistant. Extract all tasks from the following message. For each task, return:
- type: new_task, completed_task, or query
- description
- property
- cost (if mentioned)

If the message is in past tense (e.g., 'fixed', 'installed'), treat it as a completed_task. If it is in present or future tense (e.g., 'fix', 'install'), treat it as a new_task.

Message: "{{user_message}}"

Respond in JSON:
{
  "tasks": [
    {
      "type": "new_task",
      "description": "Fix leaking tap",
      "property": "Central",
      "cost": 50
    }
  ]
}
'''

def parse_message_with_gemini(user_message: str) -> Dict[str, Any]:
    if not GEMINI_API_KEY:
        raise Exception('Gemini API key not set')
    prompt = PROMPT_TEMPLATE.replace('{{user_message}}', user_message)
    headers = {'Content-Type': 'application/json'}
    params = {'key': GEMINI_API_KEY}
    data = {
        'contents': [
            {'parts': [{'text': prompt}]}
        ]
    }
    response = requests.post(GEMINI_API_URL, headers=headers, params=params, json=data)
    response.raise_for_status()
    # Gemini returns a text block, so we need to extract the JSON from the response
    try:
        text = response.json()['candidates'][0]['content']['parts'][0]['text']
        # Find the JSON block in the text
        import json, re
        match = re.search(r'\{[\s\S]*\}', text)
        if match:
            return json.loads(match.group(0))
        else:
            raise Exception('No JSON found in Gemini response')
    except Exception as e:
        raise Exception(f'Gemini parsing error: {e}') 