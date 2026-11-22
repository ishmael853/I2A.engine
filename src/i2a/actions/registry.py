from dataclasses import dataclass, field
from typing import Any


@dataclass
class ActionDefinition:
    """Describes an action supported by I2A."""

    name: str
    description: str
    required_parameters: list[str] = field(default_factory=list)
    optional_parameters: list[str] = field(default_factory=list)


class ActionRegistry:
    """Stores and retrieves supported action definitions."""

    def __init__(self) -> None:
        self._actions: dict[str, ActionDefinition] = {}

    def register(self, definition: ActionDefinition) -> None:
        name = definition.name.strip().lower()

        if not name:
            raise ValueError("Action name cannot be empty.")

        if name in self._actions:
            raise ValueError(f"Action '{name}' is already registered.")

        definition.name = name
        self._actions[name] = definition

    def get(self, name: str) -> ActionDefinition | None:
        return self._actions.get(name.strip().lower())

    def exists(self, name: str) -> bool:
        return name.strip().lower() in self._actions

    def list_actions(self) -> list[ActionDefinition]:
        return list(self._actions.values())

    def validate_parameters(
        self,
        name: str,
        parameters: dict[str, Any],
    ) -> list[str]:
        definition = self.get(name)

        if definition is None:
            return [f"Unknown action: {name}"]

        errors = []

        for parameter in definition.required_parameters:
            if parameter not in parameters:
                errors.append(
                    f"Missing required parameter '{parameter}'."
                )

        allowed = (
            set(definition.required_parameters)
            | set(definition.optional_parameters)
        )

        for parameter in parameters:
            if parameter not in allowed:
                errors.append(
                    f"Unexpected parameter '{parameter}'."
                )

        return errors


def create_default_registry() -> ActionRegistry:
    """Create a registry containing I2A's built-in actions."""

    registry = ActionRegistry()

    registry.register(
        ActionDefinition(
            name="open_url",
            description="Open a website in the default browser.",
            required_parameters=["url"],
        )
    )

    registry.register(
        ActionDefinition(
            name="wait",
            description="Pause execution for a specified duration.",
            required_parameters=["seconds"],
        )
    )

    registry.register(
        ActionDefinition(
            name="open_application",
            description="Open an approved desktop application, optionally with a folder or file.",
            required_parameters=["application"],
            optional_parameters=["path"],
        )
    )

    return registry
