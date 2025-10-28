"""
Android issue service - handles Android-specific incident tracking and management.
"""
import logging
from datetime import datetime
from typing import List, Optional, Dict
from uuid import uuid4

from src.models.android_issue import (
    AndroidIssue, AndroidIssueCreateRequest, AndroidIssueUpdateRequest,
    AndroidIssueResponse, AndroidSeverity, AndroidIssueType
)
from src.services.audit_service import AuditService

logger = logging.getLogger(__name__)


class AndroidIssueService:
    """
    Service for managing Android-specific issues.
    
    Responsibilities:
    - Track Android crashes, ANRs, and performance issues
    - Aggregate issues across devices and app versions
    - Provide analytics on Android-specific patterns
    """
    
    def __init__(self, audit_service: AuditService):
        self.audit_service = audit_service
        # In production, this would use a database
        self._issues: Dict[str, AndroidIssue] = {}
    
    async def create_issue(self, request: AndroidIssueCreateRequest) -> AndroidIssueResponse:
        """
        Create a new Android issue.
        
        Args:
            request: Issue creation request
            
        Returns:
            AndroidIssueResponse with created issue details
        """
        issue_id = f"ANDROID-{str(uuid4())[:8].upper()}"
        
        issue = AndroidIssue(
            issue_id=issue_id,
            title=request.title,
            description=request.description,
            issue_type=request.issue_type,
            severity=request.severity,
            stack_trace=request.stack_trace,
            device_info=request.device_info,
            app_version=request.app_version,
            tags=request.tags
        )
        
        self._issues[issue_id] = issue
        
        # Audit log
        await self.audit_service.log_action(
            action="android_issue_created",
            actor="system",
            details={
                "issue_id": issue_id,
                "issue_type": request.issue_type.value,
                "severity": request.severity.value
            }
        )
        
        logger.info(f"Created Android issue {issue_id}: {request.title}")
        
        return AndroidIssueResponse(
            issue_id=issue_id,
            success=True,
            message="Android issue created successfully"
        )
    
    async def get_issue(self, issue_id: str) -> Optional[AndroidIssue]:
        """
        Retrieve an Android issue by ID.
        
        Args:
            issue_id: The issue identifier
            
        Returns:
            AndroidIssue if found, None otherwise
        """
        return self._issues.get(issue_id)
    
    async def list_issues(
        self,
        issue_type: Optional[AndroidIssueType] = None,
        severity: Optional[AndroidSeverity] = None,
        is_resolved: Optional[bool] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[AndroidIssue]:
        """
        List Android issues with optional filters.
        
        Args:
            issue_type: Filter by issue type
            severity: Filter by severity
            is_resolved: Filter by resolution status
            limit: Maximum number of results
            offset: Pagination offset
            
        Returns:
            List of AndroidIssue objects
        """
        issues = list(self._issues.values())
        
        # Apply filters
        if issue_type:
            issues = [i for i in issues if i.issue_type == issue_type]
        if severity:
            issues = [i for i in issues if i.severity == severity]
        if is_resolved is not None:
            issues = [i for i in issues if i.is_resolved == is_resolved]
        
        # Sort by last_seen (most recent first)
        issues.sort(key=lambda x: x.last_seen, reverse=True)
        
        # Apply pagination
        return issues[offset:offset + limit]
    
    async def update_issue(
        self,
        issue_id: str,
        request: AndroidIssueUpdateRequest
    ) -> AndroidIssueResponse:
        """
        Update an existing Android issue.
        
        Args:
            issue_id: The issue identifier
            request: Update request with fields to modify
            
        Returns:
            AndroidIssueResponse with update status
        """
        issue = self._issues.get(issue_id)
        
        if not issue:
            return AndroidIssueResponse(
                issue_id=issue_id,
                success=False,
                message=f"Android issue {issue_id} not found"
            )
        
        # Update fields
        if request.title:
            issue.title = request.title
        if request.description:
            issue.description = request.description
        if request.severity:
            issue.severity = request.severity
        if request.is_resolved is not None:
            issue.is_resolved = request.is_resolved
            if request.is_resolved:
                issue.resolved_at = datetime.utcnow()
        if request.tags is not None:
            issue.tags = request.tags
        
        # Audit log
        await self.audit_service.log_action(
            action="android_issue_updated",
            actor="system",
            details={"issue_id": issue_id, "updates": request.dict(exclude_none=True)}
        )
        
        logger.info(f"Updated Android issue {issue_id}")
        
        return AndroidIssueResponse(
            issue_id=issue_id,
            success=True,
            message="Android issue updated successfully"
        )
    
    async def increment_occurrence(self, issue_id: str) -> None:
        """
        Increment the occurrence count for an issue.
        
        Args:
            issue_id: The issue identifier
        """
        issue = self._issues.get(issue_id)
        if issue:
            issue.occurrence_count += 1
            issue.last_seen = datetime.utcnow()
            logger.info(f"Incremented occurrence count for {issue_id}: {issue.occurrence_count}")
    
    async def get_statistics(self) -> Dict:
        """
        Get statistics about Android issues.
        
        Returns:
            Dictionary with aggregated statistics
        """
        issues = list(self._issues.values())
        
        stats = {
            "total_issues": len(issues),
            "open_issues": len([i for i in issues if not i.is_resolved]),
            "resolved_issues": len([i for i in issues if i.is_resolved]),
            "by_type": {},
            "by_severity": {},
            "total_occurrences": sum(i.occurrence_count for i in issues)
        }
        
        # Count by type
        for issue_type in AndroidIssueType:
            count = len([i for i in issues if i.issue_type == issue_type])
            stats["by_type"][issue_type.value] = count
        
        # Count by severity
        for severity in AndroidSeverity:
            count = len([i for i in issues if i.severity == severity])
            stats["by_severity"][severity.value] = count
        
        return stats
