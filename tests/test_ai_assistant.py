import pytest

from i2a.ai.assistant import I2AAssistant
from i2a.ai.prompts import I2A_SYSTEM_PROMPT

class FakeProvider:
    """Simulates an AI provider for testing."""

    def __init__(self):
        self.last_prompt = None

    def generate(self, prompt: str) -> str:
        self.last_prompt = prompt
        return "I2A is a desktop automation engine."

def test_assistant_returns_ai_response():
    provider = FakeProvider()
    assistant = I2AAssistant(provider=provider)

    response = assistant.ask("What is I2A?")

    assert response == "I2A is a desktop automation engine."

def test_assistant_includes_system_instructions():
    provider = FakeProvider()
    assistant = I2AAssistant(provider=provider)

    assistant.ask("Explain I2A.")

    assert I2A_SYSTEM_PROMPT in provider.last_prompt

def test_assistant_includes_user_instruction():
    provider = FakeProvider()
    assistant = I2AAssistant(provider=provider)

    assistant.ask("Build a python calculator.")

    assert "Build a python calculator." in provider.last_prompt

def test_assistant_rejects_empty_instruction():
    assistant = I2AAssistant(provider=FakeProvider())

    with pytest.raises(ValueError):
        assistant.ask("")

def test_assistant_rejects_whitespace_instruction():
    assistant = I2AAssistant(provider=FakeProvider())

    with pytest.raises(ValueError):
        assistant.ask(" ")