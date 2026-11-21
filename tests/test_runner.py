from unittest.mock  import Mock

from i2a.core import Action, WorkflowPlan
from i2a.execution.result import ActionResult
from i2a.execution.runner import WorkflowRunner

def test_runner_executes_valid_workflow():
    validator = Mock()
    validator.validate.return_value = []

    executor = Mock()
    executor.execute.return_value = []

    executor = Mock()
    executor.execute.return_value = ActionResult(
        step_id="step_1",
        action="wait",
        success=True,
        message="Wait completed",
    )

    runner = WorkflowRunner(validator, executor)

    plan = WorkflowPlan(
        name="Test Workflow",
        goal="Test execution",
        steps=[
            Action(
                action="wait",
                parameters={"seconds": 5},
                step_id="step_1",
            )
        ],
    )

    result = runner.run(plan)

    assert result.success is True
    assert result.total_steps == 1
    assert result.successful_steps == 1
    executor.execute.assert_called_once()

def test_runner_block_invalid_workflow():
    validator = Mock()
    validator.validate.return_value = ["Invalid workflow"]

    executor = Mock()

    runner = WorkflowRunner(validator, executor)

    plan = WorkflowPlan(
        name="Invalid Workflow",
        goal="Test validation",
    )

    result = runner.run(plan)

    assert result.success is False
    assert result.results[0].action == "validation"
    executor.execute.assert_not_called()

def test_runner_stops_after_execution_failure():
    validator = Mock()
    validator.validate.return_value = []

    executor = Mock()
    executor.execute.return_value = ActionResult(
        step_id="step_1",
        action="wait",
        success=False,
        message="execution failed",
        error="Test error.",
    )

    runner = WorkflowRunner(validator, executor)

    plan = WorkflowPlan(
        name="Failure Workflow",
        goal="Test failure handling",
        steps=[
            Action(action="wait", step_id="step_1"),
            Action(action="wait", step_id="step_2"),
        ],
    )

    result = runner.run(plan)

    assert result.success is False
    assert result.total_steps == 1
    executor.execute.assert_called_once()