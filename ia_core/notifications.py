import os
import logging
import requests
from typing import Optional

# Configuration for notification backends
IFTTT_EVENT = os.environ.get("IFTTT_EVENT")
IFTTT_KEY = os.environ.get("IFTTT_KEY")
# NOTE: Read PUSHBULLET_TOKEN and NOTIFICATION_BACKEND at call time so changes
# in environment or runtime configuration take effect without restarting the app.


def send_ifttt(title: str, body: str) -> bool:
    """Send a webhook to IFTTT Maker to trigger an applet."""
    if not IFTTT_EVENT or not IFTTT_KEY:
        logging.debug("IFTTT not configured (IFTTT_EVENT/IFTTT_KEY missing).")
        return False
    url = f"https://maker.ifttt.com/trigger/{IFTTT_EVENT}/with/key/{IFTTT_KEY}"
    payload = {"value1": title, "value2": body}
    try:
        r = requests.post(url, json=payload, timeout=8)
        r.raise_for_status()
        return True
    except requests.RequestException as e:
        logging.error(f"Error sending IFTTT webhook: {e} (status={getattr(e.response, 'status_code', None)})")
        return False


def send_pushbullet(title: str, body: str) -> bool:
    """Send a note push via Pushbullet API using an Access Token."""
    token = os.environ.get("PUSHBULLET_TOKEN")
    if not token:
        logging.debug("Pushbullet not configured (PUSHBULLET_TOKEN missing).")
        return False
    url = "https://api.pushbullet.com/v2/pushes"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    payload = {"type": "note", "title": title, "body": body}
    try:
        r = requests.post(url, json=payload, headers=headers, timeout=8)
        r.raise_for_status()
        return True
    except requests.RequestException as e:
        logging.error(f"Error sending Pushbullet push: {e}")
        return False


def send_notification(chat_id: Optional[str], text: str) -> bool:
    """Wrapper to send notifications using the configured backend.

    `chat_id` is accepted for compatibility but only Telegram would use it.
    """
    title = "MindCare Alerta"
    body = text
    # Only use the backend explicitly configured by the environment variable.
    # This avoids silently sending alerts to Pushbullet when IFTTT is not configured.
    backend = os.environ.get("NOTIFICATION_BACKEND", "").strip().lower()
    if not backend:
        logging.warning("No NOTIFICATION_BACKEND configured — not sending notification.")
        return False

    if backend == "ifttt":
        return send_ifttt(title, body)

    if backend == "pushbullet":
        return send_pushbullet(title, body)

    logging.error(f"Unknown NOTIFICATION_BACKEND '{backend}' — not sending notification.")
    return False
