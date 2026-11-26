from pathlib import Path

import pytest

from i2a.development.approval import ProposalApproval
from i2a.development.backup_cleanup import BackupCleanupApproval
from i2a.development.proposal import DevelopmentProposal, FileChange
from i2a.development.workflow import DevelopmentWorkflow

class FakePlanner:
    def __init__(self, plan: dict) -> None:
        self.plan = plan
        self.last_instruction = None
        self.last_workspace = None

    def create_plan(self, instruction, workspace_path=None):
        self.last_instruction = instruction
        self.last_workspace = workspace_path
        return self.plan


class FakeProposalGenerator:
    def __init__(self, proposal: DevelopmentProposal) -> None:
        self.proposal = proposal
        self.received_plan = None

    def generate(self, development_plan):
        self.received_plan = development_plan
        return self.proposal


class FakePreviewer:
    def __init__(self) -> None:
        self.received_proposal = None
        self.received_workspace = None

    def generate(self, proposal, workspace_path):
        self.received_proposal = proposal
        self.received_workspace = workspace_path

        changes = []

        for change in proposal.changes:
            target = Path(workspace_path) / change.file_path

            current_content = (
                target.read_text(encoding="utf-8")
                if change.operation == "modify" and target.is_file()
                else None
            )

            changes.append({
                "operation": change.operation,
                "file_path": change.file_path,
                "reason": change.reason,
                "current_content": current_content,
                "proposed_content": change.content,
                "diff": "",
            })

        return {
            "project_name": proposal.project_name,
            "summary": proposal.summary,
            "workspace": str(workspace_path),
            "total_changes": len(proposal.changes),
            "changes": changes,
        }

class FakeExecutor:
    def __init__(self, result=None) -> None:
        self.received_approval = None
        self.received_workspace = None
        self.result = result

    def execute(self, approval, workspace_path):
        self.received_approval = approval
        self.received_workspace = workspace_path

        if self.result is not None:
            return self.result

        return {
            "results": [
                {
                    "status": "success",
                    "file_path": "src/main.py",
                }
            ]
        }

    def _resolve_target(self, workspace_path, file_path):
        workspace = Path(workspace_path).resolve()
        target = (workspace / file_path).resolve()

        try:
            target.relative_to(workspace)
        except ValueError:
            raise ValueError("File path escapes workspace.")

        return target

@pytest.fixture
def workspace(tmp_path):
    return tmp_path


@pytest.fixture
def plan():
    return {
        "project_name": "Demo Project",
        "description": "A demo project.",
        "technology_stack": ["Python"],
        "requirements": ["Create an application."],
        "development_steps": [
            {
                "step": 1,
                "title": "Create application",
                "description": "Create the application entry point.",
            }
        ],
        "testing_strategy": ["Run automated tests."],
    }


@pytest.fixture
def proposal():
    return DevelopmentProposal(
        project_name="Demo Project",
        summary="Create the application entry point.",
        changes=[
            FileChange(
                operation="create",
                file_path="src/main.py",
                content="print('Hello')\n",
                reason="Create the application entry point.",
            )
        ],
    )


def create_workflow(plan, proposal, executor=None):
    planner = FakePlanner(plan)
    generator = FakeProposalGenerator(proposal)
    previewer = FakePreviewer()
    executor = executor or FakeExecutor()

    workflow = DevelopmentWorkflow(
        planner=planner,
        proposal_generator=generator,
        previewer=previewer,
        executor=executor,
    )

    return workflow, planner, generator, previewer, executor


def test_prepare_builds_pending_development_workflow(
    workspace,
    plan,
    proposal,
):
    workflow, planner, generator, previewer, executor = (
        create_workflow(plan, proposal)
    )

    result = workflow.prepare(
        "Build the demo application.",
        workspace,
    )

    assert result["status"] == ProposalApproval.PENDING
    assert result["plan"] == plan
    assert result["proposal"] == proposal.to_dict()
    assert result["preview"]["total_changes"] == 1

    assert planner.last_instruction == "Build the demo application."
    assert planner.last_workspace == workspace.resolve()
    assert generator.received_plan == plan
    assert previewer.received_proposal is proposal
    assert previewer.received_workspace == workspace.resolve()

    assert workflow.pending_approval is not None
    assert workflow.pending_approval.status == ProposalApproval.PENDING
    assert executor.received_approval is None


