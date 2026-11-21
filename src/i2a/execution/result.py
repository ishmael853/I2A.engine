from dataclasses import dataclass, field
from typing import Any

@dataclass
class ActionResult:
    """Stores the outcome of one executed action."""

    step_id: str
    action: str
    success: bool
    message: str
    output: Any = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "step_id": self.step_id,
            "action": self.action,
            "success": self.success,
            "message": self.message,
            "output": self.output,
            "error": self.error,
        }

@dataclass
class WorkflowExecutionResult:
    """Stores the outcome of an entire workflow execution."""

    workflow_name: str
    success: bool
    results: list[ActionResult] = field(default_factory=list)

    @property
    def total_steps(self) -> int:
        return len(self.results)

    @property
    def successful_steps(self) -> int:
        return sum(result.success for result in self.results)

    @property
    def failed_steps(self) -> int:
        return sum(not result.success for result in self.results)

    def to_dict(self) -> dict[str, Any]:
        return {
            "workflow_name": self.workflow_name,
            "success": self.success,
            "total_steps": self.total_steps,
            "successful_steps": self.successful_steps,
            "failed_steps": self.failed_steps,
            "results": [
                result.to_dict() for result in self.results
            ],
        }