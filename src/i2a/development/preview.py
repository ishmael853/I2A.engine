import difflib
from pathlib import Path

from i2a.development.proposal import DevelopmentProposal
from i2a.development.proposal_validator import ProposalValidator
from i2a.development.file_executor import FileChangeExecutor

class FileChangePreview:
    """Generates previews of proposed project file changes."""

    def __init__(
            self,
            validator: ProposalValidator | None = None
    ) -> None:
        self.validator = validator or ProposalValidator()
        self.path_resolver = FileChangeExecutor(self.validator)

    def generate(
            self,
            proposal: DevelopmentProposal,
            workspace_path: str | Path,
    ) -> dict:
        """Generate a preview without modifying project files."""

        if not isinstance(proposal, DevelopmentProposal):
            raise TypeError(
                "Expected a DevelopmentProposal object."
            )

        self.validator.validate(proposal)

        workspace = Path(workspace_path).expanduser().resolve()

        if not workspace.exists():
            raise FileNotFoundError(
                f"Workspace does not exist: {workspace}"
            )

        if not workspace.is_dir():
            raise NotADirectoryError(
                f"Workspace must be a directory: {workspace}"
            )

        changes = []

        for change in proposal.changes:
            target = self.path_resolver._resolve_target(
                workspace,
                change.file_path,
            )

            if not target.parent.is_dir():
                raise FileNotFoundError(
                    f"Parent directory does not exist: {target.parent}"
                )

            if change.operation == "create":
                if target.exists():
                    raise FileExistsError(
                        f"File already exists: {target}"
                    )

                current_content = None

            else:
                if not target.is_file():
                    raise FileNotFoundError(
                        f"File to modify does not exist: {target}"
                    )

                backup_path = target.with_name(
                    f"{target.name}.i2a-backup"
                )

                if backup_path.exists():
                    raise FileExistsError(
                        f"{target.name}.i2a-backup"
                    )

                current_content = target.read_text(
                    encoding="utf-8"
                )

            diff = "".join(
                difflib.unified_diff(
                    (current_content or "").splitlines(keepends=True),
                    change.content.splitlines(keepends=True),
                    fromfile=f"a/{change.file_path}",
                    tofile=f"b/{change.file_path}",
                )
            )

            changes.append({
                "operation": change.operation,
                "file_path": change.file_path,
                "reason": change.reason,
                "current_content": current_content,
                "proposed_content": change.content,
                "diff": diff,
            })


        return {
            "project_name": proposal.project_name,
            "summary": proposal.summary,
            "workspace": str(workspace),
            "total_changes": len(changes),
            "changes": changes
        }