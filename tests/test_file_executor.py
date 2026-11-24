
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

def test_creates_backup_before_modifying_file(tmp_path):
    executor = FileChangeExecutor()

    existing_file = tmp_path / "main.py"
    existing_file.write_text(
        "print('original')",
        encoding="utf-8",
    )

    approval = create_approval([
        FileChange(
            operation="modify",
            file_path="main.py",
            content="print('updated')",
            reason="Update the application.",
        )
    ])

    executor.execute(approval, tmp_path)

    backup_file = tmp_path / "main.py.i2a-backup"

    assert backup_file.exists()
    assert backup_file.read_text(encoding="utf-8") == "print('original')"
    assert existing_file.read_text(encoding="utf-8") == "print('updated')"

def test_rejects_existing_backup(tmp_path):
    executor = FileChangeExecutor()

    existing_file = tmp_path / "main.py"
    existing_file.write_text("Original", encoding="utf-8")

    backup_file = tmp_path / "main.py.i2a-backup"
    backup_file.write_text("Existing backup", encoding="utf-8")

    approval = create_approval([
        FileChange(
            operation="modify",
            file_path="main.py",
            content="Updated",
            reason="Update the application.",
        )
    ])

    with pytest.raises(FileExistsError):
        executor.execute(approval, tmp_path)

    assert existing_file.read_text(encoding="utf-8") == "Original"
    assert backup_file.read_text(encoding="utf-8") == "Existing backup"

def test_preserves_original_file_if_atomic_replace_failes(
        tmp_path, monkeypatch
):

    import i2a.development.file_executor as executor_module

    executor = FileChangeExecutor()

    existing_file = tmp_path / "main.py"
    existing_file.write_text("original", encoding="utf-8")

    approval = create_approval([
        FileChange(
            operation="modify",
            file_path="main.py",
            content="updated",
            reason="Update the application.",
        )
    ])

    def failing_replace(source, destination):
        raise OSError("simulated replacement failure")

    monkeypatch.setattr(
        executor_module.os,
        "replace",
        failing_replace,
    )

    result = executor.execute(approval, tmp_path)

    assert result["results"][0]["status"] == "failed"
    assert existing_file.read_text(encoding="utf-8") == "original"
    assert (tmp_path / "main.py.i2a-backup").exists()
    assert not list(tmp_path.glob("*.i2a-tmp"))

def test_restores_file_from_backup(tmp_path):
    executor = FileChangeExecutor()

    existing_file = tmp_path / "main.py"
    existing_file.write_text("Original", encoding="utf-8")

    backup_file = executor._create_backup(existing_file)

    existing_file.write_text("Updated", encoding="utf-8")

    executor._restore_backup(existing_file, backup_file)

    assert existing_file.read_text(encoding="utf-8") == "Original"
    assert backup_file.exists()

def test_rollback_previous_changes_when_later_change_falls(
        tmp_path, monkeypatch
):
    executor = FileChangeExecutor()

    existing_file = tmp_path / "main.py"
    existing_file.write_text("Original", encoding="utf-8")

    approval = create_approval([
        FileChange(
            operation="create",
            file_path="new.py",
            content="print('new')",
            reason="Create another file.",
        ),
        FileChange(
            operation="modify",
            file_path="main.py",
            content="Updated",
            reason="Update the application.",
        ),
    ])

    original_atomic_write = executor._atomic_write

    def failing_atomic_write(target, content):
        raise OSError("Simulated failure")

    monkeypatch.setattr(
        executor,
        "_atomic_write",
        failing_atomic_write,
    )

    result = executor.execute(approval, tmp_path)

    assert existing_file.read_text(encoding="utf-8") == "Original"
    assert not (tmp_path / "new.py").exists()

    
def test_removes_partially_created_file_when_write_failes(
        tmp_path, monkeypatch
):
    from pathlib import Path

    executor = FileChangeExecutor()

    approval = create_approval([
        FileChange(
            operation="create",
            file_path="main.py",
            content="print('Hello Kenya')",
            reason="Create the entry point.",
        )
    ])

    created_file = tmp_path / "main.py"
    original_open = Path.open

    class FailingWriter:
        def __init__(self, file):
            self.file = file

        def __enter__(self):
            self.file.__enter__()
            return self

        def __exit__(self, *args):
            return self.file.__exit__(*args)

        def write(self, content):
            self.file.write(content[:5])
            raise OSError("Simulated partial write failure.")

    def failing_open(path, mode="r", *args, **kwargs):
        file = original_open(path, mode, *args, **kwargs)

        if path == created_file and mode == "x":
            return FailingWriter(file)

        return file
    
    monkeypatch.setattr(Path, "open", failing_open)

    result = executor.execute(approval, tmp_path)

    assert result["results"][0]["status"] == "failed"
    assert not created_file.exists()