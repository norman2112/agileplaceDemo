"""
BMC service - handles integration with BMC systems.
"""
import logging
from datetime import datetime
from typing import List, Optional
from uuid import uuid4

from src.models.bmc import (
    BMCRecord, BMCRecordRequest, BMCRecordResponse, BMCRecordStatus
)
from src.services.audit_service import AuditService

logger = logging.getLogger(__name__)


class BMCService:
    """
    Service responsible for managing BMC records and integration.
    
    This service provides:
    - BMC record creation and management
    - Integration with BMC systems
    - Audit logging for BMC operations
    """
    
    def __init__(self, audit_service: AuditService):
        self.audit_service = audit_service
        # In production, this would connect to actual BMC systems
        self._records_cache = {}  # Temporary in-memory storage
        
    async def create_record(
        self,
        request: BMCRecordRequest,
        actor: str = "system"
    ) -> BMCRecordResponse:
        """
        Create a new BMC record.
        
        Args:
            request: The BMC record creation request
            actor: The user/system creating the record
            
        Returns:
            BMCRecordResponse with the created record
        """
        try:
            record_id = str(uuid4())
            
            record = BMCRecord(
                record_id=record_id,
                title=request.title,
                description=request.description,
                metadata=request.metadata or {},
                status=BMCRecordStatus.PENDING
            )
            
            # Store record (in production, this would persist to database)
            self._records_cache[record_id] = record
            
            # Audit log the creation
            await self.audit_service.log_action(
                action="bmc_record_created",
                actor=actor,
                details={
                    "record_id": record_id,
                    "title": record.title
                }
            )
            
            logger.info(f"Created BMC record {record_id}")
            
            return BMCRecordResponse(
                record_id=record_id,
                success=True,
                message="BMC record created successfully",
                record=record
            )
            
        except Exception as e:
            error_message = f"Failed to create BMC record: {str(e)}"
            logger.error(error_message, exc_info=True)
            
            return BMCRecordResponse(
                record_id="",
                success=False,
                message=error_message
            )
    
    async def get_record(self, record_id: str) -> Optional[BMCRecord]:
        """
        Retrieve a BMC record by ID.
        
        Args:
            record_id: The record identifier
            
        Returns:
            BMCRecord if found, None otherwise
        """
        return self._records_cache.get(record_id)
    
    async def list_records(
        self,
        status: Optional[BMCRecordStatus] = None,
        limit: int = 100
    ) -> List[BMCRecord]:
        """
        List BMC records with optional filtering.
        
        Args:
            status: Filter by status (optional)
            limit: Maximum number of records to return
            
        Returns:
            List of BMC records
        """
        records = list(self._records_cache.values())
        
        if status:
            records = [r for r in records if r.status == status]
        
        return records[:limit]
    
    async def update_record_status(
        self,
        record_id: str,
        status: BMCRecordStatus,
        actor: str = "system"
    ) -> BMCRecordResponse:
        """
        Update the status of a BMC record.
        
        Args:
            record_id: The record identifier
            status: New status
            actor: The user/system updating the status
            
        Returns:
            BMCRecordResponse with updated record
        """
        record = await self.get_record(record_id)
        
        if not record:
            return BMCRecordResponse(
                record_id=record_id,
                success=False,
                message=f"BMC record {record_id} not found"
            )
        
        record.status = status
        record.updated_at = datetime.utcnow()
        
        # Audit log the update
        await self.audit_service.log_action(
            action="bmc_record_status_updated",
            actor=actor,
            details={
                "record_id": record_id,
                "new_status": status.value
            }
        )
        
        logger.info(f"Updated BMC record {record_id} status to {status}")
        
        return BMCRecordResponse(
            record_id=record_id,
            success=True,
            message="BMC record status updated successfully",
            record=record
        )
