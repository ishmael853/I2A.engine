from pathlib import Path

import pytest

from i2a.development.backup_cleanup import (
    BackupCleanupApproval,
    BackupCleanupManager,
    BackupCleanupProposal,
)

def test_creates_empty_cleanup_proposal(tmp_path: Path) -> None:
    manager = BackupCleanupManager(tmp_path)

    proposal = manager.create_proposal()

    assert proposal.workspace == str(tmp_path.resolve())
    assert proposal.files == []
    assert proposal.reasons == []

def test_proposes_orphaned_checksum_only(tmp_path: Path) -> None:
    checksum = tmp_path / "missing.py.i2a-backup.sha256"
    checksum.write_text("some-checksum", encoding="utf-8")

    manager = BackupCleanupManager(tmp_path)
    proposal = manager.create_proposal()

    assert proposal.files == [
        "missing.py.i2a-backup.sha256"
    ]

    assert proposal.reasons == [
        "Checksum has no matching backup file."
    ]

def test_preservers_backup_without_checksum(tmp_path: Path) -> None:
    backup = tmp_path / "important.py.i2a-backup"
    backup.write_text("original content", encoding="utf-8")

    manager = BackupCleanupManager(tmp_path)
    proposal = manager.create_proposal()

    assert proposal.files == []
    assert backup.exists()

def test_rejects_invalid_proposal_type() -> None:
    with pytest.raises(TypeError):
        BackupCleanupApproval("invalid")

def test_approval_starts_pending() -> None:
    proposal = BackupCleanupProposal(workspace="workspace")
    approval = BackupCleanupApproval(proposal)

    assert approval.status == BackupCleanupApproval.PENDING

def test_approves_pending_proposal() -> None:
    proposal = BackupCleanupProposal(workspace="workspace")
    approval = BackupCleanupApproval(proposal)

    approval.approve()

    assert approval.status == BackupCleanupApproval.APPROVED

def test_rejects_pending_proposal() -> None:
    proposal = BackupCleanupProposal(workspace="workspace")
    approval = BackupCleanupApproval(proposal)

    approval.reject()


    assert approval.status == BackupCleanupApproval.REJECTED

def test_cannot_approve_rejected_proposal() -> None:
    proposal = BackupCleanupProposal(workspace="workspace")
    approval = BackupCleanupApproval(proposal)
    approval.reject()

    with pytest.raises(ValueError):
        approval.approve()


def test_cannot_reject_approved_proposal() -> None:
    proposal = BackupCleanupProposal(workspace="workspace")
    approval = BackupCleanupApproval(proposal)
    approval.approve()

    with pytest.raises(ValueError):
        approval.reject()