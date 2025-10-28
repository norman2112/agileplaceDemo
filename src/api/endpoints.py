from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import JSONResponse
from src.services.user_service import update_user_profile
from src.services.insights_service import InsightsService
from src.models.user import UserProfile
from src.models.insight import (
    InsightsRequest, InsightsResponse, InsightFeedback,
    AnomalyThresholdConfig, ServiceArea
)
from typing import Optional, List
from pydantic import BaseModel

app = FastAPI(
    title="Incident Auto-Resolution System",
    description="Automatically resolves high-confidence incidents with comprehensive auditing",
    version="1.0.0"
)

insights_service = InsightsService()

class UserLogin(BaseModel):
    email: str
    password: str

@app.post("/api/v1/auth/login", tags=["Auth"])
async def login(user_login: UserLogin):
    # Mock authentication, to be implemented
    if user_login.email == "test@example.com" and user_login.password == "password":
        return {"access_token": "dummy_token", "token_type": "bearer"}
    else:
        raise HTTPException(status_code=401, detail="Invalid credentials")

@app.put("/api/v1/user/profile", response_model=UserProfile, tags=["User"])
async def update_profile(user_id: str, profile: UserProfile, service=Depends(update_user_profile)):
    if user_id != profile.user_id:
        raise HTTPException(status_code=400, detail="User ID mismatch")
    return await service(user_id, profile)

@app.post("/api/v1/insights/generate", response_model=InsightsResponse, tags=["Insights"])
async def generate_insights(request: InsightsRequest):
    return await insights_service.generate_insights(request)

@app.post("/api/v1/insights/feedback", response_model=InsightFeedback, tags=["Insights"])
async def submit_insight_feedback(feedback: InsightFeedback):
    return await insights_service.submit_feedback(feedback)

@app.post("/api/v1/insights/thresholds", response_model=AnomalyThresholdConfig, tags=["Insights"])
async def configure_anomaly_threshold(config: AnomalyThresholdConfig):
    return await insights_service.configure_threshold(config)

@app.get("/api/v1/insights/thresholds", response_model=List[AnomalyThresholdConfig], tags=["Insights"])
async def get_anomaly_thresholds(service_area: Optional[ServiceArea] = None):
    return await insights_service.get_thresholds(service_area)
