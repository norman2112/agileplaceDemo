"""
Learning service - handles continuous AI improvement through feedback and retraining.
"""
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from uuid import uuid4
from collections import defaultdict, Counter

from src.models.learning import (
    ResolutionFeedback, FeedbackType, LearningMetrics, CategoryPerformanceMetrics,
    TrainingDataset, ModelRetrainingRequest, ModelRetrainingResult,
    EmergingPatternSuggestion
)
from src.models.incident import Incident, IncidentCategory
from src.services.audit_service import AuditService

logger = logging.getLogger(__name__)


class LearningService:
    """
    Service for continuous learning and AI model improvement.
    
    Responsibilities:
    - Collect feedback from manual resolutions
    - Track accuracy metrics by category
    - Prepare training datasets
    - Coordinate model retraining
    - Detect emerging incident patterns
    - Generate performance reports
    """
    
    def __init__(self, audit_service: AuditService):
        self.audit_service = audit_service
        # In production, these would be persistent storage (database, ML platform)
        self._feedback_store: List[ResolutionFeedback] = []
        self._incident_store: List[Incident] = []
        self._training_history: List[ModelRetrainingResult] = []
        self._current_model_version = "1.0.0"
        
    async def submit_feedback(self, feedback: ResolutionFeedback) -> ResolutionFeedback:
        """
        Submit feedback from manual resolution to improve AI recommendations.
        
        This feedback is used to:
        - Identify classification errors
        - Learn from successful manual resolutions
        - Improve confidence scoring
        - Retrain models with real-world data
        
        Args:
            feedback: Feedback from manual incident resolution
            
        Returns:
            Stored feedback entry
        """
        self._feedback_store.append(feedback)
        
        logger.info(
            f"Feedback received for incident {feedback.incident_id}: "
            f"{feedback.feedback_type.value} (submitted by {feedback.submitted_by})"
        )
        
        # Track if this is a classification correction
        if feedback.feedback_type == FeedbackType.INCORRECT_CLASSIFICATION:
            logger.warning(
                f"Classification error detected: {feedback.original_category} -> {feedback.correct_category} "
                f"(confidence: {feedback.original_confidence:.2%})"
            )
        
        return feedback
    
    async def get_feedback_by_incident(self, incident_id: str) -> List[ResolutionFeedback]:
        """Get all feedback for a specific incident."""
        return [f for f in self._feedback_store if f.incident_id == incident_id]
    
    async def calculate_category_metrics(
        self,
        category: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> CategoryPerformanceMetrics:
        """
        Calculate performance metrics for a specific category.
        
        Metrics include:
        - Auto-resolution success rate
        - Classification accuracy
        - Average confidence scores
        - False positive/negative rates
        """
        # Filter feedback by category and date range
        relevant_feedback = [
            f for f in self._feedback_store
            if f.original_category == category
        ]
        
        if start_date:
            relevant_feedback = [f for f in relevant_feedback if f.submitted_at >= start_date]
        if end_date:
            relevant_feedback = [f for f in relevant_feedback if f.submitted_at <= end_date]
        
        if not relevant_feedback:
            return CategoryPerformanceMetrics(
                category=category,
                last_updated=datetime.utcnow()
            )
        
        # Calculate metrics
        total_incidents = len(relevant_feedback)
        
        # Classification accuracy
        correct_classifications = sum(
            1 for f in relevant_feedback
            if f.feedback_type == FeedbackType.CORRECT_CLASSIFICATION or
            (f.correct_category is None and f.feedback_type != FeedbackType.INCORRECT_CLASSIFICATION)
        )
        classification_accuracy = correct_classifications / total_incidents if total_incidents > 0 else 0.0
        
        # Auto-resolution metrics
        auto_resolved = [f for f in relevant_feedback if f.resolution_successful]
        auto_resolved_count = len(auto_resolved)
        success_rate = auto_resolved_count / total_incidents if total_incidents > 0 else 0.0
        
        # Average confidence
        avg_confidence = sum(f.original_confidence for f in relevant_feedback) / total_incidents
        
        # False positives: Auto-resolved but shouldn't have been
        false_positives = sum(
            1 for f in relevant_feedback
            if f.feedback_type == FeedbackType.RESOLUTION_FAILURE
        )
        
        # False negatives: Could have been auto-resolved but wasn't
        # (This would require additional tracking of manual resolutions that could have been automated)
        false_negatives = sum(
            1 for f in relevant_feedback
            if f.feedback_type == FeedbackType.MANUAL_OVERRIDE and f.resolution_successful
        )
        
        return CategoryPerformanceMetrics(
            category=category,
            total_incidents=total_incidents,
            auto_resolved_count=auto_resolved_count,
            auto_resolution_success_rate=success_rate,
            classification_accuracy=classification_accuracy,
            average_confidence=avg_confidence,
            false_positive_count=false_positives,
            false_negative_count=false_negatives,
            last_updated=datetime.utcnow()
        )
    
    async def calculate_overall_metrics(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> LearningMetrics:
        """
        Calculate overall learning system metrics for a time period.
        
        This provides a comprehensive view of AI performance across all categories.
        """
        metrics_id = str(uuid4())
        
        # Filter feedback for date range
        relevant_feedback = [
            f for f in self._feedback_store
            if start_date <= f.submitted_at <= end_date
        ]
        
        total_feedback = len(relevant_feedback)
        
        # Overall accuracy metrics
        if total_feedback > 0:
            correct_classifications = sum(
                1 for f in relevant_feedback
                if f.feedback_type == FeedbackType.CORRECT_CLASSIFICATION or
                (f.correct_category is None and f.feedback_type != FeedbackType.INCORRECT_CLASSIFICATION)
            )
            classification_accuracy = correct_classifications / total_feedback
            
            successful_resolutions = sum(1 for f in relevant_feedback if f.resolution_successful)
            resolution_success_rate = successful_resolutions / total_feedback
            
            overall_accuracy = (classification_accuracy + resolution_success_rate) / 2
        else:
            classification_accuracy = 0.0
            resolution_success_rate = 0.0
            overall_accuracy = 0.0
        
        # Calculate per-category metrics
        categories = set(f.original_category for f in relevant_feedback)
        category_metrics = {}
        poor_performing_categories = []
        
        for category in categories:
            cat_metrics = await self.calculate_category_metrics(category, start_date, end_date)
            category_metrics[category] = cat_metrics
            
            # Identify poor performers (< 70% accuracy)
            if cat_metrics.classification_accuracy < 0.7:
                poor_performing_categories.append(category)
        
        return LearningMetrics(
            metrics_id=metrics_id,
            period_start=start_date,
            period_end=end_date,
            total_feedback_count=total_feedback,
            overall_accuracy=overall_accuracy,
            classification_accuracy=classification_accuracy,
            resolution_success_rate=resolution_success_rate,
            category_metrics=category_metrics,
            poor_performing_categories=poor_performing_categories,
            generated_at=datetime.utcnow()
        )
    
    async def prepare_training_dataset(
        self,
        name: str,
        description: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        categories: Optional[List[str]] = None
    ) -> TrainingDataset:
        """
        Prepare a dataset for model retraining.
        
        Aggregates incidents and feedback into a structured training dataset.
        """
        dataset_id = str(uuid4())
        
        # Default to last 90 days if no dates provided
        if not end_date:
            end_date = datetime.utcnow()
        if not start_date:
            start_date = end_date - timedelta(days=90)
        
        # Filter feedback
        relevant_feedback = [
            f for f in self._feedback_store
            if start_date <= f.submitted_at <= end_date
        ]
        
        if categories:
            relevant_feedback = [
                f for f in relevant_feedback
                if f.original_category in categories or (f.correct_category and f.correct_category in categories)
            ]
        
        # Filter incidents (in production, this would query the incident database)
        relevant_incidents = [
            i for i in self._incident_store
            if start_date <= i.created_at <= end_date
        ]
        
        if categories:
            relevant_incidents = [
                i for i in relevant_incidents
                if i.category.value in categories
            ]
        
        # Identify unique categories
        categories_included = set()
        for f in relevant_feedback:
            categories_included.add(f.original_category)
            if f.correct_category:
                categories_included.add(f.correct_category)
        for i in relevant_incidents:
            categories_included.add(i.category.value)
        
        dataset = TrainingDataset(
            dataset_id=dataset_id,
            name=name,
            description=description,
            incident_count=len(relevant_incidents),
            feedback_count=len(relevant_feedback),
            date_range_start=start_date,
            date_range_end=end_date,
            categories_included=list(categories_included),
            created_at=datetime.utcnow()
        )
        
        logger.info(
            f"Training dataset prepared: {dataset.name} "
            f"({dataset.incident_count} incidents, {dataset.feedback_count} feedback entries)"
        )
        
        return dataset
    
    async def retrain_model(self, request: ModelRetrainingRequest) -> ModelRetrainingResult:
        """
        Retrain the AI model with new data.
        
        This is a placeholder for actual ML model retraining.
        In production, this would:
        - Load the training dataset
        - Retrain classification and confidence models
        - Validate model performance
        - Deploy new model version if improvement is significant
        - Rollback if performance degrades
        
        Args:
            request: Retraining request with dataset and parameters
            
        Returns:
            Result of retraining operation
        """
        training_id = str(uuid4())
        training_started_at = datetime.utcnow()
        
        logger.info(f"Starting model retraining (training_id: {training_id})")
        
        try:
            # Prepare dataset
            if request.dataset_id:
                # In production, load specific dataset
                logger.info(f"Using dataset: {request.dataset_id}")
            else:
                # Use all available data
                logger.info("Using all available feedback data")
            
            # Filter feedback based on request parameters
            training_feedback = self._feedback_store
            
            if request.include_feedback_since:
                training_feedback = [
                    f for f in training_feedback
                    if f.submitted_at >= request.include_feedback_since
                ]
            
            if request.categories_to_train:
                training_feedback = [
                    f for f in training_feedback
                    if f.original_category in request.categories_to_train
                ]
            
            # Filter by confidence threshold
            training_feedback = [
                f for f in training_feedback
                if f.original_confidence >= request.min_confidence_threshold
            ]
            
            training_samples_count = len(training_feedback)
            
            if training_samples_count < 10:
                raise ValueError(
                    f"Insufficient training samples: {training_samples_count}. "
                    "Need at least 10 samples for meaningful retraining."
                )
            
            # Simulate training process
            # In production, this would call ML training pipeline
            logger.info(f"Training with {training_samples_count} samples...")
            
            # Calculate validation accuracy (simulated)
            # In production, use proper train/validation split and evaluation
            correct_predictions = sum(
                1 for f in training_feedback
                if f.feedback_type in [FeedbackType.CORRECT_CLASSIFICATION, FeedbackType.RESOLUTION_SUCCESS]
            )
            validation_accuracy = correct_predictions / training_samples_count if training_samples_count > 0 else 0.0
            
            # Generate new model version
            version_parts = self._current_model_version.split('.')
            new_minor = int(version_parts[1]) + 1
            new_model_version = f"{version_parts[0]}.{new_minor}.0"
            
            # Calculate performance improvement by category
            categories_trained = request.categories_to_train or list(set(f.original_category for f in training_feedback))
            performance_improvement = {}
            
            for category in categories_trained:
                # Simulate improvement (in production, compare old vs new model)
                cat_feedback = [f for f in training_feedback if f.original_category == category]
                if cat_feedback:
                    improvement = min(0.15, len(cat_feedback) * 0.001)  # Simulated improvement
                    performance_improvement[category] = improvement
            
            result = ModelRetrainingResult(
                training_id=training_id,
                status="success",
                model_version=new_model_version,
                training_samples_count=training_samples_count,
                validation_accuracy=validation_accuracy,
                categories_trained=categories_trained,
                training_started_at=training_started_at,
                training_completed_at=datetime.utcnow(),
                performance_improvement=performance_improvement
            )
            
            # Update current model version
            self._current_model_version = new_model_version
            self._training_history.append(result)
            
            logger.info(
                f"Model retraining completed: {new_model_version} "
                f"(validation accuracy: {validation_accuracy:.2%})"
            )
            
            return result
            
        except Exception as e:
            error_message = str(e)
            logger.error(f"Model retraining failed: {error_message}", exc_info=True)
            
            result = ModelRetrainingResult(
                training_id=training_id,
                status="failed",
                model_version=self._current_model_version,
                training_samples_count=0,
                validation_accuracy=0.0,
                categories_trained=request.categories_to_train or [],
                training_started_at=training_started_at,
                training_completed_at=datetime.utcnow(),
                error_message=error_message
            )
            
            self._training_history.append(result)
            return result
    
    async def detect_emerging_patterns(
        self,
        min_frequency: int = 5,
        min_confidence: float = 0.7,
        lookback_days: int = 30
    ) -> List[EmergingPatternSuggestion]:
        """
        Detect emerging incident patterns that might warrant new categories.
        
        Analyzes:
        - Common keywords in incident descriptions
        - Similar resolution steps
        - Incidents that don't fit well into existing categories
        - Recurring patterns across multiple incidents
        
        Args:
            min_frequency: Minimum number of incidents to consider a pattern
            min_confidence: Minimum confidence for pattern detection
            lookback_days: How many days to look back
            
        Returns:
            List of suggested new categories based on patterns
        """
        suggestions = []
        
        # Filter recent incidents and feedback
        cutoff_date = datetime.utcnow() - timedelta(days=lookback_days)
        recent_feedback = [
            f for f in self._feedback_store
            if f.submitted_at >= cutoff_date
        ]
        
        # Identify low-confidence predictions (might indicate missing category)
        low_confidence_feedback = [
            f for f in recent_feedback
            if f.original_confidence < 0.75
        ]
        
        if not low_confidence_feedback:
            return suggestions
        
        # Analyze common keywords across low-confidence incidents
        # In production, use NLP techniques like TF-IDF, clustering, topic modeling
        all_notes = ' '.join([f.feedback_notes or '' for f in low_confidence_feedback])
        keywords = self._extract_common_keywords(all_notes)
        
        # Group similar incidents by keywords (simplified clustering)
        keyword_groups: Dict[str, List[ResolutionFeedback]] = defaultdict(list)
        for feedback in low_confidence_feedback:
            notes = feedback.feedback_notes or ''
            for keyword in keywords[:10]:  # Top 10 keywords
                if keyword.lower() in notes.lower():
                    keyword_groups[keyword].append(feedback)
        
        # Identify significant patterns
        for keyword, group in keyword_groups.items():
            if len(group) >= min_frequency:
                # Extract common resolution steps
                common_steps = self._extract_common_resolution_steps(group)
                
                # Calculate pattern confidence based on consistency
                pattern_confidence = min(1.0, len(group) / (min_frequency * 2))
                
                if pattern_confidence >= min_confidence:
                    suggestion = EmergingPatternSuggestion(
                        suggestion_id=str(uuid4()),
                        suggested_category_name=f"emerging_{keyword.lower().replace(' ', '_')}",
                        suggested_category_description=f"Incidents related to {keyword}",
                        incident_sample_ids=[f.incident_id for f in group[:5]],
                        pattern_frequency=len(group),
                        confidence=pattern_confidence,
                        common_keywords=[keyword] + keywords[:4],
                        common_resolution_steps=common_steps,
                        detected_at=datetime.utcnow(),
                        status="pending_review"
                    )
                    
                    suggestions.append(suggestion)
                    
                    logger.info(
                        f"Emerging pattern detected: {suggestion.suggested_category_name} "
                        f"({suggestion.pattern_frequency} incidents, confidence: {suggestion.confidence:.2%})"
                    )
        
        return suggestions
    
    def _extract_common_keywords(self, text: str, top_n: int = 20) -> List[str]:
        """
        Extract common keywords from text.
        
        In production, this would use proper NLP techniques:
        - Remove stop words
        - Lemmatization
        - TF-IDF scoring
        - Named entity recognition
        """
        # Simple implementation: word frequency
        words = text.lower().split()
        
        # Filter out common stop words
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'was', 'are', 'were', 'been', 'be', 'have', 'has', 'had'}
        filtered_words = [w for w in words if w not in stop_words and len(w) > 3]
        
        # Count frequency
        word_counts = Counter(filtered_words)
        
        # Return top N most common
        return [word for word, count in word_counts.most_common(top_n)]
    
    def _extract_common_resolution_steps(self, feedback_group: List[ResolutionFeedback]) -> List[str]:
        """Extract common resolution steps from a group of feedback."""
        all_steps = []
        
        for feedback in feedback_group:
            if feedback.human_resolution_steps:
                for step in feedback.human_resolution_steps:
                    if isinstance(step, dict) and 'description' in step:
                        all_steps.append(step['description'])
        
        # Find most common steps
        step_counts = Counter(all_steps)
        return [step for step, count in step_counts.most_common(5)]
    
    async def get_training_history(self, limit: int = 10) -> List[ModelRetrainingResult]:
        """Get recent model training history."""
        return sorted(
            self._training_history,
            key=lambda r: r.training_started_at,
            reverse=True
        )[:limit]
    
    def get_current_model_version(self) -> str:
        """Get current AI model version."""
        return self._current_model_version
