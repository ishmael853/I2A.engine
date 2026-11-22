import json

from i2a.ai.assistant import I2AAssistant
from i2a.development.proposal import (
    DevelopmentProposal,
    FileChange,
)
from i2a.development.proposal_validator import ProposalValidator


class DevelopmentProposalGenerator:
    """Generates validated file-change proposals using AI."""

    def __init__(
        self,
        assistant: I2AAssistant | None = None,
        validator: ProposalValidator | None = None,
    ) -> None:
        self.assistant = assistant or I2AAssistant()
        self.validator = validator or ProposalValidator()

    def generate(self, development_plan: dict) -> DevelopmentProposal:
        """Generate a file-change proposal from a development plan."""

        if not isinstance(development_plan, dict):
            raise TypeError("Development plan must be a dictionary.")

        if not development_plan:
            raise ValueError("Development plan cannot be empty.")

        prompt = f"""
Convert the following software development plan into
a structured file-change proposal.

DEVELOPMENT PLAN:
{json.dumps(development_plan, indent=2)}

Return ONLY valid JSON using this exact structure:

{{
    "project_name": "Project name",
    "summary": "Summary of proposed changes",
    "changes": [
        {{
            "operation": "create",
            "file_path": "src/main.py",
            "content": "print('Hello')",
            "reason": "Create the application entry point."
        }}
    ]
}}

RULES:
- Every field is mandatory.
- Each change must contain operation, file_path, content and reason.
- Operation must be either create or modify.
- Use relative file paths only.
- Never use paths containing '..'.
- Do not propose deleting files.
- Include complete proposed file contents.
- Do not claim that any file has been created or modified.
- Return JSON only, without Markdown fences.
"""

        response = self.assistant.ask(prompt)

        try:
            data = json.loads(response)
        except json.JSONDecodeError as error:
            raise ValueError(
                "AI returned invalid JSON for the development proposal."
            ) from error

        if not isinstance(data, dict):
            raise ValueError("Proposal must be a JSON object.")

        required_fields = {"project_name", "summary", "changes"}

        if not required_fields.issubset(data):
            raise ValueError("Proposal is missing required fields.")

        if not isinstance(data["changes"], list):
            raise ValueError("Proposal changes must be a list.")

        changes = []

        for index, item in enumerate(data["changes"], start=1):
            if not isinstance(item, dict):
                raise ValueError(
                    f"Change {index} must be a JSON object."
                )

            required_change_fields = {
                "operation",
                "file_path",
                "content",
                "reason",
            }

            if not required_change_fields.issubset(item):
                raise ValueError(
                    f"Change {index} is missing required fields."
                )

            if not all(
                isinstance(item[field], str)
                for field in required_change_fields
            ):
                raise ValueError(
                    f"Change {index} fields must be strings."
                )

            changes.append(FileChange(**{
                field: item[field]
                for field in required_change_fields
            }))

        if not isinstance(data["project_name"], str):
            raise ValueError("Project name must be a string.")

        if not isinstance(data["summary"], str):
            raise ValueError("Proposal summary must be a string.")

        proposal = DevelopmentProposal(
            project_name=data["project_name"],
            summary=data["summary"],
            changes=changes,
        )

        self.validator.validate(proposal)

        return proposal
