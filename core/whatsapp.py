import os
import requests
from typing import Optional

WHATSAPP_ACCESS_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN", "")
WHATSAPP_PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")
WHATSAPP_API_VERSION = os.getenv("WHATSAPP_API_VERSION", "v23.0")


def normalize_sa_phone(phone: str) -> str:
    phone = (phone or "").strip().replace(" ", "").replace("-", "")
    if phone.startswith("+"):
        phone = phone[1:]

    # أمثلة:
    # 05xxxxxxxx -> 9665xxxxxxxx
    # 5xxxxxxxx -> 9665xxxxxxxx
    if phone.startswith("05"):
        return "966" + phone[1:]
    if phone.startswith("5") and len(phone) == 9:
        return "966" + phone
    return phone


def send_whatsapp_text(to_phone: str, body: str) -> dict:
    if not WHATSAPP_ACCESS_TOKEN:
        return {"ok": False, "error": "WHATSAPP_ACCESS_TOKEN missing"}

    if not WHATSAPP_PHONE_NUMBER_ID:
        return {"ok": False, "error": "WHATSAPP_PHONE_NUMBER_ID missing"}

    to_phone = normalize_sa_phone(to_phone)

    url = f"https://graph.facebook.com/{WHATSAPP_API_VERSION}/{WHATSAPP_PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": to_phone,
        "type": "text",
        "text": {"body": body},
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        data = response.json()
        return {
            "ok": response.ok,
            "status_code": response.status_code,
            "data": data,
        }
    except requests.RequestException as exc:
        return {"ok": False, "error": str(exc)}
