from i2a.core import WorkflowPlan
from i2a.actions import ActionRegistry, create_default_registry

class WorkflowValidator:
    """Validates workflow plans before execution."""

    def __init__(
            self,
            registry: ActionRegistry | None = None,
    ) -> None:
        self.registry = registry or create_default_registry()

    def validate(self, plan: WorkflowPlan) -> list[str]:
        errors = []

        if not isinstance(plan, WorkflowPlan):
            return ["Invalid workflow plan."]

        if not plan.name.strip():
            errors.append("Workflow name cannot be empty.")

        if not plan.goal.strip():
            errors.append("Workflow goal cannot be empty")

        if not plan.steps:
            errors.append("Workflow must contain at least one step.")

        seen_step_ids = set()

        for index, step in enumerate(plan.steps, start=1):

            if not step.step_id.strip():
                errors.append(
                    f"Step {index} has an empty step ID."
                )

            elif step.step_id in seen_step_ids:
                errors.append(
                    f"Duplicate step ID: '{step.step_id}'."
                )

            seen_step_ids.add(step.step_id)

            if not step.action.strip():
                errors.append(
                    f"Step {index} has an empty action name."
                )
                continue

            parameter_errors = self.registry.validate_parameters(
                step.action,
                step.parameters,
            )

            for error in parameter_errors:
                errors.append(f"Step {index}: {error}")

        return errors

    def is_valid(self, plan: WorkflowPlan) -> bool:
        return len(self.validate(plan)) == 0