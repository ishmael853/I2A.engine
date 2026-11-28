from i2a.development.retention_approval import BackupRetentionApproval
from i2a.development.retention_proposal import BackupRetentionProposal

def create_proposal() -> BackupRetentionProposal:
    return BackupRetentionProposal(
        workspace="/workspace",
        max_age_days=30,
        backups=["main.py.i2a-backup"],
        ages_days=[45.5],
        reasons=["Backup exceeds the retention period."],
    )

def test_initializes_as_pending() -> None:
    approval = BackupRetentionApproval(create_proposal())

    assert approval.status == BackupRetentionApproval.PENDING

def test_approves_proposal() -> None:
    approval = BackupRetentionApproval(create_proposal())

    approval.approve()

    assert approval.status == BackupRetentionApproval.APPROVED

def test_rejects_proposal() -> None:
    approval = BackupRetentionApproval(create_proposal())

    approval.reject()

    assert approval.status == BackupRetentionApproval.REJECTED

def test_converts_approval_to_dictionary() -> None:
    proposal = create_proposal()
    approval = BackupRetentionApproval(proposal)

    assert approval.to_dict() == {
        "status": "pending",
        "proposal": proposal.to_dict(),
    }