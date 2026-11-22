
import json
from pathlib import Path

from i2a.ai.assistant import I2AAssistant
from i2a.development.workspace import WorkspaceAnalyzer


class DevelopmentPlanner:
    """Creates and validates AI-generated development plans."""

    REQUIRED_FIELDS = {
        "project_name",
        "description",
        "technology_stack",
        "requirements",
        "development_steps",
        "testing_strategy",
    }

    def __init__(
        self,
        assistant: I2AAssistant | None = None,
        workspace_analyzer: WorkspaceAnalyzer | None = None,
    ) -> None:
        self.assistant = assistant or I2AAssistant()
        self.workspace_analyzer = (
            workspace_analyzer or WorkspaceAnalyzer()
        )

    def _validate_plan(self, plan: dict) -> None:
        """Validate the structure of a development plan."""

        missing_fields = self.REQUIRED_FIELDS - plan.keys()

        if missing_fields:
            raise ValueError(
                "Missing required fields: "
                + ", ".join(sorted(missing_fields))
            )

        for field in ("project_name", "description"):
            if not isinstance(plan[field], str) or not plan[field].strip():
                raise ValueError(f"Invalid field: {field}")

        for field in (
            "technology_stack",
            "requirements",
            "development_steps",
            "testing_strategy",
        ):
            if not isinstance(plan[field], list) or not plan[field]:
                raise ValueError(f"Invalid or empty field: {field}")

        for index, step in enumerate(plan["development_steps"], start=1):
            if not isinstance(step, dict):
                raise ValueError(
                    f"Development step {index} must be an object."
                )

            if not all(
                key in step
                for key in ("step", "title", "description")
            ):
                raise ValueError(
                    f"Development step {index} is incomplete."
                )

    def create_plan(
        self,
        instruction: str,
        workspace_path: str | Path | None = None,
    ) -> dict:
        """Generate a development plan, optionally using workspace context."""

        if not isinstance(instruction, str) or not instruction.strip():
            raise ValueError(
                "Development instruction cannot be empty."
            )

        workspace_context = ""

        if workspace_path is not None:
            analysis = self.workspace_analyzer.analyze(workspace_path)

            workspace_context = (
                "\n\nEXISTING PROJECT WORKSPACE:\n"
                + json.dumps(analysis.to_dict(), indent=2)
            )

        prompt = f"""
Create a software development plan for this request:

{instruction.strip()}

{workspace_context}

If existing project information is provided:
- Base your plan on the actual project structure.
- Identify existing files and avoid unnecessary duplication.
- Recommend changes that fit the existing technology stack.
- Do not assume that files exist unless they appear in the analysis.

Return ONLY valid JSON with ALL these fields:

{{
    "project_name": "Project name",
    "description": "Project description",
    "technology_stack": ["Python"],
    "requirements": ["Requirement one"],
    "development_steps": [
        {{
            "step": 1,
            "title": "Step title",
            "description": "Step description"
        }}
    ],
    "testing_strategy": ["Testing approach"]
}}

Rules:
- Every field is mandatory.
- Every list must contain at least one item.
- Every development step must contain step, title, and description.
- Return JSON only, without Markdown fences.
- Do not claim that development work has been executed.
"""

        response = self.assistant.ask(prompt)

        for attempt in range(2):
            try:
                plan = json.loads(response)

                if not isinstance(plan, dict):
                    raise ValueError(
                        "Development plan must be a JSON object."
                    )

                self._validate_plan(plan)
                return plan

            except (json.JSONDecodeError, ValueError) as error:
                if attempt == 1:
                    raise ValueError(
                        f"Could not generate a valid development plan "
                        f"after two attempts: {error}"
                    ) from error

                response = self.assistant.ask(
                    f"""
Your previous development plan was invalid.

Validation error:
{error}

Previous response:
{response}

Generate the complete corrected JSON plan again.

Include every required field:
project_name, description, technology_stack,
requirements, development_steps, testing_strategy.

Return JSON only. Do not omit any field.
"""
                )

        raise RuntimeError("Development planning failed.")
