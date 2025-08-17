from __future__ import annotations
from typing import Dict, Any, Tuple

# Convert raw Kafka payloads to canonical rows (one record = one chunk)

def normalize_financial(payload: Dict[str, Any]) -> Tuple[str, dict, str]:
    text = (
        f"Order {payload['order_id']} for {payload['customer']} amount {payload['amount']} "
        f"{payload['currency']} status {payload['status']} at {payload['ts']}"
    )
    meta = {**payload, "chunk_type": "financial"}
    return str(payload["order_id"]), meta, text

def normalize_device(payload: Dict[str, Any]) -> Tuple[str, dict, str]:
    text = (
        f"Device {payload['device_id']} status {payload['status']} uptime_minutes {payload['uptime_minutes']} "
        f"location {payload['location']} at {payload['ts']}"
    )
    meta = {**payload, "chunk_type": "device"}
    return f"{payload['device_id']}-{int(payload['ts'])}", meta, text

# Dispatcher for ETL
def normalize_record(payload: dict) -> tuple:
    if 'order_id' in payload:
        return normalize_financial(payload)
    elif 'device_id' in payload:
        return normalize_device(payload)
    else:
        raise ValueError('Unknown record type for normalization')