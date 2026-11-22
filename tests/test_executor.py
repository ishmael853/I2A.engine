from unittest.mock import patch

from i2a.core import Action
from i2a.execution.executor import ActionExecutor
from i2a.execution.application_discovery import (
    ApplicationDiscovery,
    DiscoveredApplication,
)


def test_unsupported_action():
    executor = ActionExecutor()

    action = Action(
        action="unknown_action",
        step_id="step_1",
    )

    result = executor.execute(action)

    assert result.success is False
    assert "not supported" in result.message.lower()


@patch("i2a.execution.executor.webbrowser.open", return_value=True)
def test_open_url(mock_open):
    executor = ActionExecutor()

    action = Action(
        action="open_url",
        parameters={"url": "https://example.com"},
        step_id="step_1",
    )

    result = executor.execute(action)

    assert result.success is True
    assert result.output == "https://example.com"
    mock_open.assert_called_once_with("https://example.com")


@patch("i2a.execution.executor.time.sleep")
def test_wait(mock_sleep):
    executor = ActionExecutor()

    action = Action(
        action="wait",
        parameters={"seconds": 5},
        step_id="step_1",
    )

    result = executor.execute(action)

    assert result.success is True
    assert result.output == 5
    mock_sleep.assert_called_once_with(5)


def test_invalid_wait_duration():
    executor = ActionExecutor()

    action = Action(
        action="wait",
        parameters={"seconds": 0},
        step_id="step_1",
    )

    result = executor.execute(action)

    assert result.success is False
    assert result.error is not None


def test_unapproved_application():
    executor = ActionExecutor()

    action = Action(
        action="open_application",
        parameters={"application": "unknown_app"},
        step_id="step_1",
    )

    result = executor.execute(action)

    assert result.success is False
    assert result.error is not None
    assert "not approved" in result.error.lower()


@patch("i2a.execution.executor.subprocess.Popen")
@patch.object(
    ApplicationDiscovery,
    "find",
    return_value=DiscoveredApplication(
        name="notepad",
        executable=r"C:\Windows\System32\notepad.exe",
    ),
)
def test_open_discovered_application(mock_find, mock_popen):
    mock_popen.return_value.pid = 1234

    executor = ActionExecutor()

    action = Action(
        action="open_application",
        parameters={"application": "notepad"},
        step_id="step_1",
    )

    result = executor.execute(action)

    assert result.success is True
    assert result.output == {"process_id": 1234}
    assert result.message == "Started application: notepad"

    mock_find.assert_called_once_with("notepad")
    mock_popen.assert_called_once_with(
        [r"C:\Windows\System32\notepad.exe"],
        shell=False,
    )


@patch.object(
    ApplicationDiscovery,
    "find",
    return_value=None,
)
def test_open_application_not_found(mock_find):
    executor = ActionExecutor()

    action = Action(
        action="open_application",
        parameters={"application": "unknown_app"},
        step_id="step_1",
    )

    result = executor.execute(action)

    assert result.success is False
    assert result.error is not None
    assert "not found" in result.error.lower()

    mock_find.assert_called_once_with("unknown_app")
