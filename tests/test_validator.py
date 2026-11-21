import pytest

from i2a.core import Action, WorkflowPlan
from i2a.actions import ActionDefinition, ActionRegistry
from i2a.validation.validator import WorkflowValidator

@pytest.fixture
def validator():
    registry = ActionRegistry()

    registry.register(
        ActionDefinition(
            name="open_url",
            description="Open a website",
            required_parameters=["url"],
        )
    )

    registry.register(
        ActionDefinition(
            name="wait",
            description="Wait for a specified duration",
            required_parameters=["seconds"],
        )
    )

    return WorkflowValidator(registry)

def test_valid_workflow(validator):
    plan = WorkflowPlan(
        name="Test workflow",
        goal="Open a website",
        steps=[
            Action(
                action="open_url",
                parameters={"url": "https://example.com"},
                step_id="step_1",
            )
        ],
    )

    assert validator.is_valid(plan)

def test_unknown_action(validator):
    plan = WorkflowPlan(
        name="Test workflow",
        goal="Perform unknown action",
        steps=[
            Action(
                action="unknown_action",
                step_id="step_1",
            )
        ],
    )

    assert not validator.is_valid(plan)

def test_missing_required_parameter(validator):
    plan = WorkflowPlan(
        name="Test workflow",
        goal="Open a website",
        steps=[
            Action(
                action="open_url",
                parameters={},
                step_id="step_1",
            )
        ],
    )

    errors = validator.validate(plan)

    assert any("Missing required parameter" in error for error in errors)

def test_duplicate_step_ids(validator):
    plan = WorkflowPlan(
        name="Test workflow",
        goal="wait twice",
        steps=[
            Action(action="wait", parameters={"seconds": 5}, step_id="step_1"),
            Action(action="wait", parameters={"seconds": 10}, step_id="step_1"),
        ],
    )

    errors = validator.validate(plan)

    assert any("Duplicate step ID" in error for error in errors)

def test_empty_workflow(validator):
    plan = WorkflowPlan(
        name="Test workflow",
        goal="Nothing",
        steps=[],
    )

    assert not validator.is_valid(plan)