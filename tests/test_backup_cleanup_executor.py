from pathlib import Path

import pytest

from i2a.development.backup_cleanup import (
    BackupCleanupApproval,
    BackupCleanupProposal,
)
from i2a.development.backup_cleanup_executor import (
    BackupCleanupExecutor,
)


def test_requires_cleanup_approval(tmp_path: Path) -> None:
    executor = BackupCleanupExecutor(tmp_path)
    proposal = BackupCleanupProposal(
        workspace=str(tmp_path.resolve()),
        files=["orphan.py.i2a-backup.sha256"],
    )
    approval = BackupCleanupApproval(proposal)

    with pytest.raises(ValueError, match="explicit approval"):
        executor.execute(approval)


def test_rejected_cleanup_cannot_execute(tmp_path: Path) -> None:
    executor = BackupCleanupExecutor(tmp_path)
    proposal = BackupCleanupProposal(
        workspace=str(tmp_path.resolve()),
        files=["orphan.py.i2a-backup.sha256"],
    )
    approval = BackupCleanupApproval(proposal)
    approval.reject()

    with pytest.raises(ValueError, match="explicit approval"):
        executor.execute(approval)


def test_removes_approved_orphaned_checksum(tmp_path: Path) -> None:
    checksum = tmp_path / "orphan.py.i2a-backup.sha256"
    checksum.write_text("checksum", encoding="utf-8")

    proposal = BackupCleanupProposal(
        workspace=str(tmp_path.resolve()),
        files=["orphan.py.i2a-backup.sha256"],
    )
    approval = BackupCleanupApproval(proposal)
    approval.approve()

    executor = BackupCleanupExecutor(tmp_path)
    result = executor.execute(approval)

    assert result["successful"] == ["orphan.py.i2a-backup.sha256"]
    assert result["failed"] == []
    assert not checksum.exists()


def test_never_removes_backup_file(tmp_path: Path) -> None:
    backup = tmp_path / "important.py.i2a-backup"
    backup.write_text("important content", encoding="utf-8")

    proposal = BackupCleanupProposal(
        workspace=str(tmp_path.resolve()),
        files=["important.py.i2a-backup"],
    )
    approval = BackupCleanupApproval(proposal)
    approval.approve()

    executor = BackupCleanupExecutor(tmp_path)
    result = executor.execute(approval)

    assert result["successful"] == []
    assert len(result["failed"]) == 1
    assert backup.exists()


def test_rejects_checksum_with_matching_backup(tmp_path: Path) -> None:
    backup = tmp_path / "important.py.i2a-backup"
    checksum = tmp_path / "important.py.i2a-backup.sha256"

    backup.write_text("important content", encoding="utf-8")
    checksum.write_text("checksum", encoding="utf-8")

    proposal = BackupCleanupProposal(
        workspace=str(tmp_path.resolve()),
        files=["important.py.i2a-backup.sha256"],
    )
    approval = BackupCleanupApproval(proposal)
    approval.approve()

    executor = BackupCleanupExecutor(tmp_path)
    result = executor.execute(approval)

    assert result["successful"] == []
    assert result["failed"][0]["path"] == ("important.py.i2a-backup.sha256")
    assert checksum.exists()
    assert backup.exists()


def test_rejects_path_traversal(tmp_path: Path) -> None:
    proposal = BackupCleanupProposal(
        workspace=str(tmp_path.resolve()),
        files=["../outside.py.i2a-backup.sha256"],
    )
    approval = BackupCleanupApproval(proposal)
    approval.approve()

    executor = BackupCleanupExecutor(tmp_path)
    result = executor.execute(approval)

    assert result["successful"] == []
    assert len(result["failed"]) == 1


def test_rejects_wrong_file_type(tmp_path: Path) -> None:
    file = tmp_path / "not-a-checksum.txt"
    file.write_text("data", encoding="utf-8")

    proposal = BackupCleanupProposal(
        workspace=str(tmp_path.resolve()),
        files=["not-a-checksum.txt"],
    )
    approval = BackupCleanupApproval(proposal)
    approval.approve()

    executor = BackupCleanupExecutor(tmp_path)
    result = executor.execute(approval)

    assert result["successful"] == []
    assert len(result["failed"]) == 1
    assert file.exists()


def test_rejects_different_workspace(tmp_path: Path) -> None:
    other_workspace = tmp_path / "other"
    other_workspace.mkdir()

    proposal = BackupCleanupProposal(
        workspace=str(other_workspace.resolve()),
        files=[],
    )
    approval = BackupCleanupApproval(proposal)
    approval.approve()

    executor = BackupCleanupExecutor(tmp_path)

    with pytest.raises(ValueError, match="different workspace"):
        executor.execute(approval)
