"""
calm.lifecycle.manager — Core Lifecycle Manager orchestrating state transitions and memory limits.
"""

from typing import Dict, List, Optional, Set, Any
from calm.models.app_state import LifecycleState, StateTransition, TransitionCost
from calm.models.prediction import PredictionResult
from calm.telemetry.collector import TelemetryCollector
from calm.telemetry.context import ContextExtractor
from calm.policy.policy_engine import CALMPolicyEngine, PolicyDecision
from calm.lifecycle.transitions import TransitionCostModel
from calm.lifecycle.states import get_next_demotion_state, get_next_promotion_state
from calm.utils.config import CALMConfig


class LifecycleManager:
    """
    Manages the lifecycle state of all memory items / applications.
    Enforces RAM budgets, executes policy transitions, and logs performance metrics.
    """

    def __init__(
        self,
        config: CALMConfig,
        all_items: List[str],
        policy_engine: Optional[CALMPolicyEngine] = None,
    ):
        self.config = config
        self.all_items = list(all_items)
        self.states: Dict[str, LifecycleState] = {
            item: LifecycleState.ARCHIVED for item in self.all_items
        }
        self.telemetry = TelemetryCollector(self.all_items)
        self.context_extractor = ContextExtractor(self.all_items)
        self.policy_engine = policy_engine or CALMPolicyEngine(config)
        self.tick: int = 0
        self.transition_log: List[StateTransition] = []
        self.reclaimed_memory_history: List[float] = []

    def get_effective_ram(self, item_id: str, state: Optional[LifecycleState] = None) -> int:
        """Returns RAM in MB for item in specified or current state."""
        st = state if state is not None else self.states[item_id]
        return self.config.effective_ram(item_id, st.value)

    def total_ram(self) -> int:
        """Calculates total resident RAM currently consumed across all items."""
        return sum(self.get_effective_ram(item) for item in self.all_items)

    def apply_transition(
        self,
        item_id: str,
        to_state: LifecycleState,
        reason: str = "",
        confidence: float = 0.0,
        priority: float = 0.0,
    ) -> Optional[StateTransition]:
        """Applies a state transition and logs its cost."""
        from_state = self.states[item_id]
        if from_state == to_state:
            return None

        cost = TransitionCostModel.calculate_cost(
            from_state=from_state,
            to_state=to_state,
            item_base_ram_mb=self.config.app_ram.get(item_id, 500),
            compressed_factor=self.config.storage.compressed_ram_factor,
        )

        self.states[item_id] = to_state
        self.telemetry.get_or_create(item_id).reset_state_timer()

        transition = StateTransition(
            tick=self.tick,
            item_id=item_id,
            from_state=from_state,
            to_state=to_state,
            cost=cost,
            reason=reason,
            confidence=confidence,
            priority=priority,
        )
        self.transition_log.append(transition)
        return transition

    def step(
        self,
        requested_item: str,
        prediction_result: Optional[PredictionResult] = None,
        context_importances: Optional[Dict[str, float]] = None,
        # Ablation overrides
        enable_prediction: bool = True,
        enable_burst: bool = True,
        enable_hysteresis: bool = True,
        enable_pressure_trend: bool = True,
        enable_compression: bool = True,
        enable_context: bool = True,
    ) -> Dict[str, Any]:
        """
        Executes one complete simulation tick.
        CRITICAL FAIRNESS RULE: Records pre-transition state BEFORE applying any modifications!
        """
        self.tick += 1

        # 1. Capture exact state BEFORE modification for fair latency and hit-rate scoring
        pre_launch_state = self.states[requested_item]
        is_cache_hit = pre_launch_state in (
            LifecycleState.ACTIVE,
            LifecycleState.CACHED,
            LifecycleState.COMPRESSED,
        )
        launch_latency = self.config.launch_times.get(pre_launch_state.value, 2.40)

        # 2. Update telemetry
        self.telemetry.record_access(requested_item, self.tick)
        self.telemetry.advance_tick()
        self.policy_engine.pressure_engine.update(self.total_ram(), self.config.ram_limit_mb)

        # 3. Evaluate policy engine
        decision = self.policy_engine.evaluate(
            all_items=self.all_items,
            current_states=self.states,
            foreground_item=requested_item,
            prediction_result=prediction_result,
            telemetry_collector=self.telemetry,
            current_tick=self.tick,
            context_extractor=self.context_extractor,
            context_importances=context_importances,
            enable_prediction=enable_prediction,
            enable_burst=enable_burst,
            enable_hysteresis=enable_hysteresis,
            enable_pressure_trend=enable_pressure_trend,
            enable_compression=enable_compression,
            enable_context=enable_context,
        )

        # 4. Apply proactive prewarming
        for item in decision.items_to_prewarm:
            target_st = decision.target_states.get(item, LifecycleState.COMPRESSED)
            if self.total_ram() + self.get_effective_ram(item, target_st) <= self.config.ram_limit_mb * 0.95:
                self.apply_transition(
                    item,
                    target_st,
                    reason="prewarm_prediction",
                    confidence=decision.prediction_confidence,
                    priority=decision.priority_scores.get(item, 0.0),
                )

        # 5. Apply proactive compression
        for item in decision.items_to_compress:
            if self.states[item] == LifecycleState.CACHED:
                self.apply_transition(
                    item,
                    LifecycleState.COMPRESSED,
                    reason="proactive_pressure_compression",
                    priority=decision.priority_scores.get(item, 0.0),
                )

        # 6. Promote foreground to ACTIVE
        self.apply_transition(
            requested_item,
            LifecycleState.ACTIVE,
            reason="foreground_launch",
            priority=1.0,
        )

        # 7. Demote any stale non-foreground ACTIVE items to CACHED
        for item in self.all_items:
            if item != requested_item and self.states[item] == LifecycleState.ACTIVE:
                self.apply_transition(
                    item,
                    LifecycleState.CACHED,
                    reason="foreground_yield",
                    priority=decision.priority_scores.get(item, 0.0),
                )

        # 8. Enforce hard RAM limit if exceeded
        reclaimed_mb = 0.0
        if self.total_ram() > self.config.ram_limit_mb:
            reclaimed_mb = self._enforce_ram_budget(
                exclude_item=requested_item,
                priority_scores=decision.priority_scores,
                enable_compression=enable_compression,
            )

        # Final pressure update
        self.policy_engine.pressure_engine.update(self.total_ram(), self.config.ram_limit_mb)
        self.reclaimed_memory_history.append(reclaimed_mb)

        return {
            "tick": self.tick,
            "requested_item": requested_item,
            "pre_launch_state": pre_launch_state,
            "is_cache_hit": is_cache_hit,
            "launch_latency": launch_latency,
            "post_states": dict(self.states),
            "total_ram": self.total_ram(),
            "pressure_level": self.policy_engine.pressure_engine.level,
            "pressure_trend": self.policy_engine.pressure_engine.trend,
            "priority_scores": decision.priority_scores,
            "reclaimed_mb": reclaimed_mb,
        }

    def _enforce_ram_budget(
        self,
        exclude_item: str,
        priority_scores: Dict[str, float],
        enable_compression: bool = True,
    ) -> float:
        """
        Demotes lowest priority items step-by-step until total RAM is within budget.
        Returns total memory reclaimed in MB.
        """
        ram_before = self.total_ram()
        attempts = 0

        while self.total_ram() > self.config.ram_limit_mb and attempts < 30:
            # Candidates that are not excluded and not already ARCHIVED
            candidates = [
                item for item in self.all_items
                if item != exclude_item and self.states[item] != LifecycleState.ARCHIVED
            ]
            if not candidates:
                break

            # Sort by priority ascending (lowest priority demoted first)
            candidates.sort(key=lambda a: priority_scores.get(a, 0.0))
            target_item = candidates[0]
            current_st = self.states[target_item]

            # Decide next demotion state
            if enable_compression and current_st == LifecycleState.CACHED:
                nxt = LifecycleState.COMPRESSED
            else:
                nxt = LifecycleState.ARCHIVED

            self.apply_transition(
                target_item,
                nxt,
                reason="hard_ram_budget_enforcement",
                priority=priority_scores.get(target_item, 0.0),
            )
            attempts += 1

        ram_after = self.total_ram()
        return max(0.0, float(ram_before - ram_after))
