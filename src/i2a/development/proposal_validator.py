
from pathlib import PurePath

from i2a.development.proposal import DevelopmentProposal


class ProposalValidator:
    """Validates development proposals before approval."""

    ALLOWED_OPERATIONS = {"create", "modify"}

    def validate(self, proposal: DevelopmentProposal) -> None:
        """Validate a development proposal."""

        if not isinstance(proposal, DevelopmentProposal):
            raise TypeError(
                "Expected a DevelopmentProposal object."
            )

        if not proposal.project_name.strip():
            raise ValueError("Project name cannot be empty.")

        if not proposal.summary.strip():
            raise ValueError("Proposal summary cannot be empty.")

        if not proposal.changes:
            raise ValueError(
                "Proposal must contain at least one change."
            )

        seen_paths = set()

        for index, change in enumerate(proposal.changes, start=1):
            if change.operation not in self.ALLOWED_OPERATIONS:
                raise ValueError(
                    f"Change {index} has an unsupported operation."
                )

            if not change.file_path.strip():
                raise ValueError(
                    f"Change {index} has an empty file path."
                )

            path = PurePath(change.file_path)

            if path.is_absolute() or ".." in path.parts:
                raise ValueError(
                    f"Change {index} contains an unsafe file path."
                )

            normalized_path = str(path).lower()

            if normalized_path in seen_paths:
                raise ValueError(
                    f"Duplicate file path: {change.file_path}"
                )

            seen_paths.add(normalized_path)

            if not isinstance(change.content, str):
                raise ValueError(
                    f"Change {index} content must be a string."
                )

            if not change.reason.strip():
                raise ValueError(
                    f"Change {index} must include a reason."
                )
