"""Planner selects which action to execute from predictions."""
from dataclasses import dataclass
from typing import Any

from thirdlayer_prototype.agent.predictor import Prediction


@dataclass
class Plan:
    """Selected action with execution decision."""
    
    prediction: Prediction | None
    should_execute: bool
    reason: str
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "prediction": self.prediction.to_dict() if self.prediction else None,
            "should_execute": self.should_execute,
            "reason": self.reason,
        }


class Planner:
    """Selects action to execute based on confidence threshold."""
    
    def __init__(self, confidence_threshold: float = 0.5):
        self.confidence_threshold = confidence_threshold
    
    def plan(self, predictions: list[Prediction]) -> Plan:
        """Select action to execute from predictions.
        
        Returns Plan with execution decision and reason.
        """
        if not predictions:
            return Plan(
                prediction=None,
                should_execute=False,
                reason="no_predictions_available",
            )
        
        top_prediction = predictions[0]
        
        if top_prediction.confidence < self.confidence_threshold:
            return Plan(
                prediction=top_prediction,
                should_execute=False,
                reason=f"confidence_too_low_{top_prediction.confidence:.2f}_below_{self.confidence_threshold}",
            )
        
        return Plan(
            prediction=top_prediction,
            should_execute=True,
            reason=f"confidence_above_threshold_{top_prediction.confidence:.2f}",
        )
