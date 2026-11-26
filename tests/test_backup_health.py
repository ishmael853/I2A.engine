from i2a.development.backup_health import BackupHealthReport

def test_new_report_is_healthy() -> None:
    report = BackupHealthReport(
        workspace="workspace"
    )

    assert report.total_backups == 0
    assert report.valid_backups == 0
    assert report.invalid_backups == 0
    assert report.healthy is True

def test_report_detects_invalid_backups() -> None:
    report = BackupHealthReport(
        workspace="workspace",
        total_backups=3,
        valid_backups=2,
        invalid_backups=1,
    )

    assert report.healthy is False

def test_report_detects_backups_without_checksums() -> None:
    report = BackupHealthReport(
        workspace="workspace",
        total_backups=1,
        valid_backups=1,
        backups_without_checksums=[
            "example.py.i2a-backup"
        ],
    )

    assert report.healthy is False

def test_report_detects_checksums_without_backups() -> None:
    report = BackupHealthReport(
        workspace="workspace",
        checksums_without_backups=[
            "missing.py.i2a-backup.sha256"
        ],
    )

    assert report.healthy is False

def test_to_dict_returns_complete_report() -> None:
    report = BackupHealthReport(
        workspace="workspace",
        total_backups=2,
        valid_backups=1,
        invalid_backups=1,
        backups_without_checksums=[
            "example.py.i2a-backup"
        ],
        checksums_without_backups=[
            "missing.py.i2a-backup.sha256"
        ],
    )

    result = report.to_dict()

    assert result == {
        "workspace": "workspace",
        "total_backups": 2,
        "valid_backups": 1,
        "invalid_backups": 1,
        "backups_without_checksums": [
            "example.py.i2a-backup"
        ],
        "checksums_without_backups": [
            "missing.py.i2a-backup.sha256"
        ],
        "healthy": False,
    }