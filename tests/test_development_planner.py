import json

import pytest

from i2a.development.planner import DevelopmentPlanner


VALID_PLAN = {
    "project_name": "Calculator",
    "description": "A Python calculator.",
    "technology_stack": ["Python"],
    "requirements": ["Support basic arithmetic."],
    "development_steps": [
        {
            "step": 1,
            "title": "Create calculator",
            "description": "Implement arithmetic functions.",
        }
    ],
    "testing_strategy": ["Use pytest."],
}


class FakeAssistant:
    """Simulates AI responses for development planner tests."""

    def __init__(self, responses):
        self.responses = iter(responses)
        self.calls = 0
        self.last_prompt = None

    def ask(self, instruction):
        self.calls += 1
        self.last_prompt = instruction
        return next(self.responses)


def test_create_valid_development_plan():
    assistant = FakeAssistant([json.dumps(VALID_PLAN)])
    planner = DevelopmentPlanner(assistant=assistant)

    plan = planner.create_plan("Build a calculator.")

    assert plan == VALID_PLAN
    assert assistant.calls == 1


def test_retries_when_required_field_is_missing():
    invalid_plan = VALID_PLAN.copy()
    invalid_plan.pop("testing_strategy")

    assistant = FakeAssistant([
        json.dumps(invalid_plan),
        json.dumps(VALID_PLAN),
    ])

    planner = DevelopmentPlanner(assistant=assistant)
    plan = planner.create_plan("Build a calculator.")

    assert plan == VALID_PLAN
    assert assistant.calls == 2


def test_rejects_invalid_plan_after_retry():
    assistant = FakeAssistant([
        "{}",
        "{}",
    ])

    planner = DevelopmentPlanner(assistant=assistant)

    with pytest.raises(ValueError):
        planner.create_plan("Build a calculator.")

    assert assistant.calls == 2


def test_rejects_empty_instruction():
    planner = DevelopmentPlanner(
        assistant=FakeAssistant([])
    )

    with pytest.raises(ValueError):
        planner.create_plan("")


def test_rejects_incomplete_development_step():
    invalid_plan = VALID_PLAN.copy()
    invalid_plan["development_steps"] = [
        {"step": 1, "title": "Incomplete"}
    ]

    assistant = FakeAssistant([
        json.dumps(invalid_plan),
        json.dumps(invalid_plan),
    ])

    planner = DevelopmentPlanner(assistant=assistant)

    with pytest.raises(ValueError):
        planner.create_plan("Build a calculator.")

    assert assistant.calls == 2


def test_create_plan_with_workspace_context(tmp_path):
    project = tmp_path / "sample_project"
    project.mkdir()

    (project / "main.py").write_text(
        "print('hello')",
        encoding="utf-8",
    )

    assistant = FakeAssistant([json.dumps(VALID_PLAN)])
    planner = DevelopmentPlanner(assistant=assistant)

    plan = planner.create_plan(
        "Improve this Python project.",
        workspace_path=project,
    )

    assert plan == VALID_PLAN
    assert "EXISTING PROJECT WORKSPACE" in assistant.last_prompt
    assert "main.py" in assistant.last_prompt


def test_create_plan_rejects_invalid_workspace(tmp_path):
    assistant = FakeAssistant([json.dumps(VALID_PLAN)])
    planner = DevelopmentPlanner(assistant=assistant)

    missing_workspace = tmp_path / "missing_project"

    with pytest.raises(FileNotFoundError):
        planner.create_plan(
            "Improve this project.",
            workspace_path=missing_workspace,
        )

    assert assistant.calls == 0
