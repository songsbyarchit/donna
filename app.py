import os
from dotenv import load_dotenv
import requests
from flask import Flask, request, jsonify
import logging
import subprocess
import json
from book_meeting import extract_meeting_details, schedule_meeting

def install_requirements():
    try:
        subprocess.check_call(["pip", "install", "-r", "requirements.txt"])
    except Exception as e:
        print(f"Error installing requirements: {e}")
        exit(1)

install_requirements()

load_dotenv()
WEBEX_BOT_TOKEN = os.getenv("WEBEX_BOT_TOKEN")
WEBEX_API_BASE = "https://webexapis.com/v1"

app = Flask(__name__)

HEADERS = {
    "Authorization": f"Bearer {WEBEX_BOT_TOKEN}",
    "Content-Type": "application/json"
}

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")

@app.route("/webhook", methods=["POST"])
def webhook():
    logging.debug("Webhook triggered")
    data = request.json
    logging.debug(f"Received data: {data}")
    if data.get("resource") == "messages" and data.get("event") == "created":
        message_id = data["data"]["id"]
        logging.debug(f"Processing message ID: {message_id}")
        process_message(message_id)
    return jsonify({"status": "ok"}), 200

def get_ngrok_url():
    try:
        output = subprocess.check_output(["curl", "http://127.0.0.1:4040/api/tunnels"], universal_newlines=True)
        tunnels = json.loads(output)
        return tunnels["tunnels"][0]["public_url"]
    except Exception as e:
        logging.error(f"Error fetching ngrok URL: {e}")
        return None

def process_message(message_id):
    try:
        logging.debug(f"Fetching message with ID: {message_id}")
        response = requests.get(f"{WEBEX_API_BASE}/messages/{message_id}", headers=HEADERS)
        message = response.json()
        logging.debug(f"Retrieved message: {message}")
        user_message = message.get("text").strip()
        logging.debug(f"User message: {user_message}")

        if "schedule a meeting" in user_message.lower():
            logging.debug("Scheduling meeting detected")
            meeting_details = extract_meeting_details(user_message)
            logging.debug(f"Extracted meeting details: {meeting_details}")

            if meeting_details:
                # Parse meeting details (assumes meeting_details is structured JSON or similar format)
                title = meeting_details.get("title", "Untitled Meeting")
                start_time = meeting_details.get("start_time")
                attendees = meeting_details.get("attendees", [])

                if start_time and attendees:
                    schedule_response = schedule_meeting(title, start_time, attendees)
                    send_message(
                        message["roomId"],
                        f"Meeting scheduled: {schedule_response.get('title')} at {schedule_response.get('start')}"
                    )
                else:
                    send_message(message["roomId"], "Sorry, I couldn't extract complete meeting details.")
            else:
                send_message(message["roomId"], "I couldn't understand the meeting details. Could you rephrase?")
        elif user_message.lower() == "hello":
            logging.debug("Matched 'hello', sending response")
            send_message(message["roomId"], "Hello there! I'm Donna, your virtual secretary. How can I assist you today?")
        else:
            logging.debug("Message did not match any command")
    except Exception as e:
        logging.error(f"Error processing message: {e}")

def send_message(room_id, text):
    try:
        logging.debug(f"Sending message to room ID: {room_id} with text: {text}")
        payload = {"roomId": room_id, "text": text}
        response = requests.post(f"{WEBEX_API_BASE}/messages", json=payload, headers=HEADERS)
        logging.debug(f"Response from Webex API: {response.status_code}, {response.text}")
    except Exception as e:
        logging.error(f"Error sending message: {e}")

def create_webhook():
    target_url = get_ngrok_url()
    if not target_url:
        logging.error("ngrok URL not found. Ensure ngrok is running.")
        return
    
    # Check if a webhook with the same targetUrl already exists
    response = requests.get(f"{WEBEX_API_BASE}/webhooks", headers=HEADERS)
    webhooks = response.json().get("items", [])
    for webhook in webhooks:
        if webhook["targetUrl"] == f"{target_url}/webhook":
            logging.debug("Webhook with this targetUrl already exists. Skipping creation.")
            return
    
    # Create the webhook
    payload = {
        "name": "DonnaBotWebhook",
        "targetUrl": f"{target_url}/webhook",
        "resource": "messages",
        "event": "created"
    }
    response = requests.post(f"{WEBEX_API_BASE}/webhooks", json=payload, headers=HEADERS)
    logging.debug(f"Webhook creation response: {response.json()}")

if __name__ == "__main__":
    create_webhook()
    app.run(port=5000, debug=True)