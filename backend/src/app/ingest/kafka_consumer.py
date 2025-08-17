import json
import logging
import threading
import time
from typing import Dict, Any
from kafka import KafkaConsumer
from ..config import settings
from ..ingest.normalizer import normalize_record
from ..ingest.embedder import embed_record
from ..ingest.upserter import upsert_record
from ..utils.logs import get_logger

logger = get_logger(__name__)

def process_message(msg: Dict[str, Any], topic: str) -> None:
    try:
        logger.info(f"Processing message from topic {topic}")
        rec_id, meta, text = normalize_record(msg)
        # We don't need to compute embeddings here anymore - QdrantStore handles it
        upsert_record(meta, text, topic)
        logger.info(f"Successfully processed message from topic {topic}")
    except Exception as e:
        logger.error(f"Error processing message from topic {topic}: {str(e)}")
        raise

def run_consumer(topic: str) -> None:
    logger.info(f"Starting consumer for topic: {topic}")
    
    while True:
        try:
            logger.info(f"Attempting to connect to Kafka for topic: {topic}")
            consumer = KafkaConsumer(
                topic,
                bootstrap_servers=settings.kafka_bootstrap,
                value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                auto_offset_reset='earliest',
                enable_auto_commit=True,
                group_id='chat_data_processor',
                max_poll_interval_ms=300000,
                max_poll_records=100
            )
            
            logger.info(f"Successfully connected to Kafka for topic: {topic}")
            try:
                for msg in consumer:
                    try:
                        logger.info(
                            f"Received message topic={msg.topic} partition={msg.partition} offset={msg.offset} "
                            f"key={getattr(msg, 'key', None)} size={len(msg.value) if msg.value else 0} bytes"
                        )
                        process_message(msg.value, topic)
                    except Exception as e:
                        logger.error(f"Failed to process message: {str(e)}")
                        continue
            except Exception as e:
                logger.error(f"Consumer error on topic {topic}: {str(e)}")
                raise
            finally:
                consumer.close()
                
        except Exception as e :
            logger.warning(f"Error while subscribing for topic {topic} : {e}. Retrying in 5 seconds...")
            time.sleep(5)
            continue
        except Exception as e:
            logger.error(f"Fatal error for consumer on topic {topic}: {str(e)}")
            raise

def start_consumers():
    topics = [settings.kafka_topic_financial, settings.kafka_topic_devices]
    threads = []
    for topic in topics:
        t = threading.Thread(target=run_consumer, args=(topic,), daemon=True)
        t.start()
        threads.append(t)
        logger.info(f"Started thread for topic: {topic}")

    # Keep the main thread alive while consumers run
    try:
        while True:
            for t in threads:
                t.join(timeout=1)
    except KeyboardInterrupt:
        logger.info("Shutting down consumers...")

if __name__ == "__main__":
    start_consumers()
