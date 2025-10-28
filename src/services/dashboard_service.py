from typing import List, Dict

class DashboardService:
    """
    Service to manage user dashboard widgets including add, remove, and rearrange.
    """
    
    def __init__(self):
        # Initial dashboard layout
        self.dashboards: Dict[str, List[Dict]] = {"default": [{"type": "task_list"}, {"type": "calendar"}, {"type": "metrics"}, {"type": "announcements"}]}

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

    def create_dashboard(self, user_id: str) -> None:
        if user_id not in self.dashboards:
            self.dashboards[user_id] = self.dashboards["default"].copy()

    def save_dashboard_layout(self, user_id: str, layout: List[Dict]) -> None:
        """Save the current layout for the user's dashboard."""
        self.dashboards[user_id] = layout

    def sync_dashboard(self, user_id: str) -> List[Dict]:
        """ Simulate syncing the dashboard settings across devices (stub). """
        # Actual sync logic to be implemented
        return self.dashboards.get(user_id, self.dashboards["default"])