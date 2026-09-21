from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import httpx
import json

app = FastAPI(title="ActiveLog API Gateway", version="1.0.0")

# Service registry
SERVICES = {
    "file-sync": "http://localhost:8000",
    "ai-orchestrator": "http://localhost:8001",
}

@app.get("/")
async def root():
    return {
        "gateway": "ActiveLog API Gateway",
        "version": "1.0.0",
        "services": list(SERVICES.keys())
    }

@app.get("/health")
async def health_check():
    health_status = {}
    async with httpx.AsyncClient() as client:
        for service_name, service_url in SERVICES.items():
            try:
                response = await client.get(f"{service_url}/health", timeout=2.0)
                health_status[service_name] = response.json()
            except:
                health_status[service_name] = {"status": "unreachable"}
    
    return health_status

@app.api_route("/{service}/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy(service: str, path: str, request: Request):
    if service not in SERVICES:
        return JSONResponse(
            status_code=404,
            content={"error": f"Service {service} not found"}
        )
    
    service_url = SERVICES[service]
    url = f"{service_url}/{path}"
    
    async with httpx.AsyncClient() as client:
        try:
            # Forward the request
            response = await client.request(
                method=request.method,
                url=url,
                headers=request.headers,
                content=await request.body(),
                timeout=30.0
            )
            return JSONResponse(
                status_code=response.status_code,
                content=response.json() if response.headers.get("content-type", "").startswith("application/json") else response.text
            )
        except Exception as e:
            return JSONResponse(
                status_code=500,
                content={"error": str(e)}
            )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
