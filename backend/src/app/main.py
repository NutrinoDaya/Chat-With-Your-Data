from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from .routes import chat, admin
from .config import settings
import os

# Initialize FastAPI app
app = FastAPI(title="Chat With Your Data")

# Create charts directory if it doesn't exist
os.makedirs("./charts", exist_ok=True)

# Mount static files for chart images
app.mount("/static/charts", StaticFiles(directory="./charts"), name="charts")

# Add startup event to check services and ingest schemas
@app.on_event("startup")
async def startup_event():
    from .deps import check_services
    from .services.schema_ingestion import ingest_schemas_and_patterns
    
    # Check basic services first
    await check_services()
    
    # Ingest schema documentation and query patterns
    try:
        await ingest_schemas_and_patterns()
        print("[startup] Schema ingestion completed successfully")
    except Exception as e:
        print(f"[startup] Schema ingestion failed: {e}")
        # Don't block startup, but log the error


# Routers already define their own prefixes; avoid double prefixing
app.include_router(chat.router)
app.include_router(admin.router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)