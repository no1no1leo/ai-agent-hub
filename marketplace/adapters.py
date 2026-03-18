"""
Adapter interfaces for routing work to different solver types.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class SolverCapabilities:
    agent_id: str
    model_name: str
    domains: List[str] = field(default_factory=list)
    modalities: List[str] = field(default_factory=lambda: ["text"])
    tools: List[str] = field(default_factory=list)
    latency_class: str = "balanced"
    cost_class: str = "medium"
    max_context_tokens: int = 0
    trust_level: str = "standard"


class BaseSolverAdapter(ABC):
    """Minimal adapter contract for pluggable solver backends."""

    @abstractmethod
    def get_capabilities(self) -> SolverCapabilities:
        raise NotImplementedError

    @abstractmethod
    def can_accept(self, task: Dict[str, Any]) -> bool:
        raise NotImplementedError

    @abstractmethod
    def estimate_bid(self, task: Dict[str, Any], market_state: Dict[str, Any]) -> float:
        raise NotImplementedError

    @abstractmethod
    def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError


class AlgoSolverAdapter(BaseSolverAdapter):
    """Adapter wrapper for existing algorithmic solvers."""

    def __init__(self, agent_id: str, model_name: str, domains: List[str] | None = None):
        self.agent_id = agent_id
        self.model_name = model_name
        self.domains = domains or ["general"]

    def get_capabilities(self) -> SolverCapabilities:
        return SolverCapabilities(
            agent_id=self.agent_id,
            model_name=self.model_name,
            domains=self.domains,
            modalities=["text"],
            tools=[],
            latency_class="fast",
            cost_class="low",
            trust_level="simulated",
        )

    def can_accept(self, task: Dict[str, Any]) -> bool:
        return float(task.get("max_budget", 0)) > 0

    def estimate_bid(self, task: Dict[str, Any], market_state: Dict[str, Any]) -> float:
        expected_tokens = int(task.get("expected_tokens", 0))
        bid_floor = float(market_state.get("bid_floor", 0.1))
        return max(bid_floor, expected_tokens / 10000)

    def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "status": "completed",
            "result": f"Simulated execution by {self.agent_id}",
            "task_id": task.get("task_id"),
        }


class ExternalHttpSolverAdapter(BaseSolverAdapter):
    """Placeholder for future external HTTP-based workers."""

    def __init__(self, agent_id: str, endpoint: str, model_name: str = "external-worker"):
        self.agent_id = agent_id
        self.endpoint = endpoint
        self.model_name = model_name

    def get_capabilities(self) -> SolverCapabilities:
        return SolverCapabilities(
            agent_id=self.agent_id,
            model_name=self.model_name,
            domains=["general"],
            modalities=["text"],
            tools=["http"],
            latency_class="balanced",
            cost_class="medium",
            trust_level="external",
        )

    def can_accept(self, task: Dict[str, Any]) -> bool:
        return bool(self.endpoint) and bool(task.get("description"))

    def estimate_bid(self, task: Dict[str, Any], market_state: Dict[str, Any]) -> float:
        expected_tokens = int(task.get("expected_tokens", 0))
        return max(0.25, expected_tokens / 8000)

    def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "status": "not_implemented",
            "endpoint": self.endpoint,
            "task_id": task.get("task_id"),
        }


class ResearchSolverAdapter(ExternalHttpSolverAdapter):
    """Specialized adapter profile for research-oriented workers."""

    def __init__(self, agent_id: str, endpoint: str, model_name: str = "research-worker"):
        super().__init__(agent_id=agent_id, endpoint=endpoint, model_name=model_name)

    def get_capabilities(self) -> SolverCapabilities:
        return SolverCapabilities(
            agent_id=self.agent_id,
            model_name=self.model_name,
            domains=["research", "market-intel", "technical-analysis"],
            modalities=["text", "web", "documents"],
            tools=["web", "browser", "citations", "memory"],
            latency_class="balanced",
            cost_class="medium",
            trust_level="verified",
            max_context_tokens=128000,
        )

    def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "status": "not_implemented",
            "task_id": task.get("task_id"),
            "summary": "Research solver stub executed.",
            "sources": [],
            "notes": "Connect this adapter to a real research agent next.",
        }
