from fastapi import APIRouter
from ..deps import sql
from ..ingest.upserter import upsert_record
from ..schemas import IngestRecord

router = APIRouter(prefix="/admin", tags=["admin"])

@router.get("/tables")
def list_tables():
    df = sql.query("SHOW TABLES")
    return df.to_dict(orient="records")

@router.post("/ingest")
def ingest(rec: IngestRecord):
    upsert_record(rec.data, str(rec.data), rec.source)
    return {"status": "accepted"}

@router.post("/ingest/financial")
def ingest_financial(rec: dict):
    upsert_record(rec, str(rec), 'financial')
    return {"status": "accepted"}

@router.post("/ingest/devices")
def ingest_devices(rec: dict):
    upsert_record(rec, str(rec), 'devices')
    return {"status": "accepted"}