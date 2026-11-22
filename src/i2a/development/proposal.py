from dataclasses import dataclass, field

@dataclass
class FileChange:
    """Represents a proposed change to a project file."""

    operation: str
    file_path: str
    content: str
    reason: str

    def to_dict(self) -> dict:
        return {
            "operation": self.operation,
            "file_path": self.file_path,
            "content": self.content,
            "reason": self.reason,
        }

@dataclass
class DevelopmentProposal:
    """Contains proposed file changes for a development task."""

    project_name: str
    summary: str
    changes: list[FileChange] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "project_name":self.project_name,
            "summary": self.summary,
            "changes": [
                change.to_dict()
                for change in self.changes
            ],
        }