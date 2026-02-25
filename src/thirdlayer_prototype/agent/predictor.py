"""Predictor generates candidate next actions using Markov model."""
from dataclasses import dataclass
from typing import Any

from thirdlayer_prototype.models.action import Action
from thirdlayer_prototype.db.storage import Storage


@dataclass
class Prediction:
    """Predicted action with confidence score."""
    
    action: Action
    confidence: float
    source: str
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "action": self.action.to_dict(),
            "confidence": self.confidence,
            "source": self.source,
        }


class Predictor:
    """Markov-based action predictor."""
    
    def __init__(self, storage: Storage):
        self.storage = storage
    
    def predict_first_order(self, current_action: Action, k: int = 5) -> list[Prediction]:
        """Predict next actions using first-order Markov model.
        
        Returns top K predictions sorted by confidence (descending).
        """
        transitions = self.storage.get_first_order_transitions(current_action)
        
        if not transitions:
            return []
        
        total_count = sum(t["count"] for t in transitions)
        
        predictions = []
        for trans in transitions[:k]:
            action = Action.from_json(trans["to_action"])
            confidence = trans["count"] / total_count
            predictions.append(
                Prediction(action=action, confidence=confidence, source="first_order")
            )
        
        return predictions
    
    def predict_second_order(
        self, prev_action: Action, current_action: Action, k: int = 5
    ) -> list[Prediction]:
        """Predict next actions using second-order Markov model.
        
        Returns top K predictions sorted by confidence (descending).
        """
        transitions = self.storage.get_second_order_transitions(prev_action, current_action)
        
        if not transitions:
            return []
        
        total_count = sum(t["count"] for t in transitions)
        
        predictions = []
        for trans in transitions[:k]:
            action = Action.from_json(trans["to_action"])
            confidence = trans["count"] / total_count
            predictions.append(
                Prediction(action=action, confidence=confidence, source="second_order")
            )
        
        return predictions
    
    def predict(
        self, action_history: list[Action], k: int = 5, use_second_order: bool = True
    ) -> list[Prediction]:
        """Predict next actions using best available model.
        
        Tries second-order if available and enabled, falls back to first-order.
        """
        if not action_history:
            return []
        
        current_action = action_history[-1]
        
        if use_second_order and len(action_history) >= 2:
            prev_action = action_history[-2]
            second_order_preds = self.predict_second_order(prev_action, current_action, k)
            
            if second_order_preds:
                return second_order_preds
        
        return self.predict_first_order(current_action, k)
