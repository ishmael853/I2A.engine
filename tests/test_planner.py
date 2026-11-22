
import pytest

from i2a.planner import IntentParser
from i2a.planner.planner import ActionPlanner
from i2a.execution.application_discovery import (
    DiscoveredApplication,
)


class FakeApplicationDiscovery:
    """Provides predictable applications for planner tests."""

    def discover(self):
        return [
            DiscoveredApplication(
                name="Notepad",
                executable=r"C:\Windows\System32\notepad.exe",
            ),
            DiscoveredApplication(
                name="Visual Studio Code",
                executable=r"C:\Program Files\VSCode\Code.exe",
            ),
            DiscoveredApplication(
                name="Android Studio",
                executable=r"C:\Program Files\Android Studio\studio64.exe",
            ),
            DiscoveredApplication(
                name="Python 3.14 (64-bit)",
                executable=r"C:\Python314\python.exe",
            ),
        ]


@pytest.fixture
def planner():
    return ActionPlanner(
        application_discovery=FakeApplicationDiscovery()
    )


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


def test_open_visual_studio_code(parser, planner):
    intent = parser.parse("Open Visual Studio Code")
    plan = planner.create_plan(intent)

    assert plan.steps[0].action == "open_application"
    assert plan.steps[0].parameters["application"] == "Visual Studio Code"


def test_open_android_studio(parser, planner):
    intent = parser.parse("Launch Android Studio")
    plan = planner.create_plan(intent)

    assert plan.steps[0].action == "open_application"
    assert plan.steps[0].parameters["application"] == "Android Studio"


def test_longest_application_name_match(parser, planner):
    intent = parser.parse("Open Python 3.14 (64-bit)")
    plan = planner.create_plan(intent)

    assert plan.steps[0].action == "open_application"
    assert plan.steps[0].parameters["application"] == "Python 3.14 (64-bit)"


def test_unsupported_instruction(parser, planner):
    intent = parser.parse("Make me a cup of coffee")

    with pytest.raises(ValueError):
        planner.create_plan(intent)

def test_open_application_with_folder_path(parser, planner):
    folder = r"C:\Users\ishma\OneDrive\Desktop\Django\Hospital"

    intent = parser.parse(
        f"Open Visual Studio Code at {folder}"
    )

    plan = planner.create_plan(intent)

    assert len(plan.steps) == 1
    assert plan.steps[0].action == "open_application"
    assert plan.steps[0].parameters["application"] == (
        "Visual Studio Code"
    )
    assert plan.steps[0].parameters["path"] == folder