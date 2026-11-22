from unittest.mock import patch

from i2a.execution.application_discovery import (
    ApplicationDiscovery,
    DiscoveredApplication,
)


@patch(
    "i2a.execution.application_discovery.shutil.which",
    return_value=r"C:\Windows\System32\notepad.exe",
)
@patch.object(ApplicationDiscovery, "_discover_start_menu")
def test_discover_application(mock_start_menu, mock_which):
    discovery = ApplicationDiscovery()

    applications = discovery.discover()

    assert len(applications) == 1
    assert applications[0].name == "notepad"
    assert applications[0].executable == (
        r"C:\Windows\System32\notepad.exe"
    )

    mock_which.assert_called()
    mock_start_menu.assert_called_once()


@patch(
    "i2a.execution.application_discovery.shutil.which",
    return_value=None,
)
@patch.object(ApplicationDiscovery, "_discover_start_menu")
def test_discover_no_applications(mock_start_menu, mock_which):
    discovery = ApplicationDiscovery()

    applications = discovery.discover()

    assert applications == []

    mock_start_menu.assert_called_once()


@patch.object(
    ApplicationDiscovery,
    "discover",
    return_value=[
        DiscoveredApplication(
            name="notepad",
            executable=r"C:\Windows\System32\notepad.exe",
        )
    ],
)
def test_find_application(mock_discover):
    discovery = ApplicationDiscovery()

    application = discovery.find("Notepad")

    assert application is not None
    assert application.name == "notepad"


@patch.object(
    ApplicationDiscovery,
    "discover",
    return_value=[],
)
def test_find_unknown_application(mock_discover):
    discovery = ApplicationDiscovery()

    application = discovery.find("unknown_app")

    assert application is None
