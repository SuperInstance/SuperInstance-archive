"""
AI Service Template
OpenAI integration with FastAPI
"""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import openai
import os
from typing import Optional, List

app = FastAPI(title="AI Service", version="1.0.0")

# Configure OpenAI
openai.api_key = os.getenv("OPENAI_API_KEY")

class AIRequest(BaseModel):
    query: str
    context: Optional[str] = None
    max_tokens: Optional[int] = 150

class AIResponse(BaseModel):
    response: str
    tokens_used: int
    model: str

class InsightRequest(BaseModel):
    data: dict
    analysis_type: str = "general"

class InsightResponse(BaseModel):
    insights: List[str]
    confidence: float
    recommendations: List[str]

@app.post("/insights", response_model=AIResponse)
async def generate_insights(request: AIRequest):
    try:
        response = openai.Completion.create(
            engine="text-davinci-003",
            prompt=f"Context: {request.context}

Query: {request.query}

Response:",
            max_tokens=request.max_tokens,
            temperature=0.7
        )
        
        return AIResponse(
            response=response.choices[0].text.strip(),
            tokens_used=response.usage.total_tokens,
            model="text-davinci-003"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI processing error: {str(e)}")

@app.post("/analyze", response_model=InsightResponse)
async def analyze_data(request: InsightRequest):
    # TODO: Implement data analysis logic
    return InsightResponse(
        insights=["Sample insight based on data analysis"],
        confidence=0.85,
        recommendations=["Implement recommendation logic"]
    )

@app.get("/models")
async def list_available_models():
    return {"models": ["openai", "ollama"], "default": "openai"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "ai", "openai_configured": bool(openai.api_key)}
