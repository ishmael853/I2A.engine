
import json

import pytest

from i2a.development.proposal_generator import (
    DevelopmentProposalGenerator,
)


VALID_RESPONSE = {
    "project_name": "Calculator",
    "summary": "Create a basic calculator application.",
    "changes": [
        {
            "operation": "create",
            "file_path": "src/main.py",
            "content": "print('Calculator')",
            "reason": "Create the application entry point.",
        }
    ],
}


class FakeAssistant:
    def __init__(self, response):
        self.response = response
        self.last_prompt = None

    def ask(self, instruction):
        self.last_prompt = instruction
        return self.response


def test_generates_valid_proposal():
    assistant = FakeAssistant(json.dumps(VALID_RESPONSE))
    generator = DevelopmentProposalGenerator(assistant=assistant)

    proposal = generator.generate({
        "project_name": "Calculator",
        "development_steps": ["Create the application."],
    })

    assert proposal.project_name == "Calculator"
    assert len(proposal.changes) == 1
    assert proposal.changes[0].file_path == "src/main.py"


def test_rejects_empty_development_plan():
    assistant = FakeAssistant("{}")
    generator = DevelopmentProposalGenerator(assistant=assistant)

    with pytest.raises(ValueError):
        generator.generate({})


def test_rejects_invalid_json():
    assistant = FakeAssistant("Not valid JSON")
    generator = DevelopmentProposalGenerator(assistant=assistant)

    with pytest.raises(ValueError):
        generator.generate({"project_name": "Calculator"})


def test_rejects_unsafe_generated_file_path():
    invalid_response = VALID_RESPONSE.copy()
    invalid_response["changes"] = [
        {
            **VALID_RESPONSE["changes"][0],
            "file_path": "../outside.py",
        }
    ]

    assistant = FakeAssistant(json.dumps(invalid_response))
    generator = DevelopmentProposalGenerator(assistant=assistant)

    with pytest.raises(ValueError):
        generator.generate({"project_name": "Calculator"})


def test_rejects_non_dictionary_development_plan():
    assistant = FakeAssistant(json.dumps(VALID_RESPONSE))
    generator = DevelopmentProposalGenerator(assistant=assistant)

    with pytest.raises(TypeError):
        generator.generate("Build a calculator.")
