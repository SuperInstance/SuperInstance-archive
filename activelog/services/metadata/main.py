from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn

from database import init_db
from routes import metadata_router, tags_router, search_router, embeddings_router, relationships_router, batch_router
from elasticsearch_client import init_elasticsearch

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    await init_elasticsearch()
    yield

app = FastAPI(
    title="ActiveLog Metadata Service",
    description="Metadata management with vector embeddings and full-text search",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8088"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(metadata_router, prefix="/metadata", tags=["metadata"])
app.include_router(tags_router, prefix="/tags", tags=["tags"])
app.include_router(search_router, prefix="/search", tags=["search"])
app.include_router(embeddings_router, prefix="/embeddings", tags=["embeddings"])
app.include_router(relationships_router, prefix="/relationships", tags=["relationships"])
app.include_router(batch_router, prefix="/batch", tags=["batch"])

@app.get("/")
def root():
    return {"service": "ActiveLog Metadata Service", "status": "running"}

@app.get("/health")
async def health_check():
    from elasticsearch_client import es_client
    from database import get_db
    
    health_status = {"status": "healthy", "components": {}}
    
    try:
        conn = get_db()
        conn.close()
        health_status["components"]["database"] = "connected"
    except Exception as e:
        health_status["components"]["database"] = f"error: {str(e)}"
        health_status["status"] = "unhealthy"
    
    try:
        await es_client.ping()
        health_status["components"]["elasticsearch"] = "connected"
    except Exception as e:
        health_status["components"]["elasticsearch"] = f"error: {str(e)}"
        health_status["status"] = "unhealthy"
    
    return health_status

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8003)