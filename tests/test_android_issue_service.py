"""
Unit tests for Android issue service.
"""
import pytest
from datetime import datetime
from src.models.android_issue import (
    AndroidIssue, AndroidIssueCreateRequest, AndroidIssueUpdateRequest,
    AndroidIssueType, AndroidSeverity, DeviceInfo
)
from src.services.android_issue_service import AndroidIssueService
from src.services.audit_service import AuditService


@pytest.fixture
def audit_service():
    """Create audit service fixture."""
    return AuditService()


@pytest.fixture
def android_issue_service(audit_service):
    """Create Android issue service fixture."""
    return AndroidIssueService(audit_service=audit_service)


@pytest.fixture
def sample_device_info():
    """Create sample device info."""
    return DeviceInfo(
        manufacturer="Samsung",
        model="Galaxy S21",
        android_version="12.0",
        api_level=31,
        screen_density="xxhdpi",
        screen_resolution="1080x2400"
    )


@pytest.fixture
def crash_issue_request(sample_device_info):
    """Create a crash issue request."""
    return AndroidIssueCreateRequest(
        title="App crashes on launch",
        description="Application crashes immediately after launch on Android 12",
        issue_type=AndroidIssueType.CRASH,
        severity=AndroidSeverity.CRITICAL,
        stack_trace="java.lang.NullPointerException at MainActivity.onCreate()",
        device_info=sample_device_info,
        app_version="2.1.0",
        tags=["crash", "launch", "android12"]
    )


@pytest.fixture
def anr_issue_request():
    """Create an ANR issue request."""
    return AndroidIssueCreateRequest(
        title="Application Not Responding on heavy load",
        description="App freezes when loading large datasets",
        issue_type=AndroidIssueType.ANR,
        severity=AndroidSeverity.HIGH,
        app_version="2.1.0",
        tags=["anr", "performance"]
    )


@pytest.mark.asyncio
async def test_create_android_issue(android_issue_service, crash_issue_request):
    """Test creating a new Android issue."""
    response = await android_issue_service.create_issue(crash_issue_request)
    
    assert response.success is True
    assert response.issue_id.startswith("ANDROID-")
    assert "successfully" in response.message.lower()


@pytest.mark.asyncio
async def test_get_android_issue(android_issue_service, crash_issue_request):
    """Test retrieving an Android issue by ID."""
    # Create issue
    response = await android_issue_service.create_issue(crash_issue_request)
    issue_id = response.issue_id
    
    # Retrieve issue
    issue = await android_issue_service.get_issue(issue_id)
    
    assert issue is not None
    assert issue.issue_id == issue_id
    assert issue.title == crash_issue_request.title
    assert issue.issue_type == crash_issue_request.issue_type
    assert issue.severity == crash_issue_request.severity


@pytest.mark.asyncio
async def test_get_nonexistent_issue(android_issue_service):
    """Test retrieving a non-existent issue returns None."""
    issue = await android_issue_service.get_issue("ANDROID-NONEXISTENT")
    assert issue is None


@pytest.mark.asyncio
async def test_list_android_issues(android_issue_service, crash_issue_request, anr_issue_request):
    """Test listing Android issues."""
    # Create multiple issues
    await android_issue_service.create_issue(crash_issue_request)
    await android_issue_service.create_issue(anr_issue_request)
    
    # List all issues
    issues = await android_issue_service.list_issues()
    
    assert len(issues) >= 2


@pytest.mark.asyncio
async def test_list_issues_filtered_by_type(android_issue_service, crash_issue_request, anr_issue_request):
    """Test filtering issues by type."""
    # Create issues
    await android_issue_service.create_issue(crash_issue_request)
    await android_issue_service.create_issue(anr_issue_request)
    
    # Filter by crash type
    crash_issues = await android_issue_service.list_issues(issue_type=AndroidIssueType.CRASH)
    
    assert len(crash_issues) > 0
    assert all(issue.issue_type == AndroidIssueType.CRASH for issue in crash_issues)


@pytest.mark.asyncio
async def test_list_issues_filtered_by_severity(android_issue_service, crash_issue_request):
    """Test filtering issues by severity."""
    # Create issue
    await android_issue_service.create_issue(crash_issue_request)
    
    # Filter by critical severity
    critical_issues = await android_issue_service.list_issues(severity=AndroidSeverity.CRITICAL)
    
    assert len(critical_issues) > 0
    assert all(issue.severity == AndroidSeverity.CRITICAL for issue in critical_issues)


@pytest.mark.asyncio
async def test_update_android_issue(android_issue_service, crash_issue_request):
    """Test updating an Android issue."""
    # Create issue
    response = await android_issue_service.create_issue(crash_issue_request)
    issue_id = response.issue_id
    
    # Update issue
    update_request = AndroidIssueUpdateRequest(
        title="Updated crash title",
        severity=AndroidSeverity.MEDIUM,
        is_resolved=True
    )
    
    update_response = await android_issue_service.update_issue(issue_id, update_request)
    
    assert update_response.success is True
    
    # Verify updates
    updated_issue = await android_issue_service.get_issue(issue_id)
    assert updated_issue.title == "Updated crash title"
    assert updated_issue.severity == AndroidSeverity.MEDIUM
    assert updated_issue.is_resolved is True
    assert updated_issue.resolved_at is not None


@pytest.mark.asyncio
async def test_update_nonexistent_issue(android_issue_service):
    """Test updating a non-existent issue returns error."""
    update_request = AndroidIssueUpdateRequest(title="Updated")
    
    response = await android_issue_service.update_issue("ANDROID-NONEXISTENT", update_request)
    
    assert response.success is False
    assert "not found" in response.message.lower()


@pytest.mark.asyncio
async def test_increment_occurrence(android_issue_service, crash_issue_request):
    """Test incrementing occurrence count."""
    # Create issue
    response = await android_issue_service.create_issue(crash_issue_request)
    issue_id = response.issue_id
    
    # Get initial occurrence count
    issue = await android_issue_service.get_issue(issue_id)
    initial_count = issue.occurrence_count
    
    # Increment occurrence
    await android_issue_service.increment_occurrence(issue_id)
    
    # Verify increment
    updated_issue = await android_issue_service.get_issue(issue_id)
    assert updated_issue.occurrence_count == initial_count + 1


@pytest.mark.asyncio
async def test_get_statistics(android_issue_service, crash_issue_request, anr_issue_request):
    """Test getting Android issue statistics."""
    # Create issues
    await android_issue_service.create_issue(crash_issue_request)
    await android_issue_service.create_issue(anr_issue_request)
    
    # Get statistics
    stats = await android_issue_service.get_statistics()
    
    assert "total_issues" in stats
    assert "open_issues" in stats
    assert "resolved_issues" in stats
    assert "by_type" in stats
    assert "by_severity" in stats
    assert stats["total_issues"] >= 2


@pytest.mark.asyncio
async def test_pagination(android_issue_service, crash_issue_request):
    """Test issue list pagination."""
    # Create multiple issues
    for i in range(5):
        await android_issue_service.create_issue(crash_issue_request)
    
    # Test pagination
    first_page = await android_issue_service.list_issues(limit=2, offset=0)
    second_page = await android_issue_service.list_issues(limit=2, offset=2)
    
    assert len(first_page) == 2
    assert len(second_page) == 2
    assert first_page[0].issue_id != second_page[0].issue_id
