import os
import requests
from dotenv import load_dotenv
import openai
import json

load_dotenv()
WEBEX_API_BASE = "https://webexapis.com/v1"
WEBEX_BOT_TOKEN = os.getenv("WEBEX_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

openai.api_key = OPENAI_API_KEY

HEADERS = {
    "Authorization": f"Bearer {WEBEX_BOT_TOKEN}",
    "Content-Type": "application/json"
}

def extract_meeting_details(user_message):
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an assistant that extracts meeting details from user text. Respond in JSON format with keys: title, start_time, and attendees."},
                {"role": "user", "content": user_message}
            ]
        )
        details = response['choices'][0]['message']['content']
        return json.loads(details)  # Assuming the response is formatted as JSON
    except Exception as e:
        print(f"Error with OpenAI API: {e}")
        return None

def schedule_meeting(title, start_time, attendees):
    try:
        payload = {
            "title": title,
            "start": start_time,
            "invitees": [{"email": email} for email in attendees]
        }
        response = requests.post(f"{WEBEX_API_BASE}/meetings", json=payload, headers=HEADERS)
        return response.json()
    except Exception as e:
        print(f"Error scheduling meeting: {e}")
        return None