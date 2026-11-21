from i2a.core import WorkflowPlan
from i2a.execution.executor import ActionExecutor
from i2a.execution.result import ActionResult, WorkflowExecutionResult
from i2a.validation.validator import WorkflowValidator

class WorkflowRunner:
    """Validates and executes complete I2A workflow plans."""

    def __init__(
            self,
            validator: WorkflowValidator | None = None,
            executor: ActionExecutor | None = None,
    ) -> None:
        self.validator = validator or WorkflowValidator()
        self.executor = executor or ActionExecutor()

    def run(self, plan: WorkflowPlan) -> WorkflowExecutionResult:
        """Validates a workflow and execute its actions in order."""

        validation_errors = self.validator.validate(plan)

        if validation_errors:
            results = [
                ActionResult(
                    step_id="",
                    action="validation",
                    success=False,
                    message="Workflow validation failed.",
                    error="; ".join(validation_errors),
                )
            ]

            return WorkflowExecutionResult(
                workflow_name=plan.name,
                success=False,
                results=results
            )

        results: list[ActionResult] = []

        for step in plan.steps:
            result = self.executor.execute(step)
            results.append(result)

            if not result.success:
                return WorkflowExecutionResult(
                    workflow_name=plan.name,
                    success=False,
                    results=results,
                )

        return WorkflowExecutionResult(
            workflow_name=plan.name,
            success=True,
            results=results,
        )