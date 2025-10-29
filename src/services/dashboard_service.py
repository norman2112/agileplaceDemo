from typing import List, Dict, Any

class DashboardService:
    """
    Service to manage user dashboard widgets including add, remove, and rearrange.
    """

    def __init__(self):
        # Initial dashboard layout
        self.dashboards: Dict[str, List[Dict]] = {}
        self.responsive_layout_enabled = True

    def add_widget(self, user_id: str, widget_data: Dict) -> None:
        """Add a new widget to the user's dashboard."""
        if user_id not in self.dashboards:
            self.dashboards[user_id] = []
        self.dashboards[user_id].append(widget_data)

    def remove_widget(self, user_id: str, widget_id: str) -> None:
        """Remove a widget from the user's dashboard by ID."""
        if user_id in self.dashboards:
            self.dashboards[user_id] = [wd for wd in self.dashboards[user_id] if wd['id'] != widget_id]

    def rearrange_widget(self, user_id: str, widget_id: str, new_position: int) -> None:
        """Rearrange widget to a new position on the user's dashboard."""
        if user_id in self.dashboards:
            widgets = self.dashboards[user_id]
            widget = next((wd for wd in widgets if wd['id'] == widget_id), None)
            if widget:
                widgets.remove(widget)
                widgets.insert(new_position, widget)

    def get_dashboard(self, user_id: str) -> List[Dict]:
        """Get the user's current dashboard layout."""
        return self.dashboards.get(user_id, [])

    def set_layout(self, user_id: str, layout_type: str) -> None:
        """Set the dashboard layout type for the user."""
        if user_id in self.dashboards:
            for widget in self.dashboards[user_id]:
                widget['layout'] = layout_type

    def navigate_to_service_area(self, user_id: str, service_area: str) -> None:
        """Navigate to a specific service area for the user."""
        if user_id in self.dashboards:
            for widget in self.dashboards[user_id]:
                widget['service_area'] = service_area

    def configure_layout_options(self, layout_config: Dict[str, Any]) -> None:
        """Configure layout options like grid or list."""
        for user_id, widgets in self.dashboards.items():
            for widget in widgets:
                widget.update(layout_config)
