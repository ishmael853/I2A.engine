
import pytest

from i2a.development.approval import ProposalApproval
from i2a.development.file_executor import FileChangeExecutor
from i2a.development.proposal import (
    DevelopmentProposal,
    FileChange,
)


def create_approval(changes):
    proposal = DevelopmentProposal(
        project_name="Sample Project",
        summary="Apply approved project changes.",
        changes=changes,
    )

    approval = ProposalApproval(proposal)
    approval.approve()

    return approval


def test_creates_file_in_workspace(tmp_path):
    executor = FileChangeExecutor()

    approval = create_approval([
        FileChange(
            operation="create",
            file_path="main.py",
            content="print('Hello')",
            reason="Create the entry point.",
        )
    ])

    result = executor.execute(approval, tmp_path)

    created_file = tmp_path / "main.py"

    assert created_file.exists()
    assert created_file.read_text(encoding="utf-8") == "print('Hello')"
    assert result["results"][0]["status"] == "success"


def test_modifies_existing_file(tmp_path):
    executor = FileChangeExecutor()

    existing_file = tmp_path / "main.py"
    existing_file.write_text("print('Old')", encoding="utf-8")

    approval = create_approval([
        FileChange(
            operation="modify",
            file_path="main.py",
            content="print('Updated')",
            reason="Update the application.",
        )
    ])

    executor.execute(approval, tmp_path)

    assert existing_file.read_text(encoding="utf-8") == "print('Updated')"


def test_rejects_pending_proposal(tmp_path):
    executor = FileChangeExecutor()

    proposal = DevelopmentProposal(
        project_name="Sample Project",
        summary="Pending changes.",
        changes=[
            FileChange(
                operation="create",
                file_path="main.py",
                content="print('Hello')",
                reason="Create the entry point.",
            )
        ],
    )

    approval = ProposalApproval(proposal)

    with pytest.raises(PermissionError):
        executor.execute(approval, tmp_path)


def test_rejects_path_outside_workspace(tmp_path):
    executor = FileChangeExecutor()

    approval = create_approval([
        FileChange(
            operation="create",
            file_path="../outside.py",
            content="print('Hello')",
            reason="Create an external file.",
        )
    ])

    with pytest.raises(ValueError):
        executor.execute(approval, tmp_path)


def test_rejects_existing_file_creation(tmp_path):
    executor = FileChangeExecutor()

    existing_file = tmp_path / "main.py"
    existing_file.write_text("Original", encoding="utf-8")

    approval = create_approval([
        FileChange(
            operation="create",
            file_path="main.py",
            content="Updated",
            reason="Create a file.",
        )
    ])

    with pytest.raises(FileExistsError):
        executor.execute(approval, tmp_path)

    assert existing_file.read_text(encoding="utf-8") == "Original"


def test_rejects_modification_of_missing_file(tmp_path):
    executor = FileChangeExecutor()

    approval = create_approval([
        FileChange(
            operation="modify",
            file_path="missing.py",
            content="print('Hello')",
            reason="Modify an existing file.",
        )
    ])

    with pytest.raises(FileNotFoundError):
        executor.execute(approval, tmp_path)


def test_rejects_missing_workspace(tmp_path):
    executor = FileChangeExecutor()

    approval = create_approval([
        FileChange(
            operation="create",
            file_path="main.py",
            content="print('Hello')",
            reason="Create the entry point.",
        )
    ])

    with pytest.raises(FileNotFoundError):
        executor.execute(approval, tmp_path / "missing")
