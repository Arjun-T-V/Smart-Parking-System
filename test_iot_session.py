
import os
import requests
from getpass import getpass

BASE_URL = "http://127.0.0.1:8000/api/iot/sensor-update/"

token = os.environ.get("IOT_DEVICE_TOKEN")
if not token:
    token = getpass("Enter your IoT device token: ")

response = requests.post(
    BASE_URL,
    headers={"Authorization": f"Bearer {token}"},
    json={
        "device_id": "ESP32_SLOT_002",
        "state": "CLEAR",
        "test_mode": True,
    },
    timeout=10,
)

print("HTTP status:", response.status_code)
print("Response:", response.text)
