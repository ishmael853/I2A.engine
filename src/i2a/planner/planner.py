import re
from urllib.parse import urlparse

from i2a.core import Action, WorkflowPlan
from i2a.planner.parser import ParsedIntent

class ActionPlanner:
    """Converts parsed instructions into structured action plans."""

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

            if(
                parsed_url.scheme in ("http", "https")
                and parsed_url.hostname
                and not parsed_url.username
                and not parsed_url.password
            ) :
                
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

        app_pattern = (
            r"\b(?:open|launch|start)\s+"
            r"(?:application\s+)?"
            r"(notepad|calculator|paint)"
            r"(?=\s|$|[.,!?;])"
        )

        for match in re.finditer(
            app_pattern, text, re.IGNORECASE
        ):
            application = match.group(1)

            candidates.append(
                (
                    match.start(),
                    "open_application",
                    {"application": application},
                    f"Open application {application}",
                )
            )

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