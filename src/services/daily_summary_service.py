import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from uuid import uuid4
import random

from src.models.daily_summary import (
    DailySummaryConfig, DailySummaryReport, SeverityBreakdown,
    CriticalIncidentHighlight, ExternalSystem, DeliveryFormat
)
from src.models.incident import IncidentPriority
from src.services.notification_service import NotificationService

logger = logging.getLogger(__name__)


class ExternalSystemConnector:
    
    def __init__(self, system: ExternalSystem):
        self.system = system
    
    async def fetch_incidents(self, start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
        logger.info(f"Fetching incidents from {self.system.value} for period {start_date} to {end_date}")
        
        incidents = []
        incident_count = random.randint(5, 25)
        
        for i in range(incident_count):
            priority = random.choice([p.value for p in IncidentPriority])
            incidents.append({
                "incident_id": f"{self.system.value.upper()}-{random.randint(1000, 9999)}",
                "title": f"Sample incident {i+1} from {self.system.value}",
                "severity": priority,
                "system": self.system.value,
                "created_at": start_date + timedelta(hours=random.randint(0, 23)),
                "status": random.choice(["open", "in_progress", "closed"])
            })
        
        return incidents


class DailySummaryService:
    
    def __init__(self, notification_service: Optional[NotificationService] = None):
        self.notification_service = notification_service
        self._configs: Dict[str, DailySummaryConfig] = {}
        self._system_connectors: Dict[ExternalSystem, ExternalSystemConnector] = {}
    
    def _get_connector(self, system: ExternalSystem) -> ExternalSystemConnector:
        if system not in self._system_connectors:
            self._system_connectors[system] = ExternalSystemConnector(system)
        return self._system_connectors[system]
    
    async def configure_summary(self, config: DailySummaryConfig) -> DailySummaryConfig:
        self._configs[config.user_id] = config
        logger.info(f"Daily summary configured for user {config.user_id}")
        return config
    
    async def get_config(self, user_id: str) -> Optional[DailySummaryConfig]:
        return self._configs.get(user_id)
    
    async def generate_daily_summary(
        self,
        user_id: str,
        period_start: Optional[datetime] = None,
        period_end: Optional[datetime] = None
    ) -> DailySummaryReport:
        config = self._configs.get(user_id)
        
        if not config or not config.enabled:
            raise ValueError(f"Daily summary not configured or disabled for user {user_id}")
        
        if not period_end:
            period_end = datetime.utcnow()
        if not period_start:
            period_start = period_end - timedelta(days=1)
        
        all_incidents = []
        for system in config.systems:
            connector = self._get_connector(system)
            incidents = await connector.fetch_incidents(period_start, period_end)
            all_incidents.extend(incidents)
        
        severity_breakdown = self._calculate_severity_breakdown(all_incidents)
        critical_incidents = self._identify_critical_incidents(all_incidents)
        trend_analysis = None
        
        if config.include_trend_analysis:
            trend_analysis = await self._analyze_trends(all_incidents, config.systems)
        
        if config.critical_incidents_only:
            filtered_count = len([i for i in all_incidents if i["severity"] in ["critical", "high"]])
        else:
            filtered_count = len(all_incidents)
        
        summary_text = self._generate_summary_text(
            filtered_count,
            severity_breakdown,
            critical_incidents,
            trend_analysis
        )
        
        report = DailySummaryReport(
            report_id=str(uuid4()),
            period_start=period_start,
            period_end=period_end,
            total_incidents=filtered_count,
            severity_breakdown=severity_breakdown,
            trend_analysis=trend_analysis,
            critical_incidents=critical_incidents,
            systems_included=config.systems,
            summary_text=summary_text
        )
        
        if config.delivery_format in [DeliveryFormat.EMAIL, DeliveryFormat.BOTH]:
            await self._send_email_summary(config, report)
        
        logger.info(f"Generated daily summary {report.report_id} for user {user_id}")
        return report
    
    def _calculate_severity_breakdown(self, incidents: List[Dict[str, Any]]) -> SeverityBreakdown:
        breakdown = SeverityBreakdown()
        
        for incident in incidents:
            severity = incident.get("severity", "low")
            if severity == "critical":
                breakdown.critical += 1
            elif severity == "high":
                breakdown.high += 1
            elif severity == "medium":
                breakdown.medium += 1
            else:
                breakdown.low += 1
        
        return breakdown
    
    def _identify_critical_incidents(
        self,
        incidents: List[Dict[str, Any]]
    ) -> List[CriticalIncidentHighlight]:
        critical = []
        
        for incident in incidents:
            if incident.get("severity") in ["critical", "high"]:
                reason = self._determine_critical_reason(incident)
                critical.append(CriticalIncidentHighlight(
                    incident_id=incident["incident_id"],
                    title=incident["title"],
                    severity=incident["severity"],
                    system=incident["system"],
                    created_at=incident["created_at"],
                    reason=reason
                ))
        
        critical.sort(key=lambda x: (x.severity == "critical", x.created_at), reverse=True)
        return critical[:10]
    
    def _determine_critical_reason(self, incident: Dict[str, Any]) -> str:
        severity = incident.get("severity")
        status = incident.get("status", "open")
        
        if severity == "critical" and status == "open":
            return "Critical severity incident still open"
        elif severity == "critical":
            return "Critical severity incident"
        elif severity == "high" and status == "open":
            return "High severity incident requiring attention"
        else:
            return "Escalated incident"
    
    async def _analyze_trends(
        self,
        incidents: List[Dict[str, Any]],
        systems: List[ExternalSystem]
    ) -> str:
        if not incidents:
            return "No incidents to analyze."
        
        total = len(incidents)
        critical_count = len([i for i in incidents if i.get("severity") == "critical"])
        open_count = len([i for i in incidents if i.get("status") == "open"])
        
        trend_parts = [
            f"Analyzed {total} incidents across {len(systems)} systems.",
        ]
        
        if critical_count > 0:
            trend_parts.append(f"{critical_count} critical incidents detected ({(critical_count/total)*100:.1f}%).")
        
        if open_count > total * 0.5:
            trend_parts.append(f"High number of open incidents ({open_count}) may indicate resolution bottleneck.")
        
        system_breakdown = {}
        for incident in incidents:
            system = incident.get("system", "unknown")
            system_breakdown[system] = system_breakdown.get(system, 0) + 1
        
        if system_breakdown:
            max_system = max(system_breakdown.items(), key=lambda x: x[1])
            trend_parts.append(f"Most incidents from {max_system[0]} ({max_system[1]} incidents).")
        
        return " ".join(trend_parts)
    
    def _generate_summary_text(
        self,
        total_incidents: int,
        severity_breakdown: SeverityBreakdown,
        critical_incidents: List[CriticalIncidentHighlight],
        trend_analysis: Optional[str]
    ) -> str:
        parts = [
            f"Daily Incident Summary: {total_incidents} total incidents.",
            f"Severity: {severity_breakdown.critical} critical, {severity_breakdown.high} high, "
            f"{severity_breakdown.medium} medium, {severity_breakdown.low} low.",
        ]
        
        if critical_incidents:
            parts.append(f"{len(critical_incidents)} incidents require immediate attention.")
        
        if trend_analysis:
            parts.append(trend_analysis)
        
        return " ".join(parts)
    
    async def _send_email_summary(
        self,
        config: DailySummaryConfig,
        report: DailySummaryReport
    ):
        if not self.notification_service:
            logger.info(f"Email summary prepared for {config.user_id} (no notification service configured)")
            return
        
        message = self._format_email_message(report)
        recipients = config.email_recipients or [config.user_id]
        
        for recipient in recipients:
            logger.info(f"Sending daily summary email to {recipient}")
    
    def _format_email_message(self, report: DailySummaryReport) -> str:
        message = f"""
Daily Incident Summary Report
==============================

Period: {report.period_start.strftime('%Y-%m-%d')} to {report.period_end.strftime('%Y-%m-%d')}
Generated: {report.generated_at.strftime('%Y-%m-%d %H:%M:%S')}

SUMMARY
-------
Total Incidents: {report.total_incidents}

Severity Breakdown:
- Critical: {report.severity_breakdown.critical}
- High: {report.severity_breakdown.high}
- Medium: {report.severity_breakdown.medium}
- Low: {report.severity_breakdown.low}

"""
        
        if report.critical_incidents:
            message += "\nCRITICAL INCIDENTS REQUIRING ATTENTION\n"
            message += "---------------------------------------\n"
            for incident in report.critical_incidents:
                message += f"\n[{incident.severity.upper()}] {incident.incident_id}\n"
                message += f"  Title: {incident.title}\n"
                message += f"  System: {incident.system}\n"
                message += f"  Reason: {incident.reason}\n"
        
        if report.trend_analysis:
            message += f"\n\nTREND ANALYSIS\n"
            message += "--------------\n"
            message += report.trend_analysis
        
        message += "\n\n---\nThis is an automated daily summary from InsightBot.\n"
        
        return message
