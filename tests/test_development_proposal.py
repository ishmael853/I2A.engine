from i2a.development.proposal import (
    DevelopmentProposal,
    FileChange,
)

def test_file_change_to_dict():
    change = FileChange(
        operation="create",
        file_path="src/main.py",
        content="print('hello')",
        reason="Create the application entry point.",
    )

    assert change.to_dict() == {
        "operation": "create",
        "file_path": "src/main.py",
        "content": "print('hello')",
        "reason": "Create the application entry point.",
    }

def test_development_proposal_to_dict():
    change = FileChange(
        operation="create",
        file_path="src/main.py",
        content="print('hello')",
        reason="Create the entry point.",
    )

    proposal = DevelopmentProposal(
        project_name="sample project",
        summary="Create a basic python application.",
        changes=[change],
    )

    result = proposal.to_dict()

    assert result["project_name"] == "sample project"
    assert result["summary"] == "Create a basic python application."
    assert len(result["changes"]) == 1
    assert result["changes"][0]["file_path"] == "src/main.py"

def test_development_proposal_supports_empty_changes():
    proposal = DevelopmentProposal(
        project_name="Sample project",
        summary="No chaanges proposed.",
    )

    assert proposal.changes == []
    assert proposal.to_dict()["changes"] == []