def test_approve_changes_pending_status(
    workspace,
    plan,
    proposal,
):
    workflow, _, _, _, _ = create_workflow(plan, proposal)

    workflow.prepare(
        "Build the demo application.",
        workspace,
    )

    result = workflow.approve()

    assert result["status"] == ProposalApproval.APPROVED
    assert workflow.pending_approval.status == ProposalApproval.APPROVED


def test_reject_changes_pending_status(
    workspace,
    plan,
    proposal,
):
    workflow, _, _, _, _ = create_workflow(plan, proposal)

    workflow.prepare(
        "Build the demo application.",
        workspace,
    )

    result = workflow.reject()

    assert result["status"] == ProposalApproval.REJECTED
    assert workflow.pending_approval.status == ProposalApproval.REJECTED


def test_execute_requires_explicit_approval(
    workspace,
    plan,
    proposal,
):
    workflow, _, _, _, executor = create_workflow(plan, proposal)

    workflow.prepare(
        "Build the demo application.",
        workspace,
    )

    with pytest.raises(PermissionError):
        workflow.execute()

    assert executor.received_approval is None


def test_execute_after_approval(
    workspace,
    plan,
    proposal,
):
    workflow, _, _, _, executor = create_workflow(plan, proposal)

    workflow.prepare(
        "Build the demo application.",
        workspace,
    )

    workflow.approve()

    result = workflow.execute()

    assert result["approval_status"] == ProposalApproval.APPROVED
    assert result["execution"]["results"][0]["status"] == "success"
    assert executor.received_approval is workflow.pending_approval
    assert executor.received_workspace == workspace.resolve()


def test_prepare_rejects_missing_workspace(
    plan,
    proposal,
    tmp_path,
):
    workflow, _, _, _, _ = create_workflow(plan, proposal)

    missing_workspace = tmp_path / "missing"

    with pytest.raises(FileNotFoundError):
        workflow.prepare(
            "Build the demo application.",
            missing_workspace,
        )


def test_prepare_rejects_file_as_workspace(
    plan,
    proposal,
    tmp_path,
):
    workflow, _, _, _, _ = create_workflow(plan, proposal)

    workspace_file = tmp_path / "workspace.txt"
    workspace_file.write_text("not a directory")

    with pytest.raises(NotADirectoryError):
        workflow.prepare(
            "Build the demo application.",
            workspace_file,
        )


def test_approve_requires_pending_proposal(
    plan,
    proposal,
):
    workflow, _, _, _, _ = create_workflow(plan, proposal)

    with pytest.raises(RuntimeError):
        workflow.approve()


def test_reject_requires_pending_proposal(
    plan,
    proposal,
):
    workflow, _, _, _, _ = create_workflow(plan, proposal)

    with pytest.raises(RuntimeError):
        workflow.reject()


def test_execute_requires_proposal(
    plan,
    proposal,
):
    workflow, _, _, _, _ = create_workflow(plan, proposal)

    with pytest.raises(RuntimeError):
        workflow.execute()

def test_execute_cannot_run_same_approved_proposal_twice(
        workspace,
        plan,
        proposal,
):
    workflow, _, _, _, executor = create_workflow(plan, proposal)

    workflow.prepare(
        "Build the demo application.",
        workspace,
    )

    workflow.approve()

    workflow.execute()

    with pytest.raises(RuntimeError):
        workflow.execute()

    assert executor.received_approval is workflow.pending_approval

