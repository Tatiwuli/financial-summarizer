from pydantic import BaseModel


"""
LLM Client Abstraction for Earnings Call Analyzer
Implements a provider-agnostic interface to communicate with different LLM APIs.
"""

import os
from abc import ABC, abstractmethod
from dotenv import load_dotenv
from typing import Optional

import google.generativeai as genai
from google.generativeai import types
from openai import OpenAI


load_dotenv()


class LLMResponse(BaseModel):
    text: str
    model: str
    input_tokens: int
    output_tokens: int
    finish_reason: Optional[str] = None


class BaseLLMClient(ABC):
    """Abstract Base Class defining the interface for all LLM clients."""

    def __init__(self, model: str):
        self.model = model

    @abstractmethod
    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        max_output_tokens: int
    ) -> LLMResponse:
        """Generates a response from the LLM."""
        pass

# --- 3. Implementações Específicas para Cada Provedor ---


class GeminiClient(BaseLLMClient):
    """LLM Client for Google's Gemini models."""

    def __init__(self, model: str):
        super().__init__(model)
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError(
                "GEMINI_API_KEY not found in environment variables.")

        genai.configure(api_key=api_key)
        self.client = genai.GenerativeModel(model_name=self.model)

    def generate(self, system_prompt, user_prompt, max_output_tokens) -> LLMResponse:

        try:
            response = self.client.generate_content(
                contents=[user_prompt],
                generation_config=genai.GenerationConfig(
                    temperature=0.0,  # Gemini has, GPT not
                    max_output_tokens=max_output_tokens,
                ),
                system_instruction=system_prompt
            )

            output_text = response.text
            finish_reason = response.candidates[0].finish_reason.name if response.candidates else "UNKNOWN"

            if not output_text:  # Tratamento de resposta vazia
                raise LLMClientError(
                    f"Empty response from Gemini. Finish Reason: {finish_reason}")

            return LLMResponse(
                text=output_text,
                model=self.model,
                input_tokens=response.usage_metadata.prompt_token_count,
                output_tokens=response.usage_metadata.candidates_token_count,
                finish_reason=finish_reason,
            )
        except Exception as e:
            raise LLMClientError(f"Gemini API error: {e}")


class OpenAIClient(BaseLLMClient):
    """LLM Client for OpenAI's GPT models."""

    def __init__(self, model: str):
        super().__init__(model)

        api_key = os.getenv("OPENAI_API_KEY")
        self.client = OpenAI(api_key=api_key)

    def generate(self, system_prompt, user_prompt, max_output_tokens) -> LLMResponse:
        try:

            response = self.client.responses.create(
                model=self.model,
                instructions=system_prompt,
                input=user_prompt,

                max_output_tokens=max_output_tokens
            )

            output_text = ""
            try:
                output_items = getattr(response, "output", None) or []
                for item in output_items:
                    parts = getattr(item, "content", None) or []
                    for part in parts:
                        if hasattr(part, "text") and part.text:
                            output_text += part.text
            except Exception:
                # Best-effort fallback to string
                output_text = str(getattr(response, "output", ""))

            print("#####################OUTPUT###############", output_text)

            # Usage (may be missing depending on model/tooling)
            usage = getattr(response, "usage", None)
            in_tok = getattr(usage, "input_tokens", None) if usage else None
            out_tok = getattr(usage, "output_tokens", None) if usage else None

            # Finish / status
            status = getattr(response, "status", None) or "unknown"

            if not output_text:
                raise LLMClientError(
                    f"Empty output from Responses API (status={status}). Raw: {response}"
                )

            print(f"[OpenAI] completed model={self.model} status={status} ")
            print(f"output_chars={len(output_text)}")

            return LLMResponse(
                text=output_text,
                model=self.model,
                input_tokens=in_tok or 0,
                output_tokens=out_tok or 0,
                finish_reason=status,
            )

        except Exception as e:

            print(f"[OpenAI] API error: {e}")
            raise LLMClientError(f"OpenAI API error: {e}")


def get_llm_client(model: str) -> BaseLLMClient:
    """
    Factory function to get the appropriate LLM client based on the model name.
    """
    if model.startswith("gemini"):
        return GeminiClient(model=model)
    elif model.startswith("gpt"):
        return OpenAIClient(model=model)
    else:
        raise ValueError(f"Unsupported model provider for model: {model}")


class LLMClientError(Exception):
    """Custom exception for all LLM client errors."""
    pass
