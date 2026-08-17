class LLMClient:
    def __init__(self, model_name: str = "mock-model"):
        self.model_name = model_name

    def generate(self, prompt: str):
        return {
            "model": self.model_name,
            "prompt": prompt,
            "response": "This is a mock LLM response for usage tracking.",
        }
