from i2a.development.proposal import (
    DevelopmentProposal,
    FileChange
)
from i2a.development.preview import FileChangePreview

def test_previews_new_file_without_creating_it(tmp_path):
    previewer = FileChangePreview()

    proposal = DevelopmentProposal(
        project_name="Demo",
        summary="Create a new Python file.",
        changes=[
            FileChange(
                operation="create",
                file_path="new.py",
                content="print('Hello')",
                reason="Add a new Script.",
            )
        ],
    )

    result = previewer.generate(proposal, tmp_path)

    assert result["total_changes"] == 1
    assert result["changes"][0]["current_content"] is None
    assert result["changes"][0]["proposed_content"] == "print('Hello')"
    assert not (tmp_path / "new.py").exists()

def test_previews_existing_file_modification(tmp_path):
    previewer = FileChangePreview()

    existing_file = tmp_path / "main.py"
    existing_file.write_text("Original", encoding="utf-8")

    proposal = DevelopmentProposal(
        project_name="Demo",
        summary="Update the main file.",
        changes=[
            FileChange(
                operation="modify",
                file_path="main.py",
                content="Updated",
                reason="Improve the application.",
            )
        ],
    )

    result = previewer.generate(proposal, tmp_path)

    change = result["changes"][0]

    assert change["current_content"] == "Original"
    assert change["proposed_content"] == "Updated"
    assert "-Original" in change["diff"]
    assert "+Updated" in change["diff"]
    assert existing_file.read_text(encoding="utf-8") == "Original"

def test_rejects_existing_file_creation(tmp_path):
    previewer = FileChangePreview()

    existing_file = tmp_path / "main.py"
    existing_file.write_text("Original", encoding="utf-8")

    proposal = DevelopmentProposal(
        project_name="Demo",
        summary="Create a file.",
        changes=[
            FileChange(
                operation="create",
                file_path="main.py",
                content="New content",
                reason="Create a script",
            )
        ],
    )

    import pytest

    with pytest.raises(FileExistsError):
        previewer.generate(proposal, tmp_path)

def test_rejects_file_path_outside_workspace(tmp_path):
    previewer = FileChangePreview()

    proposal = DevelopmentProposal(
        project_name="Demo",
        summary="Create a file.",
        changes=[
            FileChange(
                operation="create",
                file_path="../outside.py",
                content="Unsafe",
                reason="Test path validation.",
            )
        ],
    )

    import pytest

    with pytest.raises(ValueError):
        previewer.generate(proposal, tmp_path)

def test_rejects_modification_of_missing_file(tmp_path):
    import pytest

    previewer = FileChangePreview()

    proposal = DevelopmentProposal(
        project_name="Demo",
        summary="Modify a missing file.",
        changes=[
            FileChange(
                operation="modify",
                file_path="missing.py",
                content="Updated",
                reason="Update the script.",
            )
        ],
    )

    with pytest.raises(FileNotFoundError):
        previewer.generate(proposal, tmp_path)

def test_rejects_modification_when_backup_exists(tmp_path):
    import pytest

    previewer = FileChangePreview()

    existing_file = tmp_path / "main.py"
    existing_file.write_text("Original", encoding="utf-8")

    backup_file = tmp_path / "main.py.i2a-backup"
    backup_file.write_text("Previous backup", encoding="utf-8")

    proposal = DevelopmentProposal(
        project_name="Demo",
        summary="Update the main file.",
        changes=[
            FileChange(
                operation="modify",
                file_path="main.py",
                content="Updated",
                reason="Improve the application.",
            )
        ],
    )

    with pytest.raises(FileExistsError):
        previewer.generate(proposal, tmp_path)

def test_rejects_creation_when_parent_directory_is_missing(tmp_path):
    import pytest

    previewer = FileChangePreview()

    proposal = DevelopmentProposal(
        project_name="Demo",
        summary="Create a file in a missing directory.",
        changes=[
            FileChange(
                operation="create",
                file_path="missing/new.py",
                content="print('Hello')",
                reason="Add a new script.",
            )
        ],
    )

    with pytest.raises(FileNotFoundError):
        previewer.generate(proposal, tmp_path)