from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import JSONResponse
from src.services.user_service import update_user_profile
from src.services.insights_service import InsightsService
from src.services.daily_summary_service import DailySummaryService
from src.models.user import UserProfile
from src.models.insight import (
    InsightsRequest, InsightsResponse, InsightFeedback,
    AnomalyThresholdConfig, ServiceArea
)
from src.models.daily_summary import DailySummaryConfig, DailySummaryReport
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel

app = FastAPI(
    title="Incident Auto-Resolution System",
    description="Automatically resolves high-confidence incidents with comprehensive auditing",
    version="1.0.0"
)

insights_service = InsightsService()
daily_summary_service = DailySummaryService()

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

@app.post("/api/v1/daily-summary/configure", response_model=DailySummaryConfig, tags=["Daily Summary"])
async def configure_daily_summary(config: DailySummaryConfig):
    return await daily_summary_service.configure_summary(config)

@app.get("/api/v1/daily-summary/config/{user_id}", response_model=DailySummaryConfig, tags=["Daily Summary"])
async def get_daily_summary_config(user_id: str):
    config = await daily_summary_service.get_config(user_id)
    if not config:
        raise HTTPException(status_code=404, detail="Configuration not found")
    return config

@app.post("/api/v1/daily-summary/generate/{user_id}", response_model=DailySummaryReport, tags=["Daily Summary"])
async def generate_daily_summary(
    user_id: str,
    period_start: Optional[datetime] = None,
    period_end: Optional[datetime] = None
):
    try:
        return await daily_summary_service.generate_daily_summary(user_id, period_start, period_end)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
