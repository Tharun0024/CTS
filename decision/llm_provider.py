import os
import json
import urllib.request
import urllib.error
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


def load_env():
    """
    Manually parses the local .env file and sets environment variables.
    Fulfills Phase 3 zero-dependency constraints.
    """
    # Systematically locate the root .env file relative to the source directory
    src_dir = os.path.dirname(os.path.abspath(__file__))
    possible_paths = [
        os.path.join(src_dir, "..", ".env"),
        os.path.join(src_dir, "..", "..", ".env"),
        ".env",
        "../.env",
        "y:\\cts-dca1\\.env",
    ]
    for path in possible_paths:
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith("#"):
                            continue
                        if "=" in line:
                            k, v = line.split("=", 1)
                            # Strip whitespace and wrapping quotes
                            val_str = v.strip().strip("'\"")
                            os.environ[k.strip()] = val_str
                break
            except Exception:
                pass


# Auto load variable on import
load_env()


class LLMProvider(ABC):
    """
    Abstract base class for replaceable LLM providers.
    """

    @abstractmethod
    def generate_structured_response(self, prompt: str, system_prompt: str) -> str:
        """
        Submits prompt and system prompt to LLM and returns the raw response string (expected to be JSON).
        """
        pass


class NVIDIAProvider(LLMProvider):
    """
    Replaceable NVIDIA NIM API provider using standard library urllib.
    No external request or OpenAI SDK dependencies are required.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        # Reload env variables in case of updates
        load_env()
        # 1. Load keys safely from climate configuration or os environment
        self.api_key = api_key if api_key is not None else os.environ.get("NVIDIA_API_KEY")
        self.model = model if model is not None else (os.environ.get("NVIDIA_MODEL") or "z-ai/glm-5.2")
        
        raw_base = (
            base_url
            or os.environ.get("NVIDIA_API_URL")
            or "https://integrate.api.nvidia.com/v1"
        )
        # Parse endpoint to ensure /chat/completions suffix
        base_stripped = raw_base.rstrip("/")
        if not base_stripped.endswith("/chat/completions"):
            self.endpoint = base_stripped + "/chat/completions"
        else:
            self.endpoint = base_stripped

    def generate_structured_response(self, prompt: str, system_prompt: str) -> str:
        # Check for empty API key
        if not self.api_key or not self.api_key.strip():
            raise ValueError(
                "NVIDIA API Key is missing. Please configure NVIDIA_API_KEY."
            )

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        }

        # Build standard ChatCompletions message payload
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ]

        # Phase 3 settings: conservative output-token limit (512), low temperature (0.1), thinking disabled
        data = {
            "model": self.model,
            "messages": messages,
            "response_format": {"type": "json_object"},
            "temperature": 0.1,
            "max_tokens": 512,
            "chat_template_kwargs": {"enable_thinking": False},
        }

        req_payload = json.dumps(data).encode("utf-8")
        req = urllib.request.Request(
            self.endpoint, data=req_payload, headers=headers, method="POST"
        )

        try:
            # 90 seconds timeout
            with urllib.request.urlopen(req, timeout=90) as response:
                resp_bytes = response.read()
                resp_data = json.loads(resp_bytes.decode("utf-8"))

                # Extract chat completion choice
                choices = resp_data.get("choices")
                if not choices:
                    raise IOError("Invalid response from NVIDIA NIM: 'choices' field missing.")
                
                content = choices[0].get("message", {}).get("content")
                if content is None:
                    raise IOError("Invalid response from NVIDIA NIM: message content is null.")

                return content

        except urllib.error.HTTPError as he:
            # Propagate rate-limits, auth failure error details explicitly
            details = ""
            try:
                details = he.read().decode("utf-8")
            except Exception:
                pass
            
            status_code = he.code
            if status_code == 429:
                raise IOError(f"NVIDIA API Rate Limit Exceeded (429). Details: {details}")
            elif status_code == 401:
                raise IOError(f"NVIDIA API Unauthorized (401). Check NVIDIA_API_KEY. Details: {details}")
            else:
                raise IOError(
                    f"NVIDIA API HTTP Error {status_code}: {he.reason}. Details: {details}"
                )
        except urllib.error.URLError as ue:
            raise IOError(f"NVIDIA API Network Error: {str(ue)}")
        except TimeoutError:
            raise IOError("NVIDIA API request timed out (fail closed).")
        except Exception as ex:
            raise IOError(f"Unexpected NVIDIA API Error: {str(ex)}")



class OpenRouterProvider(LLMProvider):
    """
    Replaceable OpenRouter API provider using standard library urllib.
    No external request or OpenAI SDK dependencies are required.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        # Reload env variables in case of updates
        load_env()
        self.api_key = api_key if api_key is not None else os.environ.get("OPENROUTER_API_KEY")
        self.model = model if model is not None else (os.environ.get("OPENROUTER_MODEL") or "google/gemma-4-26b-a4b-it:free")
        
        raw_base = (
            base_url
            or os.environ.get("OPENROUTER_API_URL")
            or "https://openrouter.ai/api/v1"
        )
        base_stripped = raw_base.rstrip("/")
        if not base_stripped.endswith("/chat/completions"):
            self.endpoint = base_stripped + "/chat/completions"
        else:
            self.endpoint = base_stripped

    def generate_structured_response(self, prompt: str, system_prompt: str) -> str:
        # Check for empty API key
        if not self.api_key or not self.api_key.strip():
            raise ValueError(
                "OpenRouter API Key is missing. Please configure OPENROUTER_API_KEY."
            )

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        }

        # Build standard ChatCompletions message payload
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ]

        # OpenRouter requirements: compact structured JSON, low temp, max_tokens <= 512
        data = {
            "model": self.model,
            "messages": messages,
            "response_format": {"type": "json_object"},
            "temperature": 0.1,
            "max_tokens": 512,
        }

        req_payload = json.dumps(data).encode("utf-8")
        req = urllib.request.Request(
            self.endpoint, data=req_payload, headers=headers, method="POST"
        )

        try:
            # 60 seconds fail-closed timeout
            with urllib.request.urlopen(req, timeout=60) as response:
                resp_bytes = response.read()
                resp_data = json.loads(resp_bytes.decode("utf-8"))

                # Standard OpenAI structure matching
                choices = resp_data.get("choices")
                if not choices:
                    raise IOError("Invalid response from OpenRouter: 'choices' field missing.")
                
                content = choices[0].get("message", {}).get("content")
                if content is None:
                    raise IOError("Invalid response from OpenRouter: message content is null.")

                return content

        except urllib.error.HTTPError as he:
            details = ""
            try:
                details = he.read().decode("utf-8")
            except Exception:
                pass
            
            status_code = he.code
            if status_code == 429:
                raise IOError(f"OpenRouter API Rate Limit Exceeded (429). Details: {details}")
            elif status_code == 401:
                raise IOError(f"OpenRouter API Unauthorized (401). Check OPENROUTER_API_KEY. Details: {details}")
            else:
                raise IOError(
                    f"OpenRouter API HTTP Error {status_code}: {he.reason}. Details: {details}"
                )
        except urllib.error.URLError as ue:
            raise IOError(f"OpenRouter API Network Error: {str(ue)}")
        except TimeoutError:
            raise IOError("OpenRouter API request timed out (fail closed).")
        except Exception as ex:
            raise IOError(f"Unexpected OpenRouter API Error: {str(ex)}")


