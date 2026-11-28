import pytest

from i2a.development.retention_policy import BackupRetentionPolicy

def test_uses_default_retention_period() -> None:
    policy = BackupRetentionPolicy()

    assert policy.max_age_days == 30

def test_accepts_custom_retention_period() -> None:
    policy = BackupRetentionPolicy(max_age_days=14)

    assert policy.max_age_days == 14

def test_rejects_zero_retention_period() -> None:
    with pytest.raises(ValueError):
        BackupRetentionPolicy(max_age_days=0)

def test_rejects_negative_retention_period() -> None:
    with pytest.raises(ValueError):
        BackupRetentionPolicy(max_age_days=-1)

def test_rejects_non_integer_retention_period() -> None:
    with pytest.raises(TypeError):
        BackupRetentionPolicy(max_age_days=1.5)

def test_rejects_boolean_retention_period() -> None:
    with pytest.raises(TypeError):
        BackupRetentionPolicy(max_age_days=True)

def test_converts_policy_to_dictionary() -> None:
    policy = BackupRetentionPolicy(max_age_days=14)

    assert policy.to_dict() == {
        "max_age_days": 14,
    }