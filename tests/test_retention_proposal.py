from i2a.development.retention_proposal import BackupRetentionProposal


def test_creates_empty_retention_proposal() -> None:
    proposal = BackupRetentionProposal(
        workspace="/workspace",
        max_age_days=30,
    )

    assert proposal.backups == []
    assert proposal.ages_days == []
    assert proposal.reasons == []

def test_stores_proposed_backups() -> None:
    proposal = BackupRetentionProposal(
        workspace="/workspace",
        max_age_days=30,
        backups=["main.py.i2a-backup"],
        ages_days=[45.5],
        reasons=["Backup exceeds the retention period."]
    )

    assert proposal.backups == ["main.py.i2a-backup"]
    assert proposal.ages_days == [45.5]
    assert proposal.reasons == [
        "Backup exceeds the retention period."
    ]

def test_converts_proposal_to_dictionaty() -> None:
    proposal = BackupRetentionProposal(
        workspace="/workspace",
        max_age_days=30,
        backups=["main.py.i2a-backup"],
        ages_days=[45.5],
        reasons=["Backup exceeds the retention period."]
    )

    assert proposal.to_dict() == {
        "workspace": "/workspace",
        "max_age_days": 30,
        "backups": ["main.py.i2a-backup"],
        "ages_days": [45.5],
        "reasons": [
            "Backup exceeds the retention period."
        ],
    }

def test_dictionary_uses_independent_lists() -> None:
    proposal = BackupRetentionProposal(
        workspace="/workspace",
        max_age_days=30,
        backups=["main.py.i2a-backup"],
        ages_days=[45.5],
        reasons=["Backup exceeds the retention period."],
    )

    result = proposal.to_dict()
    result["backups"].append("others.py.i2a-backup")

    assert proposal.backups == ["main.py.i2a-backup"]