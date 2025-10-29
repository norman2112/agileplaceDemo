from typing import List, Dict, Optional
from src.models.widget import (
    Widget, WidgetCreateRequest, WidgetTemplate, WidgetType,
    WidgetStatus, WidgetApprovalRequest, WidgetValidationResult
)
from datetime import datetime
import uuid


class WidgetService:
    
    def __init__(self):
        self.widgets: Dict[str, Widget] = {}
        self.templates: Dict[str, WidgetTemplate] = self._initialize_templates()
    
    def _initialize_templates(self) -> Dict[str, WidgetTemplate]:
        """Initialize common widget templates."""
        return {
            "incident_chart": WidgetTemplate(
                template_id="incident_chart",
                name="Incident Trend Chart",
                description="Line chart showing incident trends over time",
                widget_type=WidgetType.CHART,
                default_config={
                    "chart_type": "line",
                    "time_range": "30d",
                    "metrics": ["count", "resolution_time"]
                },
                schema={"type": "object", "properties": {"time_range": {"type": "string"}}}
            ),
            "resolution_metric": WidgetTemplate(
                template_id="resolution_metric",
                name="Resolution Rate Metric",
                description="Key metric showing auto-resolution success rate",
                widget_type=WidgetType.METRIC,
                default_config={
                    "metric": "resolution_rate",
                    "format": "percentage"
                },
                schema={"type": "object", "properties": {"metric": {"type": "string"}}}
            ),
            "service_table": WidgetTemplate(
                template_id="service_table",
                name="Service Area Table",
                description="Table view of service area performance",
                widget_type=WidgetType.TABLE,
                default_config={
                    "columns": ["service_area", "incidents", "resolution_rate"],
                    "sort_by": "incidents"
                },
                schema={"type": "object", "properties": {"columns": {"type": "array"}}}
            )
        }
    
    async def create_widget(self, creator_id: str, request: WidgetCreateRequest) -> Widget:
        """Create a new custom widget."""
        widget_id = str(uuid.uuid4())
        
        config = request.config
        if request.template_id and request.template_id in self.templates:
            template = self.templates[request.template_id]
            config = {**template.default_config, **request.config}
        
        widget = Widget(
            widget_id=widget_id,
            name=request.name,
            description=request.description,
            widget_type=request.widget_type,
            template_id=request.template_id,
            creator_id=creator_id,
            service_area=request.service_area,
            config=config,
            position=request.position or {"x": 0, "y": 0, "width": 4, "height": 3},
            status=WidgetStatus.DRAFT
        )
        
        self.widgets[widget_id] = widget
        return widget
    
    async def get_templates(self) -> List[WidgetTemplate]:
        """Get all available widget templates."""
        return list(self.templates.values())
    
    async def validate_widget(self, widget_id: str) -> WidgetValidationResult:
        """Validate widget configuration."""
        if widget_id not in self.widgets:
            return WidgetValidationResult(
                valid=False,
                errors=["Widget not found"]
            )
        
        widget = self.widgets[widget_id]
        errors = []
        warnings = []
        
        if not widget.name:
            errors.append("Widget name is required")
        
        if not widget.service_area:
            errors.append("Service area is required")
        
        if widget.template_id and widget.template_id not in self.templates:
            warnings.append("Template not found, using custom configuration")
        
        required_fields = ["widget_type", "creator_id"]
        for field in required_fields:
            if not getattr(widget, field):
                errors.append(f"Missing required field: {field}")
        
        return WidgetValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
    
    async def submit_for_approval(self, widget_id: str) -> Widget:
        """Submit widget for approval to publish to dashboard."""
        if widget_id not in self.widgets:
            raise ValueError("Widget not found")
        
        widget = self.widgets[widget_id]
        validation = await self.validate_widget(widget_id)
        
        if not validation.valid:
            raise ValueError(f"Widget validation failed: {', '.join(validation.errors)}")
        
        widget.status = WidgetStatus.PENDING_APPROVAL
        widget.updated_at = datetime.utcnow()
        return widget
    
    async def approve_widget(self, request: WidgetApprovalRequest) -> Widget:
        """Approve or reject a widget for publication."""
        if request.widget_id not in self.widgets:
            raise ValueError("Widget not found")
        
        widget = self.widgets[request.widget_id]
        
        if widget.status != WidgetStatus.PENDING_APPROVAL:
            raise ValueError("Widget is not pending approval")
        
        widget.status = WidgetStatus.APPROVED if request.approved else WidgetStatus.REJECTED
        widget.updated_at = datetime.utcnow()
        
        return widget
    
    async def get_widget(self, widget_id: str) -> Optional[Widget]:
        """Get widget by ID."""
        return self.widgets.get(widget_id)
    
    async def get_widgets_by_creator(self, creator_id: str) -> List[Widget]:
        """Get all widgets created by a specific user."""
        return [w for w in self.widgets.values() if w.creator_id == creator_id]
    
    async def get_widgets_by_status(self, status: WidgetStatus) -> List[Widget]:
        """Get all widgets with a specific status."""
        return [w for w in self.widgets.values() if w.status == status]
    
    async def update_widget_position(self, widget_id: str, position: Dict[str, int]) -> Widget:
        """Update widget position for drag-and-drop functionality."""
        if widget_id not in self.widgets:
            raise ValueError("Widget not found")
        
        widget = self.widgets[widget_id]
        widget.position = position
        widget.updated_at = datetime.utcnow()
        
        return widget
