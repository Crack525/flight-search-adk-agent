import os
from dotenv import load_dotenv
import logging

# Load environment variables from .env file
load_dotenv()

logger = logging.getLogger(__name__)

# --- Core Configuration ---
GOOGLE_CLOUD_PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT")
GOOGLE_CLOUD_LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
GEMINI_MODEL_NAME = os.getenv("GEMINI_MODEL_NAME", "gemini-1.5-pro-latest") # Or your preferred model for Vertex AI

# --- Agent Specific Configuration ---
AGENT_NAME = 'flight_search_assistant_vertex'
AGENT_SYSTEM_INSTRUCTION = """Your SOLE first task is to call the 'search_flights' tool. Do NOT ask questions. Do NOT respond with text. Extract parameters from the user's query and call 'search_flights' IMMEDIATELY.
After 'search_flights' is called, your SOLE second task is to call 'search_google_flights'. Do NOT ask questions. Do NOT respond with text. Use parameters from the user's query and call 'search_google_flights' IMMEDIATELY.
After BOTH tools are called, then and ONLY then, analyze their combined results and provide a text summary to the user."""

def get_config():
    """Returns a dictionary of key configurations."""
    config = {
        "GOOGLE_CLOUD_PROJECT": GOOGLE_CLOUD_PROJECT,
        "GOOGLE_CLOUD_LOCATION": GOOGLE_CLOUD_LOCATION,
        "GEMINI_MODEL_NAME": GEMINI_MODEL_NAME,
        "AGENT_NAME": AGENT_NAME,
        "AGENT_SYSTEM_INSTRUCTION": AGENT_SYSTEM_INSTRUCTION
    }
    # Basic validation
    if not GOOGLE_CLOUD_PROJECT:
        logger.warning("GOOGLE_CLOUD_PROJECT environment variable is not set. This is required for Vertex AI.")
    return config

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    conf = get_config()
    logger.info(f"Loaded configuration: {conf}")
    if not conf["GOOGLE_CLOUD_PROJECT"]:
        logger.error("Critical: GOOGLE_CLOUD_PROJECT must be set in your .env file for Vertex AI operations.")