def test_execute_rejects_workspace_changes_after_preview(
    workspace,
    plan,
    proposal,
):
    target = workspace / "src" / "main.py"
    target.parent.mkdir()

    target.write_text(
        "print('Original')\n",
        encoding="utf-8",
    )

    proposal.changes[0].operation = "modify"
    proposal.changes[0].content = "print('Updated')\n"

    workflow, _, _, _, executor = create_workflow(plan, proposal)

    workflow.prepare(
        "Update the demo application.",
        workspace,
    )

    target.write_text(
        "print('Changed outside I2A')\n",
        encoding="utf-8",
    )

    workflow.approve()

    with pytest.raises(RuntimeError):
        workflow.execute()

    assert executor.received_approval is None
    assert target.read_text(encoding="utf-8") == (
        "print('Changed outside I2A')\n"
    )

def test_execute_does_not_mark_failed_execution_as_completed(
        workspace,
        plan,
        proposal,
):
    executor = FakeExecutor(
        result={
            "results": [
                {
                    "file_path": "src/main.py",
                    "operation": "create",
                    "status": "failed",
                    "error": "simulated execution failure.",
                }
            ]
        }
    )

    workflow, _, _, _, _ = create_workflow(
        plan,
        proposal,
        executor=executor,
    )

    workflow.prepare(
        "Build the demo application.",
        workspace,
    )

    workflow.approve()

    result = workflow.execute()

    assert result["execution"]["results"][0]["status"] == "failed"
    assert workflow.execution_completed is False

def test_execute_does_not_mark_rolled_back_execution_as_completed(
        workspace,
        plan,
        proposal,
):
    executor = FakeExecutor(
        result={
            "results": [
                {
                    "file_path": "src/main.py",
                    "operation": "create",
                    "status": "rolled_back",
                },
                {
                    "file_path": "src/main.py",
                    "operation": "create",
                    "status": "rollback_failed",
                },
            ]
        }
    )

    workflow, _, _, _, _ = create_workflow(
        plan,
        proposal,
        executor=executor,
    )

    workflow.prepare(
        "Build the demo application.",
        workspace,
    )

    workflow.approve()

    result = workflow.execute()

    assert len(result["execution"]["results"]) == 2
    assert workflow.execution_completed is False

def test_inspect_backups_returns_integrity_and_orphaned_files(
    workspace: Path,
    plan: dict,
    proposal: DevelopmentProposal,
) -> None:
    workflow, _, _, _, _ = create_workflow(plan, proposal)

    workflow.prepare("BUild the demo application.", workspace)

    result = workflow.inspect_backups()

    assert result == {
        "backups": [],
        "orphaned_files": [],
    }

def test_prepare_backup_cleanup_creates_pending_approval(
        workspace: Path,
        plan: dict,
        proposal: DevelopmentProposal,
) -> None:
    workflow, _, _, _, _ = create_workflow(plan, proposal)

    workflow.prepare("Build the demo application.", workspace)

    result = workflow.prepare_backup_cleanup()

    assert result["status"] == BackupCleanupApproval.PENDING
    assert result["proposal"]["workspace"] == str(workspace.resolve())
    assert result["proposal"]["files"] == []
    assert workflow.pending_backup_cleanup is not None

def test_backup_cleanup_requires_independent_approval(
        workspace: Path,
        plan: dict,
        proposal: DevelopmentProposal,
) -> None:
    workflow, _, _, _, _ = create_workflow(plan, proposal)

    workflow.prepare("Build the demo application.", workspace)
    workflow.prepare_backup_cleanup()

    assert workflow.pending_backup_cleanup is not None
    assert workflow.pending_backup_cleanup.status == BackupCleanupApproval.PENDING

    with pytest.raises(PermissionError):
        workflow.execute_backup_cleanup()

    result = workflow.approve_backup_cleanup()

    assert result["status"] == BackupCleanupApproval.APPROVED
    assert workflow.pending_backup_cleanup.status == BackupCleanupApproval.APPROVED

def test_reject_backup_cleanup(
        workspace: Path,
        plan: dict,
        proposal: DevelopmentProposal,
) -> None:
    workflow, _, _, _, _ = create_workflow(plan, proposal)

    workflow.prepare("Build the demo application.", workspace)
    workflow.prepare_backup_cleanup()

    result = workflow.reject_backup_cleanup()

    assert result["status"] == BackupCleanupApproval.REJECTED

    with pytest.raises(PermissionError):
        workflow.execute_backup_cleanup()