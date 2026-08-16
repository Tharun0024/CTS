import os
from dotenv import load_dotenv

load_dotenv()

# Base directories
# Use project-relative paths instead of hardcoded user paths
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORKSPACE_DIR = os.path.join(PROJECT_ROOT, "agent2", "workspace")
PROJECT_COMPANION_DIR = os.path.join(PROJECT_ROOT, "payer-knowledge")

# Data file paths
DB_PATH = os.path.join(WORKSPACE_DIR, "agent2.db")
FHIR_DIR = os.path.join(PROJECT_ROOT, "data", "raw")  # Fallback location
POLICIES_DIR = os.path.join(PROJECT_COMPANION_DIR, "policies")
CMS_JSONL_PATH = os.path.join(PROJECT_ROOT, "payer-knowledge", "CMS_NCD_LCD_Dataset.json")

# Configuration parameters
MAX_RESUBMISSION_ATTEMPTS = 3

# NVIDIA LLM Configuration
NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY", "")
NVIDIA_BASE_URL = os.getenv("NVIDIA_API_URL", "https://integrate.api.nvidia.com/v1")
NVIDIA_MODEL = os.getenv("NVIDIA_MODEL", "meta/llama-3.1-8b-instruct")

# Legacy Gemini config (for compatibility)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# Ensure workspace directory exists
os.makedirs(WORKSPACE_DIR, exist_ok=True)
