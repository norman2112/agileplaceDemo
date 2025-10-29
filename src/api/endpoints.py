from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import JSONResponse
from src.services.user_service import update_user_profile
from src.services.insights_service import InsightsService
from src.services.widget_service import WidgetService
from src.models.user import UserProfile
from src.models.insight import (
    InsightsRequest, InsightsResponse, InsightFeedback,
    AnomalyThresholdConfig, ServiceArea
)
from src.models.widget import (
    Widget, WidgetCreateRequest, WidgetTemplate, WidgetStatus,
    WidgetApprovalRequest, WidgetValidationResult
)
from typing import Optional, List, Dict
from pydantic import BaseModel

app = FastAPI(
    title="Incident Auto-Resolution System",
    description="Automatically resolves high-confidence incidents with comprehensive auditing",
    version="1.0.0"
)

insights_service = InsightsService()
widget_service = WidgetService()

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

@app.post("/api/v1/widgets", response_model=Widget, tags=["Widgets"])
async def create_widget(creator_id: str, request: WidgetCreateRequest):
    return await widget_service.create_widget(creator_id, request)

@app.get("/api/v1/widgets/templates", response_model=List[WidgetTemplate], tags=["Widgets"])
async def get_widget_templates():
    return await widget_service.get_templates()

@app.get("/api/v1/widgets/{widget_id}", response_model=Widget, tags=["Widgets"])
async def get_widget(widget_id: str):
    widget = await widget_service.get_widget(widget_id)
    if not widget:
        raise HTTPException(status_code=404, detail="Widget not found")
    return widget

@app.get("/api/v1/widgets/creator/{creator_id}", response_model=List[Widget], tags=["Widgets"])
async def get_widgets_by_creator(creator_id: str):
    return await widget_service.get_widgets_by_creator(creator_id)

@app.get("/api/v1/widgets/status/{status}", response_model=List[Widget], tags=["Widgets"])
async def get_widgets_by_status(status: WidgetStatus):
    return await widget_service.get_widgets_by_status(status)

@app.post("/api/v1/widgets/{widget_id}/validate", response_model=WidgetValidationResult, tags=["Widgets"])
async def validate_widget(widget_id: str):
    return await widget_service.validate_widget(widget_id)

@app.post("/api/v1/widgets/{widget_id}/submit", response_model=Widget, tags=["Widgets"])
async def submit_widget_for_approval(widget_id: str):
    try:
        return await widget_service.submit_for_approval(widget_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/v1/widgets/approve", response_model=Widget, tags=["Widgets"])
async def approve_widget(request: WidgetApprovalRequest):
    try:
        return await widget_service.approve_widget(request)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.put("/api/v1/widgets/{widget_id}/position", response_model=Widget, tags=["Widgets"])
async def update_widget_position(widget_id: str, position: Dict[str, int]):
    try:
        return await widget_service.update_widget_position(widget_id, position)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
