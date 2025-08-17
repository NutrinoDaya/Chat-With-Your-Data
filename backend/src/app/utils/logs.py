from pydantic import BaseModel
import os

LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")


import logging
def get_logger(name=None):
    logger = logging.getLogger(name or "chat-data-etl")
    if not logger.hasHandlers():
        handler = logging.StreamHandler()
        formatter = logging.Formatter('[%(asctime)s] %(levelname)s %(name)s: %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    logger.setLevel(LOG_LEVEL or "INFO")
    return logger