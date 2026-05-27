import os

# LLM Configuration
# Supports OpenAI-compatible endpoints via OPENAI_API_BASE
LLM_MODEL = os.environ.get("OPENAI_MODEL_NAME", "astron-code-latest")
LLM_BASE_URL = os.environ.get("OPENAI_API_BASE", "")
LLM_API_KEY = os.environ.get("OPENAI_API_KEY", "")
