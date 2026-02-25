"""Main agent decision loop."""
import json
import time
from typing import Any
from playwright.async_api import Page

from thirdlayer_prototype.models.action import Action
from thirdlayer_prototype.models.state import BrowserState
from thirdlayer_prototype.db.storage import Storage
from thirdlayer_prototype.agent.observer import Observer
from thirdlayer_prototype.agent.predictor import Predictor
from thirdlayer_prototype.agent.planner import Planner
from thirdlayer_prototype.agent.validator import Validator
from thirdlayer_prototype.agent.executor import Executor
from thirdlayer_prototype.agent.metrics import Metrics


class AgentLoop:
    """Deterministic agent decision loop."""
    
    def __init__(
        self,
        page: Page,
        storage: Storage,
        confidence_threshold: float = 0.5,
        dry_run: bool = False,
    ):
        self.page = page
        self.storage = storage
        self.dry_run = dry_run
        
        self.observer = Observer(page)
        self.predictor = Predictor(storage)
        self.planner = Planner(confidence_threshold)
        self.validator = Validator(page)
        self.executor = Executor(page)
        self.metrics = Metrics()
        
        self.action_history: list[Action] = []
    
    async def step(
        self,
        use_second_order: bool = True,
        ground_truth_action: Action | None = None,
    ) -> dict[str, Any]:
        """Execute one iteration of the agent loop.
        
        Args:
            use_second_order: Whether to use second-order Markov predictions.
            ground_truth_action: Known next action for accuracy measurement (optional).
        
        Returns:
            Dictionary with step results and logs.
        """
        step_start = time.time()
        
        state = await self.observer.observe()
        
        predictions = self.predictor.predict(
            self.action_history,
            k=5,
            use_second_order=use_second_order,
        )
        
        plan = self.planner.plan(predictions)
        
        step_result = {
            "timestamp": time.time(),
            "url": state.url,
            "predictions": [p.to_dict() for p in predictions],
            "plan": plan.to_dict(),
            "validation": None,
            "execution": None,
            "ground_truth_match": None,
        }
        
        if plan.prediction:
            self.metrics.record_confidence(plan.prediction.confidence)
        
        if ground_truth_action and plan.prediction:
            is_correct = plan.prediction.action.signature() == ground_truth_action.signature()
            self.metrics.record_prediction(correct=is_correct)
            step_result["ground_truth_match"] = is_correct
        elif plan.prediction:
            self.metrics.record_prediction(correct=None)
        
        if plan.should_execute and plan.prediction:
            validation = await self.validator.validate(plan.prediction.action)
            step_result["validation"] = validation.to_dict()
            
            if not validation.valid:
                self.metrics.record_unsafe_filtered()
                step_result["execution"] = {
                    "attempted": False,
                    "reason": "validation_failed",
                }
            else:
                if self.dry_run:
                    step_result["execution"] = {
                        "attempted": False,
                        "reason": "dry_run_mode",
                        "would_execute": plan.prediction.action.to_dict(),
                    }
                else:
                    execution = await self.executor.execute(plan.prediction.action)
                    step_result["execution"] = {
                        "attempted": True,
                        **execution.to_dict(),
                    }
                    
                    self.metrics.record_execution(execution.success)
                    
                    if execution.success:
                        self.storage.record_action(
                            plan.prediction.action,
                            url=state.url,
                            success=True,
                        )
                        
                        if len(self.action_history) > 0:
                            self.storage.record_transition_first_order(
                                self.action_history[-1],
                                plan.prediction.action,
                            )
                        
                        if len(self.action_history) > 1:
                            self.storage.record_transition_second_order(
                                self.action_history[-2],
                                self.action_history[-1],
                                plan.prediction.action,
                            )
                        
                        self.action_history.append(plan.prediction.action)
        
        decision_time = time.time() - step_start
        self.metrics.record_decision_time(decision_time)
        step_result["decision_time_ms"] = decision_time * 1000
        
        return step_result
    
    def add_action_to_history(self, action: Action) -> None:
        """Manually add action to history (for recording mode)."""
        self.action_history.append(action)
    
    def get_metrics(self) -> dict[str, Any]:
        """Get current metrics snapshot."""
        return self.metrics.to_dict()
