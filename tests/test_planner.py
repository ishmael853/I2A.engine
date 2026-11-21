
import pytest

from i2a.planner import IntentParser
from i2a.planner.planner import ActionPlanner


@pytest.fixture
def planner():
    return ActionPlanner()


@pytest.fixture
def parser():
    return IntentParser()


def test_open_website(parser, planner):
    intent = parser.parse("Open https://example.com")
    plan = planner.create_plan(intent)

    assert len(plan.steps) == 1
    assert plan.steps[0].action == "open_url"
    assert plan.steps[0].parameters["url"] == "https://example.com"


def test_wait_seconds(parser, planner):
    intent = parser.parse("Wait 10 seconds")
    plan = planner.create_plan(intent)

    assert plan.steps[0].action == "wait"
    assert plan.steps[0].parameters["seconds"] == 10


def test_wait_minutes(parser, planner):
    intent = parser.parse("Wait 2 minutes")
    plan = planner.create_plan(intent)

    assert plan.steps[0].parameters["seconds"] == 120


def test_open_application(parser, planner):
    intent = parser.parse("Open application Notepad")
    plan = planner.create_plan(intent)

    assert plan.steps[0].action == "open_application"
    assert plan.steps[0].parameters["application"] == "Notepad"


def test_unsupported_instruction(parser, planner):
    intent = parser.parse("Make me a cup of coffee")

    with pytest.raises(ValueError):
        planner.create_plan(intent)
