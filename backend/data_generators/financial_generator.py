# financial_generator.py

import random, time, json, yaml, os, sys, requests
from datetime import datetime, timezone
from pathlib import Path

# Get the script's directory
script_dir = Path(__file__).parent.absolute()
config_path = script_dir.parent / 'config' / 'config.yaml'

# Load config.yaml
with open(config_path, 'r') as f:
    config = yaml.safe_load(f)

API_BASE = os.environ.get("API_BASE", "http://localhost:8001")
print(f"Sending financial data to {API_BASE}/admin/ingest/financial")

customers = ["Acme LLC", "Globex", "Soylent", "Initech", "Umbrella", "Wayne"]
currencies = ["USD", "EUR", "AED", "SAR"]

order_id = int(time.time())

while True:
    amount = round(random.uniform(50, 5000), 2)
    payload = {
        "order_id": order_id,
        "customer": random.choice(customers),
        "amount": amount,
        "currency": random.choice(currencies),
        "ts": datetime.now(timezone.utc).isoformat(),
        "status": random.choice(["PAID", "PENDING", "CANCELLED", "REFUNDED"]),
    }
    try:
        r = requests.post(f"{API_BASE}/admin/ingest/financial", json=payload, timeout=5)
        r.raise_for_status()
    except Exception as e:
        print(f"Failed to POST financial record: {e}")
    order_id += 1
    print(f"Sent order {order_id}")
    time.sleep(random.uniform(0.2, 1.2))