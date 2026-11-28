import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from i2a.development.retention_approval import BackupRetentionApproval
from i2a.development.retention_proposal import BackupRetentionProposal
from i2a.development.retention_executor import BackupRetentionExecutor

def create_approved_proposal(
        workspace: Path,
        backup_name: str = "example.py.i2a-backup",
) -> BackupRetentionApproval:
    """Create a backup and an approved retention proposal."""

    backup = workspace / backup_name
    content = "original content"
    backup.write_text(content, encoding="utf-8")

    checksum = hashlib.sha256(
        content.encode("utf-8")
    ).hexdigest()

    checksum_path = backup.with_name(
        f"{backup.name}.sha256"
    )
    checksum_path.write_text(checksum, encoding="utf-8")

    metadata = {
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    metadata_path = backup.with_name(
        f"{backup.name}.metadata.json"
    )
    metadata_path.write_text(
        json.dumps(metadata),
        encoding="utf-8",
    )

    proposal = BackupRetentionProposal(
        workspace=str(workspace.resolve()),
        max_age_days=30,
        backups=[backup_name],
        ages_days=[35.0],
        reasons=["Backup exceeds the retention period."],
    )

    approval = BackupRetentionApproval(proposal)
    approval.approve()

    return approval

def test_initializes_with_valid_workspace(
        tmp_path: Path,
) -> None:
    executor = BackupRetentionExecutor(tmp_path)

    assert executor.workspace == tmp_path.resolve()

def test_rejects_pending_approval(tmp_path: Path) -> None:
    backup = tmp_path / "example.py.i2a-backup"

    proposal = BackupRetentionProposal(
        workspace=str(tmp_path.resolve()),
        max_age_days=30,
        backups=[backup.name],
    )

    approval = BackupRetentionApproval(proposal)
    executor = BackupRetentionExecutor(tmp_path)

    with pytest.raises(
        ValueError,
        match="explicit approval",
    ):
        executor.execute(approval)

def test_rejects_rejected_approval(tmp_path: Path) -> None:
    proposal = BackupRetentionProposal(
        workspace=str(tmp_path.resolve()),
        max_age_days=30,
        backups=["example.py.i2a-backup"],
    )

    approval = BackupRetentionApproval(proposal)
    approval.reject()

    executor = BackupRetentionExecutor(tmp_path)

    with pytest.raises(
        ValueError,
        match="explicit approval",
    ):
        executor.execute(approval)

def test_rejects_invalid_approval_type(
        tmp_path: Path,
) -> None:
    executor = BackupRetentionExecutor(tmp_path)

    with pytest.raises(
        TypeError,
        match="BackupRetentionApproval",
    ):
        executor.execute("invalid approval")

def test_rejects_proposal_from_different_workspace(
        tmp_path: Path,
) -> None:
    other_workspace = tmp_path / "other"
    other_workspace.mkdir()

    proposal = BackupRetentionProposal(
        workspace=str(other_workspace.resolve()),
        max_age_days=30,
        backups=["example.py.i2a-backup"],
    )

    approval = BackupRetentionApproval(proposal)
    approval.approve()

    executor = BackupRetentionExecutor(tmp_path)

    with pytest.raises(
        ValueError,
        match="different workspace"
    ):
        executor.execute(approval)

def test_removes_approved_backup_and_sidecars(
        tmp_path: Path,
) -> None:
    approval = create_approved_proposal(tmp_path)
    executor = BackupRetentionExecutor(tmp_path)

    result = executor.execute(approval)

    backup = tmp_path / "example.py.i2a-backup"

    assert result["successful"] == [
        "example.py.i2a-backup"
    ]
    assert result["failed"] == []
    assert not backup.exists()
    assert not backup.with_name(
        f"{backup.name}.sha256"
    ).exists()
    assert not backup.with_name(
        f"{backup.name}.metadata.json"
    ).exists()

def test_does_not_remove_corrupted_backup(
        tmp_path: Path,
) -> None:
    approval = create_approved_proposal(tmp_path)

    backup = tmp_path / "example.py.i2a-backup"
    backup.write_text("modified content", encoding="utf-8")

    executor = BackupRetentionExecutor(tmp_path)

    result = executor.execute(approval)

    assert result["successful"] == []
    assert len(result["failed"]) == 1
    assert backup.exists()
    assert backup.with_name(
        f"{backup.name}.sha256"
    ).exists()
    assert backup.with_name(
        f"{backup.name}.metadata.json"
    ).exists()

def test_does_not_remove_backup_without_checksum(
        tmp_path: Path,
) -> None:
    approval = create_approved_proposal(tmp_path)

    backup = tmp_path / "example.py.i2a-backup"
    checksum = backup.with_name(f"{backup.name}.sha256")
    checksum.unlink()

    executor = BackupRetentionExecutor(tmp_path)

    result = executor.execute(approval)

    assert result["successful"] == []
    assert len(result["failed"]) == 1
    assert backup.exists()
    assert not checksum.exists()

def test_does_not_remove_backup_without_metadata(
        tmp_path: Path,
) -> None:
    approval = create_approved_proposal(tmp_path)

    backup = tmp_path / "example.py.i2a-backup"
    metadata = backup.with_name(
        f"{backup.name}.metadata.json"
    )
    metadata.unlink()

    executor = BackupRetentionExecutor(tmp_path)

    result = executor.execute(approval)

    assert result["successful"] == []
    assert len(result["failed"]) == 1
    assert backup.exists()
    assert not metadata.exists()

def test_rejects_backup_path_traversal(
        tmp_path: Path,
) -> None:
    approval = BackupRetentionApproval(
        BackupRetentionProposal(
            workspace=str(tmp_path.resolve()),
            max_age_days=30,
            backups=["../outside.py.i2a-backup"],
        )
    )
    approval.approve()

    executor = BackupRetentionExecutor(tmp_path)

    result = executor.execute(approval)

    assert result["successful"] == []
    assert len(result["failed"]) == 1
    assert "Unsafe backup path" in result["failed"][0]["reason"]

def test_rejects_symbolic_link_backup(
        tmp_path: Path,
) -> None:
    real_backup = tmp_path / "real.py.i2a-backup"
    real_backup.write_text("original content", encoding="utf-8")

    linked_backup = tmp_path / "linked.py.i2a-backup"

    try:
        linked_backup.symlink_to(real_backup)
    except (OSError, NotImplementedError):
        pytest.skip("symbolic links are not supported.")

    checksum = hashlib.sha256(
        b"original content"
    ).hexdigest()

    linked_backup.with_name(
        f"{linked_backup.name}.sha256"
    ).write_text(checksum, encoding="utf-8")

    linked_backup.with_name(
        f"{linked_backup.name}.metadata.json"
    ).write_text(
        json.dumps({
            "created_at": datetime.now(timezone.utc).isoformat
        }),
        encoding="utf-8",
    )

    proposal = BackupRetentionProposal(
        workspace=str(tmp_path.resolve()),
        max_age_days=30,
        backups=[linked_backup.name],
    )
    approval = BackupRetentionApproval(proposal)
    approval.approve()

    executor = BackupRetentionExecutor(tmp_path)
    result = executor.execute(approval)

    assert result["successful"] == []
    assert len(result["failed"]) == 1
    assert real_backup.exists()
    assert linked_backup.is_symlink()

def test_reports_missing_backup(
        tmp_path: Path,
) -> None:
    proposal = BackupRetentionProposal(
        workspace=str(tmp_path.resolve()),
        max_age_days=30,
        backups=["missing.py.i2a-backup"],
    )

    approval = BackupRetentionApproval(proposal)
    approval.approve()

    executor = BackupRetentionExecutor(tmp_path)

    result = executor.execute(approval)

    assert result["successful"] == []
    assert len(result["failed"]) == 1
    assert result["failed"][0]["path"] == (
        "missing.py.i2a-backup"
    )
    assert "Backup file does not exist" in (
        result["failed"][0]["reason"]
    )

def test_does_not_remove_backup_with_invalid_checksum(
        tmp_path: Path,
) -> None:
    approval = create_approved_proposal(tmp_path)

    backup = tmp_path / "example.py.i2a-backup"
    checksum = backup.with_name(f"{backup.name}.sha256")
    checksum.write_text("invalid-checksums", encoding="utf-8")

    executor = BackupRetentionExecutor(tmp_path)

    result = executor.execute(approval)

    assert result["successful"] == []
    assert len(result["failed"]) == 1
    assert backup.exists()
    assert checksum.exists()

def test_preserves_backup_when_sidecar_deletion_fails(
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch
) -> None:
    approval = create_approved_proposal(tmp_path)

    backup = tmp_path / "example.py.i2a-backup"
    metadata = backup.with_name(
        f"{backup.name}.metadata.json"
    )

    original_unlink = Path.unlink

    def failing_unlink(
            path: Path,
            *args,
            **kwargs,
    ) -> None:
        if path == metadata:
            raise PermissionError("Simulated deletion failure.")

        original_unlink(path, *args, **kwargs)

    monkeypatch.setattr(Path, "unlink", failing_unlink)

    executor = BackupRetentionExecutor(tmp_path)
    result = executor.execute(approval)

    assert result["successful"] == []
    assert len(result["failed"]) == 1
    assert backup.exists()
    assert metadata.exists()