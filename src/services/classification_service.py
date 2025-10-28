"""
Incident Classification Service - automatically classifies incoming incidents.

Requirements:
- Correctly classify at least 80% of incoming incidents
- Classification must occur within 5 seconds of ticket creation
- Display classification confidence score
- Support for 20+ predefined incident categories
- Manual override option for incorrect classifications
"""
import logging
import time
from typing import Optional, List
from uuid import uuid4

from src.models.incident import Incident, IncidentCategory
from src.models.classification import (
    ClassificationRequest,
    ClassificationResult,
    ClassificationOverride,
    ClassificationStats,
    ClassificationFeedback
)
from src.services.audit_service import AuditService

logger = logging.getLogger(__name__)


class ClassificationService:
    """
    Service responsible for automatic incident classification.
    
    This is a stub implementation that would be replaced with:
    - ML model integration (e.g., trained text classifier)
    - NLP pipeline for text analysis
    - Feature extraction from incident descriptions
    - Category prediction with confidence scores
    """
    
    def __init__(self, audit_service: AuditService):
        self.audit_service = audit_service
        self.model_version = "1.0.0"
        
        # In production, these would be loaded from persistent storage
        self._overrides: List[ClassificationOverride] = []
        self._feedback: List[ClassificationFeedback] = []
        self._stats = ClassificationStats()
        
        # Keyword-based classification (stub for ML model)
        self._category_keywords = self._initialize_category_keywords()
    
    async def classify_incident(
        self,
        request: ClassificationRequest,
        max_processing_time_ms: int = 5000
    ) -> ClassificationResult:
        """
        Classify an incident into a category.
        
        Args:
            request: Classification request with incident details
            max_processing_time_ms: Maximum allowed processing time (default 5000ms = 5 seconds)
            
        Returns:
            ClassificationResult with category and confidence score
        """
        start_time = time.time()
        
        logger.info(f"Classifying incident {request.incident_id}")
        
        try:
            # Check if there's a manual override for this incident
            override = self._get_override(request.incident_id)
            if override:
                logger.info(f"Using manual override for incident {request.incident_id}")
                return await self._apply_override(request, override, start_time)
            
            # Audit: Classification started
            await self.audit_service.log_action(
                action="classification_started",
                incident_id=request.incident_id,
                details={"title": request.title}
            )
            
            # Perform classification (stub implementation)
            category, confidence, alternatives = await self._classify(
                title=request.title,
                description=request.description,
                metadata=request.metadata
            )
            
            processing_time_ms = int((time.time() - start_time) * 1000)
            
            # Check if we meet the 5-second requirement
            if processing_time_ms > max_processing_time_ms:
                logger.warning(
                    f"Classification took {processing_time_ms}ms, "
                    f"exceeding {max_processing_time_ms}ms requirement"
                )
            
            result = ClassificationResult(
                incident_id=request.incident_id,
                category=category,
                confidence_score=confidence,
                alternative_categories=alternatives,
                processing_time_ms=processing_time_ms,
                model_version=self.model_version
            )
            
            # Update statistics
            self._update_stats(result)
            
            # Audit: Classification completed
            await self.audit_service.log_action(
                action="classification_completed",
                incident_id=request.incident_id,
                details={
                    "category": category.value,
                    "confidence": confidence,
                    "processing_time_ms": processing_time_ms
                }
            )
            
            logger.info(
                f"Classified incident {request.incident_id} as {category.value} "
                f"with confidence {confidence:.2%} in {processing_time_ms}ms"
            )
            
            return result
            
        except Exception as e:
            processing_time_ms = int((time.time() - start_time) * 1000)
            error_msg = f"Classification failed: {str(e)}"
            logger.error(f"Error classifying incident {request.incident_id}: {error_msg}", exc_info=True)
            
            # Return a low-confidence default classification
            return ClassificationResult(
                incident_id=request.incident_id,
                category=IncidentCategory.APPLICATION,  # Safe default
                confidence_score=0.0,
                alternative_categories=[],
                processing_time_ms=processing_time_ms,
                model_version=self.model_version
            )
    
    async def override_classification(
        self,
        incident_id: str,
        original_category: IncidentCategory,
        original_confidence: float,
        override_category: IncidentCategory,
        override_reason: str,
        overridden_by: str
    ) -> ClassificationOverride:
        """
        Manually override automatic classification.
        
        Args:
            incident_id: Incident identifier
            original_category: Original automatic classification
            original_confidence: Original confidence score
            override_category: Manual override category
            override_reason: Reason for override
            overridden_by: User who performed override
            
        Returns:
            ClassificationOverride record
        """
        logger.info(
            f"Manual override for incident {incident_id}: "
            f"{original_category.value} -> {override_category.value}"
        )
        
        override = ClassificationOverride(
            incident_id=incident_id,
            original_category=original_category,
            original_confidence=original_confidence,
            override_category=override_category,
            override_reason=override_reason,
            overridden_by=overridden_by
        )
        
        # Store override
        self._overrides.append(override)
        
        # Update statistics
        self._stats.overrides_count += 1
        if self._stats.total_classifications > 0:
            self._stats.override_rate = self._stats.overrides_count / self._stats.total_classifications
        
        # Audit: Classification overridden
        await self.audit_service.log_action(
            action="classification_overridden",
            incident_id=incident_id,
            details={
                "original_category": original_category.value,
                "override_category": override_category.value,
                "reason": override_reason,
                "overridden_by": overridden_by
            }
        )
        
        logger.info(f"Override recorded for incident {incident_id}")
        
        return override
    
    async def submit_feedback(
        self,
        incident_id: str,
        classification_id: str,
        was_correct: bool,
        expected_category: Optional[IncidentCategory],
        feedback_type: str,
        comments: Optional[str],
        submitted_by: str
    ) -> ClassificationFeedback:
        """
        Submit feedback on classification accuracy.
        
        This feedback is used to:
        - Monitor classification accuracy
        - Retrain and improve the ML model
        - Identify categories that need more training data
        """
        feedback = ClassificationFeedback(
            feedback_id=str(uuid4()),
            incident_id=incident_id,
            classification_id=classification_id,
            was_correct=was_correct,
            expected_category=expected_category,
            feedback_type=feedback_type,
            comments=comments,
            submitted_by=submitted_by
        )
        
        self._feedback.append(feedback)
        
        # Audit: Feedback submitted
        await self.audit_service.log_action(
            action="classification_feedback_submitted",
            incident_id=incident_id,
            details={
                "was_correct": was_correct,
                "feedback_type": feedback_type,
                "submitted_by": submitted_by
            }
        )
        
        logger.info(f"Feedback {feedback.feedback_id} submitted for incident {incident_id}")
        
        return feedback
    
    async def get_stats(self) -> ClassificationStats:
        """Get classification engine statistics."""
        return self._stats
    
    async def get_overrides(self, incident_id: Optional[str] = None) -> List[ClassificationOverride]:
        """Get classification overrides, optionally filtered by incident ID."""
        if incident_id:
            return [o for o in self._overrides if o.incident_id == incident_id]
        return self._overrides
    
    async def _classify(
        self,
        title: str,
        description: str,
        metadata: Optional[dict]
    ) -> tuple[IncidentCategory, float, List[tuple[IncidentCategory, float]]]:
        """
        Perform actual classification.
        
        This is a stub implementation using keyword matching.
        In production, this would:
        - Use a trained ML model (e.g., BERT, transformers)
        - Extract features from title, description, metadata
        - Return category prediction with confidence scores
        - Provide alternative categories ranked by probability
        """
        text = f"{title} {description}".lower()
        
        # Score each category based on keyword matches
        scores = {}
        for category, keywords in self._category_keywords.items():
            score = sum(1 for keyword in keywords if keyword in text)
            if score > 0:
                scores[category] = score
        
        if not scores:
            # No keywords matched - return low confidence default
            return IncidentCategory.APPLICATION, 0.3, []
        
        # Get top category
        top_category = max(scores, key=scores.get)
        total_matches = sum(scores.values())
        
        # Calculate confidence based on match strength
        # This is a simplified approach - real ML would use model probabilities
        confidence = min(0.95, (scores[top_category] / (total_matches + 1)) * 1.2)
        
        # Get alternative categories
        alternatives = []
        for category, score in sorted(scores.items(), key=lambda x: x[1], reverse=True)[1:4]:
            alt_confidence = min(0.90, (score / (total_matches + 1)) * 1.0)
            alternatives.append((category, alt_confidence))
        
        return top_category, confidence, alternatives
    
    def _initialize_category_keywords(self) -> dict[IncidentCategory, List[str]]:
        """
        Initialize keyword mappings for stub classification.
        
        In production, this would be replaced with actual ML model.
        """
        return {
            IncidentCategory.NETWORK: ["network", "connection", "ping", "timeout"],
            IncidentCategory.NETWORK_CONNECTIVITY: ["cannot connect", "connection failed", "unreachable"],
            IncidentCategory.NETWORK_LATENCY: ["slow", "latency", "lag", "delay"],
            IncidentCategory.NETWORK_DNS: ["dns", "domain", "name resolution", "nslookup"],
            IncidentCategory.INFRASTRUCTURE: ["infrastructure", "server", "host", "vm"],
            IncidentCategory.HARDWARE_FAILURE: ["hardware", "disk", "memory", "cpu failure"],
            IncidentCategory.POWER_OUTAGE: ["power", "outage", "shutdown", "electricity"],
            IncidentCategory.STORAGE: ["storage", "disk space", "volume", "filesystem"],
            IncidentCategory.APPLICATION: ["application", "app", "service", "process"],
            IncidentCategory.APPLICATION_CRASH: ["crash", "crashed", "core dump", "segfault"],
            IncidentCategory.APPLICATION_PERFORMANCE: ["slow performance", "high latency", "response time"],
            IncidentCategory.SOFTWARE_BUG: ["bug", "error", "exception", "defect"],
            IncidentCategory.DEPLOYMENT_ISSUE: ["deployment", "release", "rollout", "version"],
            IncidentCategory.DATABASE: ["database", "db", "sql", "query"],
            IncidentCategory.DATABASE_CONNECTIVITY: ["cannot connect to database", "db connection"],
            IncidentCategory.DATABASE_PERFORMANCE: ["slow query", "db performance", "query timeout"],
            IncidentCategory.DATABASE_CORRUPTION: ["corruption", "corrupt data", "integrity"],
            IncidentCategory.SECURITY: ["security", "vulnerability", "exploit"],
            IncidentCategory.SECURITY_BREACH: ["breach", "intrusion", "compromise"],
            IncidentCategory.MALWARE: ["malware", "virus", "trojan", "ransomware"],
            IncidentCategory.UNAUTHORIZED_ACCESS: ["unauthorized", "illegal access", "intrusion"],
            IncidentCategory.USER_ACCESS: ["access", "permission", "user"],
            IncidentCategory.AUTHENTICATION: ["login", "authentication", "sign in", "credentials"],
            IncidentCategory.AUTHORIZATION: ["authorization", "permission denied", "forbidden"],
            IncidentCategory.PASSWORD_RESET: ["password", "reset password", "forgot password"],
        }
    
    def _get_override(self, incident_id: str) -> Optional[ClassificationOverride]:
        """Get manual override for an incident if it exists."""
        for override in self._overrides:
            if override.incident_id == incident_id:
                return override
        return None
    
    async def _apply_override(
        self,
        request: ClassificationRequest,
        override: ClassificationOverride,
        start_time: float
    ) -> ClassificationResult:
        """Apply manual override to classification result."""
        processing_time_ms = int((time.time() - start_time) * 1000)
        
        return ClassificationResult(
            incident_id=request.incident_id,
            category=override.override_category,
            confidence_score=1.0,  # Manual overrides have 100% confidence
            alternative_categories=[],
            processing_time_ms=processing_time_ms,
            model_version=f"{self.model_version}-override"
        )
    
    def _update_stats(self, result: ClassificationResult):
        """Update classification statistics."""
        self._stats.total_classifications += 1
        
        # Update successful classifications (confidence >= 0.8 for 80% requirement)
        if result.confidence_score >= 0.8:
            self._stats.successful_classifications += 1
        
        # Update accuracy rate
        if self._stats.total_classifications > 0:
            self._stats.accuracy_rate = (
                self._stats.successful_classifications / self._stats.total_classifications
            )
        
        # Update average confidence
        total_confidence = (
            self._stats.average_confidence * (self._stats.total_classifications - 1) +
            result.confidence_score
        )
        self._stats.average_confidence = total_confidence / self._stats.total_classifications
        
        # Update average processing time
        total_time = (
            self._stats.average_processing_time_ms * (self._stats.total_classifications - 1) +
            result.processing_time_ms
        )
        self._stats.average_processing_time_ms = total_time / self._stats.total_classifications
        
        # Update category distribution
        category_key = result.category.value
        self._stats.category_distribution[category_key] = (
            self._stats.category_distribution.get(category_key, 0) + 1
        )
