import pytest

from i2a.development.proposal import (
    DevelopmentProposal,
    FileChange,
)
from i2a.development.proposal_validator import ProposalValidator


def create_valid_proposal():
    return DevelopmentProposal(
        project_name="Sample Project",
        summary="Create a basic Python application.",
        changes=[
            FileChange(
                operation="create",
                file_path="src/main.py",
                content="print('Hello')",
                reason="Create the application entry point.",
            )
        ],
    )


def test_accepts_valid_proposal():
    validator = ProposalValidator()
    proposal = create_valid_proposal()

    assert validator.validate(proposal) is None


def test_rejects_invalid_proposal_type():
    validator = ProposalValidator()

    with pytest.raises(TypeError):
        validator.validate({})


def test_rejects_unsupported_operation():
    validator = ProposalValidator()
    proposal = create_valid_proposal()
    proposal.changes[0].operation = "delete"

    with pytest.raises(ValueError):
        validator.validate(proposal)


def test_rejects_unsafe_file_path():
    validator = ProposalValidator()
    proposal = create_valid_proposal()
    proposal.changes[0].file_path = "../outside.py"

    with pytest.raises(ValueError):
        validator.validate(proposal)


def test_rejects_duplicate_file_paths():
    validator = ProposalValidator()
    proposal = create_valid_proposal()

    proposal.changes.append(
        FileChange(
            operation="modify",
            file_path="src/main.py",
            content="print('Updated')",
            reason="Update the application.",
        )
    )

    with pytest.raises(ValueError):
        validator.validate(proposal)


def test_rejects_empty_proposal():
    validator = ProposalValidator()

    proposal = DevelopmentProposal(
        project_name="Sample Project",
        summary="No changes.",
    )

    with pytest.raises(ValueError):
        validator.validate(proposal)
