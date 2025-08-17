from ..config import settings
from ..deps import vs, sql  # reuse singletons
import pandas as pd, asyncio

def upsert_record(meta: dict, text: str, topic: str):
    """Persist record into vector store (Qdrant) AND DuckDB warehouse.
    Reuses shared singleton objects for efficiency."""
    
    # Handle both legacy topic names and direct source names
    if topic == settings.kafka_topic_financial or topic == 'financial':
        source = 'financial'
    elif topic == settings.kafka_topic_devices or topic == 'devices':  
        source = 'devices'
    else:
        source = topic  # Direct source name
        
    # stable id
    meta['record_id'] = meta.get('order_id') or meta.get('device_id')
    
    # Upsert vector (async)
    asyncio.run(vs.upsert_texts(source, [text], [meta]))
    
    # Insert into DuckDB table for SQL aggregation
    try:
        if source == 'financial' and {'order_id','customer','amount','currency','ts','status'} <= set(meta.keys()):
            df = pd.DataFrame([{
                'order_id': meta['order_id'],
                'customer': meta['customer'],
                'amount': float(meta['amount']),
                'currency': meta['currency'],
                'ts': meta['ts'],
                'status': meta['status'],
            }])
            sql.insert_financial(df)
        elif source == 'devices' and {'device_id','status','uptime_minutes','location','ts'} <= set(meta.keys()):
            df = pd.DataFrame([{
                'device_id': meta['device_id'],
                'status': meta['status'],
                'uptime_minutes': float(meta['uptime_minutes']),
                'location': meta['location'],
                'ts': meta['ts'],
            }])
            sql.insert_devices(df)
    except Exception as e:
        print(f"[upsert_record] DuckDB insert failed: {e}")