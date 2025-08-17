import os
from typing import Optional, Dict, Any
import yaml
from pydantic import BaseModel


class Settings(BaseModel):
    # LLM Settings
    provider: str
    model_name: str
    max_length: int
    temperature: float
        
    # Embeddings
    embeddings_model: str
    embedding_dimension: int
    
    # Vector Store
    qdrant_url: str
    qdrant_api_key: str
    qdrant_collection_financial: str
    qdrant_collection_devices: str
    
    # (Kafka removed) legacy optional fields
    kafka_bootstrap: Optional[str] = None
    kafka_topic_financial: Optional[str] = None
    kafka_topic_devices: Optional[str] = None
    
    # Database
    duckdb_path: str
    
    # Logging
    log_level: str

    # Raw nested sections (optional)
    vllm: Optional[Dict[str, Any]] = None
    lmcache: Optional[Dict[str, Any]] = None

    @classmethod
    def from_yaml(cls, yaml_path: Optional[str] = None) -> 'Settings':
        if yaml_path is None:
            yaml_path = os.path.join(os.path.dirname(__file__), '../../config/config.yaml')
        
        with open(yaml_path, 'r') as f:
            config_dict = yaml.safe_load(f)
        return cls(**config_dict)

settings = Settings.from_yaml()