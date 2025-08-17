from pydantic import BaseModel, Field
from typing import Literal, Optional, List, Any, Dict

DataSource = Literal["financial", "devices", "auto"]
ResultMode = Literal["auto", "text", "table", "chart"]

class ChatRequest(BaseModel):
    source: DataSource
    message: str
    mode: ResultMode = "auto"  # desired response presentation
    top_k: int = 6              # number of chunks for RAG
    session_id: Optional[str] = "default_session"  # for conversation memory

class TableResponse(BaseModel):
    columns: List[str]
    rows: List[List[Any]]

class ChatResponse(BaseModel):
    mode: str
    text: Optional[str] = None
    table: Optional[TableResponse] = None
    chart_path: Optional[str] = None
    query_sql: Optional[str] = None

class IngestRecord(BaseModel):
    source: str
    data: dict

class SearchHit(BaseModel):
    score: float
    payload: dict
    id: str | int | None = None