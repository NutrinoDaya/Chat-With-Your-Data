# Generate the contents of the file: data_generators/devices_generator.py

"""Generate realistic device telemetry and send via HTTP ingestion."""
import random, time, json, yaml, os, requests
from datetime import datetime, timezone

# Load config.yaml
with open('../config/config.yaml', 'r') as f:
    config = yaml.safe_load(f)

API_BASE = os.environ.get("API_BASE", "http://localhost:8001")
print(f"Sending devices data to {API_BASE}/admin/ingest/devices")

locations = ["DXB-01", "DXB-02", "AUH-01", "SHJ-01"]
statuses = ["ONLINE", "OFFLINE", "DEGRADED"]

def random_device_id():
    return f"dev-{random.randint(1000,1999)}"

while True:
    uptime = max(0, random.gauss(22*60, 60))  # around 22 hours in minutes
    payload = {
        "device_id": random_device_id(),
        "status": random.choices(statuses, weights=[0.85, 0.05, 0.10])[0],
        "uptime_minutes": round(uptime, 2),
        "location": random.choice(locations),
        "ts": datetime.now(timezone.utc).timestamp(),
    }
    try:
        r = requests.post(f"{API_BASE}/admin/ingest/devices", json=payload, timeout=5)
        r.raise_for_status()
    except Exception as e:
        print(f"Failed to POST device record: {e}")
    time.sleep(random.uniform(0.1, 0.6))