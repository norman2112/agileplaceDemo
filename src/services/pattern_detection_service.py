"""
Pattern detection service - analyzes incidents to identify recurring patterns.
"""
import logging
import time
import re
from datetime import datetime
from typing import List, Optional, Dict
from uuid import uuid4

from src.models.pattern import (
    IncidentPattern, PatternMatch, PatternType,
    PatternAnalysisRequest, PatternAnalysisResponse
)
from src.models.audit import AuditAction
from src.services.audit_service import AuditService

logger = logging.getLogger(__name__)

# Default timeout for pattern analysis (30 seconds as per requirements)
ANALYSIS_TIMEOUT_MS = 30000


class PatternDetectionService:
    """
    Service for detecting common incident patterns.
    
    Analyzes incoming incidents against known patterns based on:
    - Error messages
    - System components
    - Historical data
    
    Identifies matches within 30 seconds and logs results with confidence scores.
    """
    
    def __init__(self, audit_service: AuditService):
        self.audit_service = audit_service
        self._patterns: Dict[str, IncidentPattern] = {}
        self._incident_history: List[Dict] = []
        self._initialize_default_patterns()
    
    def _initialize_default_patterns(self):
        """Initialize common incident patterns."""
        default_patterns = [
            IncidentPattern(
                pattern_id="pat_conn_timeout",
                name="Connection Timeout Pattern",
                pattern_type=PatternType.ERROR_MESSAGE,
                keywords=["timeout", "connection refused", "connection timed out", "ETIMEDOUT"],
                components=["database", "api", "network"],
                category="network",
                min_confidence_threshold=0.7
            ),
            IncidentPattern(
                pattern_id="pat_memory_exhaustion",
                name="Memory Exhaustion Pattern",
                pattern_type=PatternType.SYSTEM_COMPONENT,
                keywords=["out of memory", "OOM", "memory limit", "heap overflow", "memory exhausted"],
                components=["application", "container", "server"],
                category="infrastructure",
                min_confidence_threshold=0.75
            ),
            IncidentPattern(
                pattern_id="pat_auth_failure",
                name="Authentication Failure Pattern",
                pattern_type=PatternType.ERROR_MESSAGE,
                keywords=["authentication failed", "unauthorized", "401", "invalid token", "access denied"],
                components=["auth", "api", "identity"],
                category="security",
                min_confidence_threshold=0.8
            ),
            IncidentPattern(
                pattern_id="pat_db_connection",
                name="Database Connection Pattern",
                pattern_type=PatternType.SYSTEM_COMPONENT,
                keywords=["connection pool", "max connections", "database unavailable", "connection reset"],
                components=["database", "postgresql", "mysql", "mongodb"],
                category="database",
                min_confidence_threshold=0.75
            ),
            IncidentPattern(
                pattern_id="pat_disk_space",
                name="Disk Space Pattern",
                pattern_type=PatternType.SYSTEM_COMPONENT,
                keywords=["disk full", "no space left", "storage quota", "disk space low"],
                components=["storage", "filesystem", "disk"],
                category="infrastructure",
                min_confidence_threshold=0.85
            ),
            IncidentPattern(
                pattern_id="pat_service_unavailable",
                name="Service Unavailable Pattern",
                pattern_type=PatternType.ERROR_MESSAGE,
                keywords=["503", "service unavailable", "service down", "unhealthy", "not responding"],
                components=["service", "api", "microservice"],
                category="application",
                min_confidence_threshold=0.7
            ),
            IncidentPattern(
                pattern_id="pat_rate_limit",
                name="Rate Limiting Pattern",
                pattern_type=PatternType.ERROR_MESSAGE,
                keywords=["rate limit", "429", "too many requests", "throttled", "quota exceeded"],
                components=["api", "gateway"],
                category="application",
                min_confidence_threshold=0.8
            ),
            IncidentPattern(
                pattern_id="pat_cert_expiry",
                name="Certificate Expiry Pattern",
                pattern_type=PatternType.ERROR_MESSAGE,
                keywords=["certificate expired", "ssl error", "tls handshake", "cert invalid"],
                components=["ssl", "tls", "certificate"],
                category="security",
                min_confidence_threshold=0.9
            ),
        ]
        
        for pattern in default_patterns:
            self._patterns[pattern.pattern_id] = pattern
    
    async def analyze_incident(
        self,
        request: PatternAnalysisRequest
    ) -> PatternAnalysisResponse:
        """
        Analyze an incident for pattern matches.
        
        Must complete within 30 seconds per acceptance criteria.
        Logs pattern matches with confidence scores.
        """
        start_time = time.time()
        
        await self.audit_service.log_entry(
            incident_id=request.incident_id,
            action=AuditAction.PATTERN_ANALYSIS_STARTED,
            details={"title": request.title, "category": request.category}
        )
        
        matches: List[PatternMatch] = []
        text_to_analyze = self._prepare_text(request)
        
        for pattern in self._patterns.values():
            elapsed_ms = int((time.time() - start_time) * 1000)
            if elapsed_ms >= ANALYSIS_TIMEOUT_MS:
                logger.warning(f"Pattern analysis timeout reached for incident {request.incident_id}")
                break
            
            match = self._match_pattern(pattern, text_to_analyze, request, start_time)
            if match and match.confidence_score > 0:
                matches.append(match)
        
        # Sort by confidence score
        matches.sort(key=lambda m: m.confidence_score, reverse=True)
        
        total_time_ms = int((time.time() - start_time) * 1000)
        best_match = matches[0] if matches else None
        auto_response_triggered = False
        
        if best_match:
            # Log pattern match
            await self.audit_service.log_entry(
                incident_id=request.incident_id,
                action=AuditAction.PATTERN_MATCH_FOUND,
                confidence_score=best_match.confidence_score,
                details={
                    "pattern_id": best_match.pattern_id,
                    "pattern_name": best_match.pattern_name,
                    "matched_keywords": best_match.matched_keywords,
                    "analysis_time_ms": total_time_ms
                }
            )
            
            # Trigger auto-response for high-confidence matches
            if best_match.should_auto_respond:
                auto_response_triggered = True
                await self._trigger_auto_response(request.incident_id, best_match)
            
            # Update pattern occurrence count
            if best_match.pattern_id in self._patterns:
                self._patterns[best_match.pattern_id].occurrence_count += 1
        
        # Store in history for future pattern learning
        self._store_incident_history(request, matches)
        
        logger.info(
            f"Pattern analysis completed for incident {request.incident_id}: "
            f"{len(matches)} matches found in {total_time_ms}ms"
        )
        
        return PatternAnalysisResponse(
            incident_id=request.incident_id,
            matches=matches,
            best_match=best_match,
            total_analysis_time_ms=total_time_ms,
            auto_response_triggered=auto_response_triggered
        )
    
    def _prepare_text(self, request: PatternAnalysisRequest) -> str:
        """Prepare combined text for analysis."""
        parts = [request.title, request.description]
        if request.error_message:
            parts.append(request.error_message)
        if request.tags:
            parts.extend(request.tags)
        return " ".join(parts).lower()
    
    def _match_pattern(
        self,
        pattern: IncidentPattern,
        text: str,
        request: PatternAnalysisRequest,
        start_time: float
    ) -> Optional[PatternMatch]:
        """Match a single pattern against incident text."""
        analysis_start = time.time()
        
        matched_keywords = []
        matched_components = []
        
        # Keyword matching
        for keyword in pattern.keywords:
            if keyword.lower() in text:
                matched_keywords.append(keyword)
        
        # Component matching
        component_text = (request.component or "").lower()
        for comp in pattern.components:
            if comp.lower() in text or comp.lower() in component_text:
                matched_components.append(comp)
        
        # Category matching bonus
        category_match = pattern.category and pattern.category == request.category
        
        # Calculate confidence score
        confidence = self._calculate_confidence(
            pattern, matched_keywords, matched_components, category_match
        )
        
        if confidence < 0.1:
            return None
        
        analysis_time_ms = int((time.time() - analysis_start) * 1000)
        
        # Determine if auto-response should be triggered
        should_auto_respond = (
            pattern.auto_response_enabled and
            confidence >= pattern.min_confidence_threshold
        )
        
        return PatternMatch(
            pattern_id=pattern.pattern_id,
            pattern_name=pattern.name,
            confidence_score=round(confidence, 3),
            matched_keywords=matched_keywords,
            matched_components=matched_components,
            analysis_time_ms=analysis_time_ms,
            should_auto_respond=should_auto_respond
        )
    
    def _calculate_confidence(
        self,
        pattern: IncidentPattern,
        matched_keywords: List[str],
        matched_components: List[str],
        category_match: bool
    ) -> float:
        """Calculate confidence score for a pattern match."""
        if not matched_keywords and not matched_components:
            return 0.0
        
        keyword_score = 0.0
        if pattern.keywords:
            keyword_score = len(matched_keywords) / len(pattern.keywords)
        
        component_score = 0.0
        if pattern.components:
            component_score = len(matched_components) / len(pattern.components)
        
        # Weight: keywords 50%, components 30%, category 20%
        base_score = (keyword_score * 0.5) + (component_score * 0.3)
        
        if category_match:
            base_score += 0.2
        
        # Boost for multiple keyword matches
        if len(matched_keywords) >= 2:
            base_score = min(1.0, base_score * 1.15)
        
        return min(1.0, base_score)
    
    async def _trigger_auto_response(
        self,
        incident_id: str,
        match: PatternMatch
    ):
        """Trigger automated response for high-confidence pattern match."""
        logger.info(
            f"Triggering auto-response for incident {incident_id} "
            f"based on pattern {match.pattern_name} (confidence: {match.confidence_score:.2%})"
        )
        
        await self.audit_service.log_entry(
            incident_id=incident_id,
            action=AuditAction.PATTERN_AUTO_RESPONSE_TRIGGERED,
            confidence_score=match.confidence_score,
            details={
                "pattern_id": match.pattern_id,
                "pattern_name": match.pattern_name,
                "trigger_reason": "High confidence pattern match"
            }
        )
    
    def _store_incident_history(
        self,
        request: PatternAnalysisRequest,
        matches: List[PatternMatch]
    ):
        """Store incident for historical pattern learning."""
        self._incident_history.append({
            "incident_id": request.incident_id,
            "title": request.title,
            "category": request.category,
            "matches": [m.pattern_id for m in matches],
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # Keep only recent history
        if len(self._incident_history) > 1000:
            self._incident_history = self._incident_history[-1000:]
    
    def register_pattern(self, pattern: IncidentPattern) -> IncidentPattern:
        """Register a new pattern for detection."""
        if not pattern.pattern_id:
            pattern.pattern_id = f"pat_{uuid4().hex[:8]}"
        self._patterns[pattern.pattern_id] = pattern
        logger.info(f"Registered new pattern: {pattern.name} ({pattern.pattern_id})")
        return pattern
    
    def get_pattern(self, pattern_id: str) -> Optional[IncidentPattern]:
        """Get a pattern by ID."""
        return self._patterns.get(pattern_id)
    
    def list_patterns(self) -> List[IncidentPattern]:
        """List all registered patterns."""
        return list(self._patterns.values())
    
    def get_pattern_statistics(self) -> Dict:
        """Get statistics about pattern matches."""
        total_matches = sum(p.occurrence_count for p in self._patterns.values())
        top_patterns = sorted(
            self._patterns.values(),
            key=lambda p: p.occurrence_count,
            reverse=True
        )[:5]
        
        return {
            "total_patterns": len(self._patterns),
            "total_matches": total_matches,
            "incidents_analyzed": len(self._incident_history),
            "top_patterns": [
                {"name": p.name, "matches": p.occurrence_count}
                for p in top_patterns
            ]
        }
