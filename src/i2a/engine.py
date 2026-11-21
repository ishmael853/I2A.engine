from i2a.core import WorkflowPlan
from i2a.planner.parser import IntentParser
from i2a.planner.planner import ActionPlanner
from i2a.execution.runner import WorkflowRunner
from i2a.execution.result import WorkflowExecutionResult

class I2AEngine:
    """Coordinates instruction parsing, planning, and execution."""

    def __init__(
            self,
            parser: IntentParser | None = None,
            planner: ActionPlanner | None = None,
            runner: WorkflowRunner | None = None,
    ) -> None:
        self.parser = parser or IntentParser()
        self.planner = planner or ActionPlanner()
        self.runner = runner or WorkflowRunner()

    def create_plan(self, instruction: str) -> WorkflowPlan:
        """Convert a natural-language instruction into a workflow plan."""

        intent = self.parser.parse(instruction)
        return self.planner.create_plan(intent)

    def run(self, instruction: str) -> WorkflowExecutionResult:
        """Parse, plan, validate, and execute an instruction."""

        plan = self.create_plan(instruction)
        return self.runner.run(plan)