class MockLLMProvider(LLMProvider):
    """
    Mock LLM provider used to simulate model behavior inside testing suites.
    """

    def __init__(self, response_generator=None):
        self.response_generator = response_generator
        self.last_prompt = None
        self.last_system_prompt = None
        self.call_count = 0

    def generate_structured_response(self, prompt: str, system_prompt: str) -> str:
        self.call_count += 1
        self.last_prompt = prompt
        self.last_system_prompt = system_prompt
        if self.response_generator:
            return self.response_generator(prompt, system_prompt)
        # Default empty JSON structure
        return json.dumps(
            {
                "extracted_facts": [],
                "criterion_interpretations": [],
                "overall_reasoning_summary": "Mock empty response",
            }
        )


class GeminiProvider(LLMProvider):
    """
    urllib-based Gemini Provider using standard library.
    """
    def __init__(self, api_key=None, model=None):
        load_env()
        self.api_key = api_key if api_key is not None else os.environ.get("GOOGLE_API_KEY")
        self.model = model if model is not None else (os.environ.get("GOOGLE_MODEL") or "gemini-3.1-flash-lite")

    def generate_structured_response(self, prompt: str, system_prompt: str) -> str:
        if not self.api_key or not self.api_key.strip():
            raise ValueError("Google Gemini API Key is missing. Please configure GOOGLE_API_KEY.")

        endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key.strip()}"
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

        # Format payload for Google Gemini REST API
        data = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": prompt
                        }
                    ]
                }
            ],
            "systemInstruction": {
                "parts": [
                    {
                        "text": system_prompt
                    }
                ]
            },
            "generationConfig": {
                "responseMimeType": "application/json",
                "temperature": 0.1
            }
        }

        req_payload = json.dumps(data).encode("utf-8")
        req = urllib.request.Request(
            endpoint, data=req_payload, headers=headers, method="POST"
        )

        try:
            with urllib.request.urlopen(req, timeout=60) as response:
                resp_bytes = response.read()
                resp_data = json.loads(resp_bytes.decode("utf-8"))
                
                candidates = resp_data.get("candidates")
                if not candidates:
                    raise IOError("Invalid response from Gemini: 'candidates' field missing.")
                
                parts = candidates[0].get("content", {}).get("parts")
                if not parts:
                    raise IOError("Invalid response from Gemini: 'parts' field missing.")
                    
                content = parts[0].get("text")
                if content is None:
                    raise IOError("Invalid response from Gemini: content text is null.")
                return content
        except urllib.error.HTTPError as he:
            details = ""
            try:
                details = he.read().decode("utf-8")
            except Exception:
                pass
            status_code = he.code
            raise IOError(f"Gemini API HTTP Error {status_code}: {he.reason}. Details: {details}")
        except Exception as ex:
            raise IOError(f"Gemini API Error: {str(ex)}")
