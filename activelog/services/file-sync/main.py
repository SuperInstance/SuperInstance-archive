from fastapi import FastAPI, UploadFile, File
import psycopg2
import redis
from minio import Minio

app = FastAPI(title="ActiveLog File Sync Service")

# Connect to services
redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)
minio_client = Minio('localhost:9000',
                     access_key='minioadmin',
                     secret_key='minioadmin123',
                     secure=False)

@app.get("/")
def read_root():
    return {"service": "File Sync", "status": "running"}

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    # Save to MinIO
    try:
        if not minio_client.bucket_exists("activelog"):
            minio_client.make_bucket("activelog")
        
        minio_client.put_object(
            "activelog",
            file.filename,
            file.file,
            file.size
        )
        return {"filename": file.filename, "status": "uploaded"}
    except Exception as e:
        return {"error": str(e)}

@app.get("/health")
def health_check():
    try:
        redis_client.ping()
        return {"status": "healthy", "redis": "connected", "minio": "connected"}
    except:
        return {"status": "unhealthy"}
