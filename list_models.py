import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()

# Configure the API key
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)

# List available models
try:
    print("Available models:")
    for model in genai.list_models():
        print(f"- {model.name}")
        if hasattr(model, 'supported_generation_methods'):
            print(f"  Supported methods: {model.supported_generation_methods}")
        print()
except Exception as e:
    print(f"Error listing models: {e}")