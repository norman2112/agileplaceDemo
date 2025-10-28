"""
Unit tests for BMC service integration.
"""
import pytest
from src.models.bmc import BMCRecordRequest, BMCRecordStatus
from src.services.bmc_service import BMCService
from src.services.audit_service import AuditService


@pytest.fixture
def audit_service():
    """Create audit service fixture."""
    return AuditService()


@pytest.fixture
def bmc_service(audit_service):
    """Create BMC service fixture."""
    return BMCService(audit_service=audit_service)


@pytest.mark.asyncio
async def test_create_bmc_record(bmc_service):
    """Test creating a new BMC record."""
    request = BMCRecordRequest(
        title="Test BMC Record",
        description="This is a test BMC record",
        metadata={"source": "test"}
    )
    
    response = await bmc_service.create_record(request, actor="test-user")
    
    assert response.success is True
    assert response.record is not None
    assert response.record.title == "Test BMC Record"
    assert response.record.status == BMCRecordStatus.PENDING


@pytest.mark.asyncio
async def test_get_bmc_record(bmc_service):
    """Test retrieving a BMC record by ID."""
    # Create a record first
    request = BMCRecordRequest(
        title="Test Record",
        description="Description"
    )
    create_response = await bmc_service.create_record(request)
    record_id = create_response.record_id
    
    # Retrieve the record
    record = await bmc_service.get_record(record_id)
    
    assert record is not None
    assert record.record_id == record_id
    assert record.title == "Test Record"


@pytest.mark.asyncio
async def test_list_bmc_records(bmc_service):
    """Test listing BMC records."""
    # Create a few records
    for i in range(3):
        request = BMCRecordRequest(
            title=f"Test Record {i}",
            description=f"Description {i}"
        )
        await bmc_service.create_record(request)
    
    # List all records
    records = await bmc_service.list_records()
    
    assert len(records) >= 3


@pytest.mark.asyncio
async def test_update_record_status(bmc_service):
    """Test updating BMC record status."""
    # Create a record
    request = BMCRecordRequest(
        title="Test Record",
        description="Description"
    )
    create_response = await bmc_service.create_record(request)
    record_id = create_response.record_id
    
    # Update status
    update_response = await bmc_service.update_record_status(
        record_id,
        BMCRecordStatus.ACTIVE,
        actor="test-user"
    )
    
    assert update_response.success is True
    assert update_response.record.status == BMCRecordStatus.ACTIVE


@pytest.mark.asyncio
async def test_update_nonexistent_record(bmc_service):
    """Test updating a record that doesn't exist."""
    response = await bmc_service.update_record_status(
        "nonexistent-id",
        BMCRecordStatus.ACTIVE
    )
    
    assert response.success is False
    assert "not found" in response.message


@pytest.mark.asyncio
async def test_list_records_with_status_filter(bmc_service):
    """Test listing records with status filter."""
    # Create records with different statuses
    request1 = BMCRecordRequest(title="Record 1", description="Desc 1")
    response1 = await bmc_service.create_record(request1)
    
    request2 = BMCRecordRequest(title="Record 2", description="Desc 2")
    response2 = await bmc_service.create_record(request2)
    
    # Update one to ACTIVE
    await bmc_service.update_record_status(
        response2.record_id,
        BMCRecordStatus.ACTIVE
    )
    
    # List only ACTIVE records
    active_records = await bmc_service.list_records(status=BMCRecordStatus.ACTIVE)
    
    assert len(active_records) >= 1
    assert all(r.status == BMCRecordStatus.ACTIVE for r in active_records)


@pytest.mark.asyncio
async def test_bmc_operations_create_audit_logs(bmc_service, audit_service):
    """Test that BMC operations create audit log entries."""
    initial_count = len(audit_service._audit_log)
    
    # Create a record
    request = BMCRecordRequest(
        title="Audit Test",
        description="Testing audit logging"
    )
    response = await bmc_service.create_record(request, actor="test-user")
    
    # Update status
    await bmc_service.update_record_status(
        response.record_id,
        BMCRecordStatus.ACTIVE,
        actor="test-user"
    )
    
    # Verify audit logs were created
    assert len(audit_service._audit_log) > initial_count
