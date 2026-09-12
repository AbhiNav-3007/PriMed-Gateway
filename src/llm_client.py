"""
PrivMed Gateway — Foundation LLM Client Integration Module
Supports local Ollama LLM integration, Google Gemini API integration, and a fallback mock adapter.
"""

import os
import json
import requests
import time
from typing import Dict, Any, Optional

class BaseLLMClient:
    """Base interface for downstream foundation LLM client."""
    def generate(self, prompt: str) -> str:
        raise NotImplementedError


class MockLLMClient(BaseLLMClient):
    """Mock LLM adapter for offline testing and zero-dependency demonstration."""
    
    def generate(self, prompt: str) -> str:
        # Extract de-identified clinical text body if system instructions are prepended
        if "De-identified Clinical Input:\n" in prompt:
            clinical_body = prompt.split("De-identified Clinical Input:\n")[-1].strip()
        else:
            clinical_body = prompt.strip()
            
        return f"[MOCK LLM RESPONSE]: Clinical summary generated for prompt:\n'{clinical_body}'\n\nRecommendation: Patient should continue current medication regimen and follow up in two weeks."


class OllamaLLMClient(BaseLLMClient):
    """Local Ollama LLM API Client."""

    def __init__(self, model_name: str = "llama3:latest", host: str = "http://localhost:11434"):
        self.model_name = model_name
        self.host = host.rstrip('/')
        self.endpoint = f"{self.host}/api/generate"

    def generate(self, prompt: str) -> str:
        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": False
        }
        try:
            response = requests.post(self.endpoint, json=payload, timeout=30)
            if response.status_code == 200:
                data = response.json()
                return data.get("response", "")
            else:
                print(f"[OllamaLLMClient] Error HTTP {response.status_code}: {response.text}")
                return MockLLMClient().generate(prompt)
        except Exception as e:
            print(f"[OllamaLLMClient] Ollama unavailable ({e}). Falling back to Mock adapter.")
            return MockLLMClient().generate(prompt)


class GeminiLLMClient(BaseLLMClient):
    """Google Gemini API Client Integration."""

    def __init__(self, api_key: Optional[str] = None, model_name: str = "gemini-3.6-flash"):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY", "")
        self.model_name = model_name
        self.endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_name}:generateContent?key={self.api_key}"

    def generate(self, prompt: str) -> str:
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is not set. Add it to your .env file.")

        payload = {
            "contents": [{
                "parts": [{"text": prompt}]
            }]
        }
        
        max_retries = 3
        for attempt in range(1, max_retries + 1):
            try:
                response = requests.post(self.endpoint, json=payload, timeout=60)
                if response.status_code == 200:
                    data = response.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        if parts:
                            return parts[0].get("text", "")
                    raise RuntimeError(f"Gemini returned empty response: {data}")
                elif response.status_code in [429, 500, 502, 503, 504] and attempt < max_retries:
                    time.sleep(2 * attempt)
                    continue
                else:
                    raise RuntimeError(f"Gemini API error {response.status_code}: {response.text}")
            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
                if attempt < max_retries:
                    time.sleep(2 * attempt)
                    continue
                raise RuntimeError(f"Gemini API network timeout after {max_retries} attempts ({e}). Please try again.")


def get_llm_client(provider: str = "mock", use_mock: bool = True, model_name: str = "llama3:latest", api_key: Optional[str] = None) -> BaseLLMClient:
    """
    Factory helper to obtain configured LLM client instance.
    Supports provider string ('mock', 'ollama', 'gemini') and legacy use_mock boolean.
    """
    if not use_mock and provider == "mock":
        provider = "ollama"

    provider_lower = provider.lower()
    if provider_lower == "ollama":
        return OllamaLLMClient(model_name=model_name)
    elif provider_lower == "gemini":
        return GeminiLLMClient(api_key=api_key)
    else:
        return MockLLMClient()
