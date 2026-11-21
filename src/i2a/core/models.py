from dataclasses import dataclass, field
from typing import Any

@dataclass
class Action:
    """Represents one structured automation action."""

    action: str
    parameters: dict[str, any] = field(default_factory=dict)
    description: str = ""
    step_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "action": self.action,
            "parameters": self.parameters,
            "description": self.description,
            "step_id": self.step_id,
        }

@dataclass
class WorkflowPlan:
    """Represents a complete plan generated from a user instruction."""

    name: str
    goal: str
    steps: list[Action] = field(default_factory=list)
    version: str = "1.0"

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "goal": self.goal,
            "version": self.version,
            "steps": [step.to_dict() for step in self.steps],
        }