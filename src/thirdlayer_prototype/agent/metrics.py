"""Metrics tracking and reporting."""
from dataclasses import dataclass, field
from typing import Any
import time


@dataclass
class Metrics:
    """System metrics tracker."""
    
    total_predictions: int = 0
    correct_predictions: int = 0
    total_executions: int = 0
    successful_executions: int = 0
    unsafe_filtered: int = 0
    total_confidence: float = 0.0
    decision_times: list[float] = field(default_factory=list)
    start_time: float = field(default_factory=time.time)
    
    def record_prediction(self, correct: bool | None = None) -> None:
        """Record a prediction attempt.
        
        Args:
            correct: Whether prediction matched ground truth (None if unknown).
        """
        self.total_predictions += 1
        if correct is not None and correct:
            self.correct_predictions += 1
    
    def record_execution(self, success: bool) -> None:
        """Record an execution attempt."""
        self.total_executions += 1
        if success:
            self.successful_executions += 1
    
    def record_unsafe_filtered(self) -> None:
        """Record an action filtered by safety validator."""
        self.unsafe_filtered += 1
    
    def record_confidence(self, confidence: float) -> None:
        """Record confidence score."""
        self.total_confidence += confidence
    
    def record_decision_time(self, duration: float) -> None:
        """Record decision loop duration in seconds."""
        self.decision_times.append(duration)
    
    def get_prediction_accuracy(self) -> float:
        """Calculate prediction accuracy when ground truth available."""
        if self.total_predictions == 0:
            return 0.0
        return self.correct_predictions / self.total_predictions
    
    def get_execution_success_rate(self) -> float:
        """Calculate execution success rate."""
        if self.total_executions == 0:
            return 0.0
        return self.successful_executions / self.total_executions
    
    def get_average_confidence(self) -> float:
        """Calculate average confidence across predictions."""
        if self.total_predictions == 0:
            return 0.0
        return self.total_confidence / self.total_predictions
    
    def get_average_decision_time(self) -> float:
        """Calculate average decision loop time in seconds."""
        if not self.decision_times:
            return 0.0
        return sum(self.decision_times) / len(self.decision_times)
    
    def get_uptime(self) -> float:
        """Get system uptime in seconds."""
        return time.time() - self.start_time
    
    def to_dict(self) -> dict[str, Any]:
        """Convert metrics to dictionary for API response."""
        return {
            "total_predictions": self.total_predictions,
            "correct_predictions": self.correct_predictions,
            "prediction_accuracy": self.get_prediction_accuracy(),
            "total_executions": self.total_executions,
            "successful_executions": self.successful_executions,
            "execution_success_rate": self.get_execution_success_rate(),
            "average_confidence": self.get_average_confidence(),
            "unsafe_filtered": self.unsafe_filtered,
            "average_decision_time_ms": self.get_average_decision_time() * 1000,
            "uptime_seconds": self.get_uptime(),
        }
