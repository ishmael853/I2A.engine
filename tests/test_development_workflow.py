from pathlib import Path

import pytest

from i2a.development.approval import ProposalApproval
from i2a.development.proposal import (
    DevelopmentProposal,
    FileChange,
)
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

        return {
            "project_name": proposal.project_name,
            "summary": proposal.summary,
            "workspace": str(workspace_path),
            "total_changes": len(proposal.changes),
            "changes": [],
        }


class FakeExecutor:
    def __init__(self) -> None:
        self.received_approval = None
        self.received_workspace = None

    def execute(self, approval, workspace_path):
        self.received_approval = approval
        self.received_workspace = workspace_path

        return {
            "project_name": approval.proposal.project_name,
            "workspace": str(workspace_path),
            "results": [
                {
                    "file_path": "src/main.py",
                    "operation": "create",
                    "status": "success",
                }
            ],
        }


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


def create_workflow(plan, proposal):
    planner = FakePlanner(plan)
    generator = FakeProposalGenerator(proposal)
    previewer = FakePreviewer()
    executor = FakeExecutor()

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