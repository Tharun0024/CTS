import os
from dotenv import load_dotenv

load_dotenv()

# Base directories
WORKSPACE_DIR = r"c:\Users\swaro\OneDrive\Documents\agent2"
PROJECT_COMPANION_DIR = r"c:\Users\swaro\OneDrive\Documents\project\prior-auth-companion"

# Data file paths
DB_PATH = os.path.join(WORKSPACE_DIR, "agent2.db")
FHIR_DIR = r"C:\Users\swaro\Downloads\synthea-master\output\fhir"
POLICIES_DIR = os.path.join(PROJECT_COMPANION_DIR, "policies")
CMS_JSONL_PATH = r"c:\Users\swaro\OneDrive\Documents\cms_rag_chunks_8policies.jsonl"

# Configuration parameters
MAX_RESUBMISSION_ATTEMPTS = 3
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# Ensure workspace directory exists
os.makedirs(WORKSPACE_DIR, exist_ok=True)
