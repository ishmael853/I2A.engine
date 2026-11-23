from pathlib import Path

from i2a.development.planner import DevelopmentPlanner
from i2a.development.proposal_generator import (
    DevelopmentProposalGenerator
)
from i2a.development.proposal_validator import ProposalValidator
from i2a.development.preview import FileChangePreview
from i2a.development.approval import ProposalApproval
from i2a.development.file_executor import FileChangeExecutor

class DevelopmentWorkflow:
    """Coordinates the complete AI-assisted development workflow."""

    def __init__(
            self,
            planner: DevelopmentPlanner | None = None,
            proposal_generator: DevelopmentProposalGenerator | None = None,
            validator: ProposalValidator | None = None,
            previewer: FileChangePreview | None = None,
            executor: FileChangeExecutor | None = None,
    ) -> None:
        self.validator = validator or ProposalValidator()

        self.planner = planner or DevelopmentPlanner()

        self.proposal_generator = (
            proposal_generator
            or DevelopmentProposalGenerator(
                validator=self.validator
            )
        )

        self.previewer = (
            previewer
            or FileChangePreview(self.validator)
        )

        self.executor = (
            executor
            or FileChangeExecutor(self.validator)
        )

        self.pending_approval: ProposalApproval | None = None
        self.workspace_path: Path | None = None
        self.preview: dict | None = None

    def prepare(
            self,
            instruction: str,
            workspace_path: str | Path,
    ) -> dict:
        """Generate a development plan and review proposed changes."""

        if not isinstance(instruction, str) or not instruction.strip():
            raise ValueError(
                "Development instruction cannot be empty."
            )

        workspace = Path(workspace_path).expanduser().resolve()

        if not workspace.exists():
            raise FileNotFoundError(
                f"Workspace does not exist: {workspace}"
            )

        if not workspace.is_dir():
            raise NotADirectoryError(
                f"Workspace must be a directory: {workspace}"
            )

        self.pending_approval = None
        self.workspace_path = None
        self.preview = None

        plan = self.planner.create_plan(
            instruction,
            workspace,
        )

        proposal = self.proposal_generator.generate(plan)

        self.validator.validate(proposal)

        preview = self.previewer.generate(
            proposal,
            workspace,
        )

        approval = ProposalApproval(proposal)

        self.pending_approval = approval
        self.workspace_path = workspace
        self.preview = preview

        return {
            "status": ProposalApproval.PENDING,
            "plan": plan,
            "proposal": proposal.to_dict(),
            "preview": preview,
        }

    def approve(self) -> dict:
        """Approve the pending development proposal."""

        if self.pending_approval is None:
            raise RuntimeError(
                "There is no pending development proposal."
            )

        self.pending_approval.approve()

        return self.pending_approval.to_dict()

    def reject(self) -> dict:
        """Reject the pending development proposal."""

        if self.pending_approval is None:
            raise RuntimeError(
                "There is no pending development proposal."
            )

        self.pending_approval.reject()

        return self.pending_approval.to_dict()

    def execute(self) ->  dict:
        """Execute the approved development proposal."""

        if self.pending_approval is None:
            raise RuntimeError(
                "There is no development proposal to execute."
            )

        if self.pending_approval.status != ProposalApproval.APPROVED:
            raise PermissionError(
                "The development proposal has not been approved"
            )

        if self.workspace_path is None:
            raise RuntimeError(
                "No workspace is associated with the proposal."
            )

        result = self.executor.execute(
            self.pending_approval,
            self.workspace_path,
        )

        return {
            "approval_status": self.pending_approval.status,
            "execution": result,
        }