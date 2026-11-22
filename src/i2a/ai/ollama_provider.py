import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

class OllamaProvider:
    """Connects I2A to a locally running Ollama model."""

    def __init__(
            self,
            model: str = "qwen2.5:1.5b",
            base_url:str = "http://localhost:11434",
            timeout: int = 120,
    ) -> None:
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def generate(self, prompt: str) -> str:
        """Send a prompt to Ollama and return its response."""

        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError("Prompt cannot be empty.")

        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
        }

        request = Request(
            url=f"{self.base_url}/api/generate",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urlopen(request, timeout=self.timeout) as response:
                result = json.loads(
                    response.read().decode("utf-8")
                )

        except HTTPError as error:
            details = error.read().decode("utf-8", errors="replace")
            raise RuntimeError(
                f"Ollama API error ({error.code}): {details}"
            ) from error

        except URLError as error:
            raise RuntimeError(
                "Could not connect to Ollama. "
                "Make sure Ollama is running. "
            ) from error

        generated_text = result.get("response")

        if not isinstance(generated_text, str):
            raise RuntimeError(
                "Ollama returned an invalid response."
            )

        return generated_text.strip()