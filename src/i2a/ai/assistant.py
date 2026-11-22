from i2a.ai.ollama_provider import OllamaProvider
from i2a.ai.prompts import I2A_SYSTEM_PROMPT

class I2AAssistant:
    """Provides AI assistant using the I2A system instruction."""

    def __init__(
            self,
            provider: OllamaProvider | None = None,
    ) -> None:
        self.provider = provider or OllamaProvider()

    def ask(self, instruction: str) -> str:
        """Send an instruction to the I2A AI assistant."""

        if not isinstance(instruction, str) or not instruction.strip():
            raise ValueError("Instruction cannot be empty.")

        prompt = (
            f"{I2A_SYSTEM_PROMPT}\n\n"
            f"USER INSTRUCTION:\n{instruction.strip()}\n\n"
            "Respond as the AI assistant for I2A."
        )

        return self.provider.generate(prompt)