from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import JSONResponse
from src.services.user_service import update_user_profile
from src.services.insights_service import InsightsService
from src.services.widget_service import WidgetService
from src.services.audit_service import AuditService
from src.services.notification_service import NotificationService
from src.services.incident_detection_service import IncidentDetectionService
from src.models.user import UserProfile
from src.models.insight import (
    InsightsRequest, InsightsResponse, InsightFeedback,
    AnomalyThresholdConfig, ServiceArea
)
from src.models.widget import (
    Widget, WidgetCreateRequest, WidgetTemplate, WidgetStatus,
    WidgetApprovalRequest, WidgetValidationResult
)
from src.models.incident import Incident, IncidentSource
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

app = FastAPI(
    title="Incident Auto-Resolution System",
    description="Automatically resolves high-confidence incidents with comprehensive auditing",
    version="1.0.0"
)

insights_service = InsightsService()
widget_service = WidgetService()
audit_service = AuditService()
notification_service = NotificationService(audit_service)
incident_detection_service = IncidentDetectionService(audit_service, notification_service)

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


class IncidentDetectionRequest(BaseModel):
    """Request for incident detection from a data source."""
    source: IncidentSource = Field(..., description="Data source type")
    data: Dict[str, Any] = Field(..., description="Raw data from the source")
    notify_teams: Optional[List[str]] = Field(None, description="Team IDs to notify")


class BatchDetectionRequest(BaseModel):
    """Batch detection request for multiple data sources."""
    items: List[IncidentDetectionRequest] = Field(..., description="List of detection requests")


@app.post("/api/v1/incidents/detect", response_model=Optional[Incident], tags=["Incident Detection"])
async def detect_incident(request: IncidentDetectionRequest):
    """
    Analyze data from a source and detect/classify any incidents.
    
    Returns the created incident if anomaly detected, None otherwise.
    """
    incident = await incident_detection_service.detect_and_classify(
        source=request.source,
        data=request.data,
        notify_teams=request.notify_teams
    )
    return incident


@app.post("/api/v1/incidents/detect/batch", response_model=List[Incident], tags=["Incident Detection"])
async def detect_incidents_batch(request: BatchDetectionRequest):
    """
    Process batch of data from multiple sources for incident detection.
    
    Returns list of created incidents for any anomalies detected.
    """
    data_batch = [(item.source, item.data) for item in request.items]
    return await incident_detection_service.process_batch(data_batch)


@app.get("/api/v1/incidents/sources", response_model=List[str], tags=["Incident Detection"])
async def get_monitored_sources():
    """Get list of monitored data sources."""
    return [source.value for source in IncidentSource]
