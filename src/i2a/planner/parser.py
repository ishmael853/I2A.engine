from dataclasses import dataclass

@dataclass
class ParsedIntent:
    """A normalized representation of a user's instruction."""

    original_text: str
    normalized_text: str
    tokens: list[str]

class IntentParser:
    """Prepares natural-language"""

    def parse(self, instruction: str) -> ParsedIntent:
        if not isinstance(instruction, str):
            raise TypeError("Instruction must be a string.")

        cleaned = instruction.strip()

        if not cleaned:
            raise ValueError("Instruction cannot be empty.")

        normalized = " ".join(cleaned.split())

        tokens = [
            word.strip(".,!?;:()[]{}\"'").lower()
            for word in normalized.split()
        ]

        tokens = [token for token in tokens if token]

        return ParsedIntent(
            original_text=instruction,
            normalized_text=normalized,
            tokens=tokens,
        )