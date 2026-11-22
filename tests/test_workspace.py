import pytest

from i2a.development.workspace import WorkspaceAnalyzer


def test_analyze_workspace(tmp_path):
    project = tmp_path / "project"
    project.mkdir()

    source_file = project / "main.py"
    source_file.write_text("print('hello')", encoding="utf-8")

    tests_directory = project / "tests"
    tests_directory.mkdir()

    test_file = tests_directory / "test_main.py"
    test_file.write_text("def test_example(): pass", encoding="utf-8")

    analyzer = WorkspaceAnalyzer()
    analysis = analyzer.analyze(project)

    assert analysis.root == str(project.resolve())
    assert str(tests_directory) in analysis.directories

    discovered_names = {
        file.name
        for file in analysis.files
    }

    assert "main.py" in discovered_names
    assert "test_main.py" in discovered_names


def test_excludes_common_directories(tmp_path):
    project = tmp_path / "project"
    project.mkdir()

    git_directory = project / ".git"
    git_directory.mkdir()

    venv_directory = project / ".venv"
    venv_directory.mkdir()

    (git_directory / "config").write_text(
        "ignored",
        encoding="utf-8",
    )

    (venv_directory / "python.exe").write_text(
        "ignored",
        encoding="utf-8",
    )

    (project / "main.py").write_text(
        "print('hello')",
        encoding="utf-8",
    )

    analyzer = WorkspaceAnalyzer()
    analysis = analyzer.analyze(project)

    discovered_names = {
        file.name
        for file in analysis.files
    }

    assert "main.py" in discovered_names
    assert "config" not in discovered_names
    assert "python.exe" not in discovered_names

    assert str(git_directory) in analysis.excluded_directories
    assert str(venv_directory) in analysis.excluded_directories


def test_rejects_missing_workspace():
    analyzer = WorkspaceAnalyzer()

    with pytest.raises(FileNotFoundError):
        analyzer.analyze("C:\\this\\workspace\\does\\not\\exist")


def test_rejects_file_as_workspace(tmp_path):
    file_path = tmp_path / "not_a_workspace.txt"
    file_path.write_text("hello", encoding="utf-8")

    analyzer = WorkspaceAnalyzer()

    with pytest.raises(NotADirectoryError):
        analyzer.analyze(file_path)


def test_workspace_analysis_to_dict(tmp_path):
    project = tmp_path / "project"
    project.mkdir()

    source_file = project / "main.py"
    source_file.write_text("print('hello')", encoding="utf-8")

    analyzer = WorkspaceAnalyzer()
    analysis = analyzer.analyze(project)

    result = analysis.to_dict()

    assert result["root"] == str(project.resolve())
    assert isinstance(result["directories"], list)
    assert isinstance(result["files"], list)
    assert result["files"][0]["name"] == "main.py"