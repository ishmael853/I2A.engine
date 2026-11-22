import re
from urllib.parse import urlparse
from pathlib import Path

from i2a.core import Action, WorkflowPlan
from i2a.planner.parser import ParsedIntent
from i2a.execution.application_discovery import ApplicationDiscovery


class ActionPlanner:
    """Converts parsed instructions into structured action plans."""

    def __init__(
        self,
        application_discovery: ApplicationDiscovery | None = None,
    ) -> None:
        self.application_discovery = (
            application_discovery
            if application_discovery is not None
            else ApplicationDiscovery()
        )

    def create_plan(self, intent: ParsedIntent) -> WorkflowPlan:
        text = intent.normalized_text

        steps = self._plan_steps(text)

        if not steps:
            raise ValueError(
                "I2A could not identify a supported action in this instruction."
            )

        return WorkflowPlan(
            name="Generated Automation",
            goal=text,
            steps=steps,
        )

    def _plan_steps(self, text: str) -> list[Action]:
        candidates = []

        website_pattern = (
            r"\b(?:open|visit|go to|browse)\s+"
            r"(https?://[^\s,;]+)"
        )

        for match in re.finditer(
            website_pattern, text, re.IGNORECASE
        ):
            url = match.group(1).rstrip(".,!?")
            parsed_url = urlparse(url)

            if (
                parsed_url.scheme in ("http", "https")
                and parsed_url.hostname
                and not parsed_url.username
                and not parsed_url.password
            ):
                candidates.append(
                    (
                        match.start(),
                        "open_url",
                        {"url": url},
                        f"Open website {url}",
                    )
                )

        wait_pattern = (
            r"\bwait\s+(\d+)\s+"
            r"(seconds?|secs?|minutes?|mins?)\b"
        )

        for match in re.finditer(
            wait_pattern, text, re.IGNORECASE
        ):
            amount = int(match.group(1))
            unit = match.group(2).lower()

            seconds = (
                amount * 60
                if unit.startswith("min")
                else amount
            )

            if 0 < seconds <= 300:
                candidates.append(
                    (
                        match.start(),
                        "wait",
                        {"seconds": seconds},
                        f"Wait for {seconds} seconds",
                    )
                )

        self._discover_application_actions(text, candidates)

        candidates.sort(key=lambda item: item[0])

        steps = []

        for position, action, parameters, description in candidates:
            steps.append(
                Action(
                    action=action,
                    parameters=parameters,
                    description=description,
                    step_id=f"step_{len(steps) + 1}",
                )
            )

        return steps

    def _extract_target_path(self, text: str) -> str | None:
        """Extract an optional Windows folder or file path."""

        match = re.search(
            r"\b(?:at|in|inside)\s+"
            r"([A-Za-z]:\\.+)",
            text,
            re.IGNORECASE,
        )

        if not match:
            return None

        return match.group(1).strip().rstrip(".,!?;")


    def _discover_application_actions(
        self,
        text: str,
        candidates: list,
    ) -> None:
        """Match application names against discovered applications."""

        applications = self.application_discovery.discover()

        # Check longer names first to avoid partial matches.
        applications = sorted(
            applications,
            key=lambda application: len(application.name),
            reverse=True,
        )

        command_pattern = (
            r"\b(?:open|launch|start)\s+"
            r"(?:application\s+)?"
        )

        for command in re.finditer(
            command_pattern,
            text,
            re.IGNORECASE,
        ):
            remaining_text = text[command.end():]

            for application in applications:
                name = application.name.strip()

                if not name:
                    continue

                pattern = (
                    re.escape(name)
                    + r"(?=$|[\s.,!?;])"
                )

                match = re.match(
                    pattern,
                    remaining_text,
                    re.IGNORECASE,
                )

                if match:
                    parameters = {"application": name}

                    target_path = self._extract_target_path(text)

                    if target_path:
                        parameters["path"] = target_path

                    candidates.append(
                        (
                            command.start(),
                            "open_application",
                            parameters,
                            f"Open application {name}",
                        )
                    )
