import pytest

from i2a.development.approval import ProposalApproval
from i2a.development.proposal import (
    DevelopmentProposal,
    FileChange,
)


def create_proposal():
    return DevelopmentProposal(
        project_name="Sample Project",
        summary="Create a basic application.",
        changes=[
            FileChange(
                operation="create",
                file_path="src/main.py",
                content="print('Hello')",
                reason="Create the entry point.",
            )
        ],
    )


def test_new_proposal_is_pending():
    approval = ProposalApproval(create_proposal())

    assert approval.status == ProposalApproval.PENDING


def test_approves_pending_proposal():
    approval = ProposalApproval(create_proposal())

    approval.approve()

    assert approval.status == ProposalApproval.APPROVED


def test_rejects_pending_proposal():
    approval = ProposalApproval(create_proposal())

    approval.reject()

    assert approval.status == ProposalApproval.REJECTED


def test_cannot_approve_rejected_proposal():
    approval = ProposalApproval(create_proposal())

    approval.reject()

    with pytest.raises(ValueError):
        approval.approve()


def test_cannot_reject_approved_proposal():
    approval = ProposalApproval(create_proposal())

    approval.approve()

    with pytest.raises(ValueError):
        approval.reject()


def test_rejects_invalid_proposal_type():
    with pytest.raises(TypeError):
        ProposalApproval({})


def test_to_dict_includes_status_and_proposal():
    approval = ProposalApproval(create_proposal())

    result = approval.to_dict()

    assert result["status"] == "pending"
    assert result["proposal"]["project_name"] == "Sample Project"
