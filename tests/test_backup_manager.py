import hashlib
from pathlib import Path

import pytest

from i2a.development.backup_manager import BackupManager

def test_initializes_with_valid_workspace(tmp_path: Path) -> None:
    manager = BackupManager(tmp_path)

    assert manager.workspace == tmp_path.resolve()

def test_rejects_nonexistent_workspace(tmp_path: Path) -> None:
    workspace = tmp_path / "missing"

    with pytest.raises(FileNotFoundError):
        BackupManager(workspace)

def test_rejects_file_as_workspace(tmp_path: Path) -> None:
    workspace = tmp_path / "file.txt"
    workspace.write_text("test", encoding="utf-8")

    with pytest.raises(NotADirectoryError):
        BackupManager(workspace)

def test_lists_backup_files(tmp_path: Path) -> None:
    backup = tmp_path / "example.py.i2a-backup"
    backup.write_text("original content", encoding="utf-8")

    ordinary_file = tmp_path / "example.py"
    ordinary_file.write_text("updated content", encoding="utf-8")

    manager = BackupManager(tmp_path)

    assert manager.list_backups() == [
        Path("example.py.i2a-backup")
    ]

def test_verifies_valid_backup(tmp_path: Path) -> None:
    backup = tmp_path / "example.py.i2a-backup"
    content = "original content"

    backup.write_text(content, encoding="utf-8")

    checksum = hashlib.sha256(
        content.encode("utf-8")
    ).hexdigest()

    checksum_path = backup.with_name(
        f"{backup.name}.sha256"
    )

    checksum_path.write_text(checksum, encoding="utf-8")

    manager = BackupManager(tmp_path)

    result = manager.verify_backup(
        Path("example.py.i2a-backup")
    )

    assert result["valid"] is True
    assert result["checksum"] == checksum

def test_rejects_corrupted_backup(tmp_path: Path) -> None:
    backup = tmp_path / "example.py.i2a-backup"
    backup.write_text("modified content", encoding="utf-8")

    original_checksum = hashlib.sha256(
        b"original content"
    ).hexdigest()

    checksum_path = backup.with_name(
        f"{backup.name}.sha256"
    )
    checksum_path.write_text(
        original_checksum,
        encoding="utf-8",
    )

    manager = BackupManager(tmp_path)

    with pytest.raises(
        OSError,
        match="Backup integrity verification failed",
    ):
        manager.verify_backup(
            Path("example.py.i2a-backup")
        )

def test_rejects_backup_without_checksum(tmp_path: Path) -> None:
    backup = tmp_path / "example.py.i2a-backup"
    backup.write_text("original content", encoding="utf-8")

    manager = BackupManager(tmp_path)

    with pytest.raises(
        FileNotFoundError,
        match="Backup checksum is missing",
    ):
        manager.verify_backup(
            Path("example.py.i2a-backup")
        )

def test_rejects_invalid_checksum_metadata(tmp_path: Path) -> None:
    backup = tmp_path / "example.py.i2a-backup"
    backup.write_text("original content", encoding="utf-8")

    checksum_path = backup.with_name(
        f"{backup.name}.sha256"
    )
    checksum_path.write_text(
        "invalid-checksum",
        encoding="utf-8",
    )

    manager = BackupManager(tmp_path)

    with pytest.raises(
        OSError,
        match="Invalid backup checksum",
    ):
        manager.verify_backup(
            Path("example.py.i2a-backup")
        )

def test_inspects_backups(tmp_path: Path) -> None:
    backup = tmp_path / "example.py.i2a-backup"
    content = "original content"
    backup.write_text(content, encoding="utf-8")

    checksum = hashlib.sha256(
        content.encode("utf-8")
    ).hexdigest()

    checksum_path = backup.with_name(
        f"{backup.name}.sha256"
    )
    checksum_path.write_text(checksum, encoding="utf-8")

    manager = BackupManager(tmp_path)

    report = manager.inspect_backups()

    assert len(report) == 1
    assert report[0]["status"] == "valid"
    assert report[0]["checksum"] == checksum

def test_finds_backup_without_checksum(tmp_path: Path) -> None:
    backup = tmp_path / "example.py.i2a-backup"
    backup.write_text("original content", encoding="utf-8")

    manager = BackupManager(tmp_path)

    orphaned = manager.find_orphaned_files()

    assert len(orphaned) == 1
    assert orphaned[0]["type"] == "backup_without_checksum"
    assert orphaned[0]["path"] == str(
        Path("example.py.i2a-backup")
    )

def test_finds_checksum_without_backup(tmp_path: Path) -> None:
    checksum = tmp_path / "missing.py.i2a-backup.sha256"
    checksum.write_text("some-checksum", encoding="utf-8")

    manager = BackupManager(tmp_path)

    orphaned = manager.find_orphaned_files()

    assert len(orphaned) == 1
    assert orphaned[0]["type"] == "checksum_without_backup"
    assert orphaned[0]["path"] == str(
        Path("missing.py.i2a-backup.sha256")
    )

def test_ignores_symbolic_link_backups(tmp_path: Path) -> None:
    real_file = tmp_path / "real.py.i2a-backup"
    real_file.write_text("backup content", encoding="utf-8")

    linked_file = tmp_path / "linked.py.i2a-backup"

    try:
        linked_file.symlink_to(real_file)
    except (OSError, NotImplementedError):
        pytest.skip("Symbolic links are not supported.")

    manager = BackupManager(tmp_path)

    assert manager.list_backups() == [
        Path("real.py..i2a-backup")
    ]