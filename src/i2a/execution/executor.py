import subprocess
import time
import webbrowser
from urllib.parse import urlparse

from i2a.core import Action
from i2a.execution.application_discovery import ApplicationDiscovery
from i2a.execution.result import ActionResult


class ActionExecutor:
    """Executes individual supported I2A actions."""

    MAX_WAIT_SECONDS = 300

    def __init__(
        self,
        application_discovery: ApplicationDiscovery | None = None,
    ) -> None:
        self.application_discovery = (
            application_discovery
            if application_discovery is not None
            else ApplicationDiscovery()
        )

    def execute(self, action: Action) -> ActionResult:
        """Execute one action and return its result."""

        try:
            if action.action == "open_url":
                return self._open_url(action)

            if action.action == "wait":
                return self._wait(action)

            if action.action == "open_application":
                return self._open_application(action)

            return ActionResult(
                step_id=action.step_id,
                action=action.action,
                success=False,
                message="Action is not supported.",
                error=f"Action '{action.action}' is not supported.",
            )

        except Exception as error:
            return ActionResult(
                step_id=action.step_id,
                action=action.action,
                success=False,
                message="Action execution failed.",
                error=str(error),
            )

    def _open_url(self, action: Action) -> ActionResult:
        """Open a valid HTTP or HTTPS website."""

        url = action.parameters.get("url")

        if not isinstance(url, str):
            raise ValueError("URL must be a string.")

        parsed = urlparse(url)

        if (
            parsed.scheme not in ("http", "https")
            or not parsed.hostname
            or parsed.username
            or parsed.password
        ):
            raise ValueError("A valid HTTP or HTTPS URL is required.")

        opened = webbrowser.open(url)

        if not opened:
            raise RuntimeError("The browser could not open the URL.")

        return ActionResult(
            step_id=action.step_id,
            action=action.action,
            success=True,
            message=f"Opened website: {url}",
            output=url,
        )

    def _wait(self, action: Action) -> ActionResult:
        """Pause execution for a specified duration."""

        seconds = action.parameters.get("seconds")

        if (
            isinstance(seconds, bool)
            or not isinstance(seconds, (int, float))
            or not 0 < seconds <= self.MAX_WAIT_SECONDS
        ):
            raise ValueError(
                f"Wait duration must be between 1 and "
                f"{self.MAX_WAIT_SECONDS} seconds."
            )

        time.sleep(seconds)

        return ActionResult(
            step_id=action.step_id,
            action=action.action,
            success=True,
            message=f"Waited for {seconds} seconds.",
            output=seconds,
        )

    def _open_application(self, action: Action) -> ActionResult:
        """Discover and launch an available application."""

        application = action.parameters.get("application")

        if not isinstance(application, str):
            raise ValueError("Application name must be a string.")

        application = application.strip()

        if not application:
            raise ValueError("Application name cannot be empty.")

        discovered = self.application_discovery.find(application)

        if discovered is None:
            raise ValueError(
                f"Application '{application}' was not found "
                "or is not approved."
            )

        process = subprocess.Popen(
            [discovered.executable],
            shell=False,
        )

        return ActionResult(
            step_id=action.step_id,
            action=action.action,
            success=True,
            message=f"Started application: {discovered.name}",
            output={"process_id": process.pid},
        )
