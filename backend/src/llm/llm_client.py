from pydantic import BaseModel

import os
from abc import ABC, abstractmethod
from dotenv import load_dotenv
from typing import Optional, Type, Any
import time

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
    parsed: Optional[BaseModel] = None
    raw: Optional[Any] = None
    # Remaining tokens per minute from OpenAI rate-limit headers, when available
    remaining_tokens: Optional[int] = None
    # Reasoning tokens when available (e.g., gpt-5)
    reasoning_tokens: Optional[int] = None
    # Round-trip duration in seconds for the LLM API call
    duration_seconds: Optional[float] = None

    class Config:
        arbitrary_types_allowed = True


class BaseLLMClient(ABC):
    """Abstract Base Class defining the interface for all LLM clients."""

    def __init__(self, model: str):
        self.model = model

    @abstractmethod
    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        max_output_tokens: int,
        **kwargs  # specific parameters for each model
    ) -> LLMResponse:
        """Generates a response from the LLM."""
        pass


class OpenAIClient(BaseLLMClient):
    """LLM Client for OpenAI's GPT models."""

    def __init__(self, model: str):
        super().__init__(model)

        api_key = os.getenv("OPENAI_API_KEY")
        self.client = OpenAI(api_key=api_key)

    def generate(self, system_prompt: str, user_prompt: str, max_output_tokens: int,
                 effort_level: Optional[str] = "medium",
                 text_format: Optional[Type[BaseModel]] = None) -> LLMResponse:

        base = {
            "model": self.model,
            "instructions": system_prompt,
            "input": user_prompt,
            "max_output_tokens": max_output_tokens,

        }

        #Only gpt-5 support effort level for reasoning
        if effort_level and self.model == "gpt-5":
            base["reasoning"] = {"effort": effort_level}

        try:
            #Track output generation time
            start_time = time.time()

            # Use raw responses to access headers for rate limit info
            if text_format is not None:
                raw_api_resp = self.client.responses.with_raw_response.parse(
                    **base,
                    text_format=text_format,
                )
                response = raw_api_resp.parse()

                text_output = getattr(response, "output_text", "") or ""

                #get status before possible json parsing error 
                status = getattr(response, "status", None) or "unknown"

                print("OPEN AI Status: ", status)

                parsed_resp = getattr(response, "output_parsed", None)
                text_output = parsed_resp.json() if parsed_resp is not None else ""
            else:
                raw_api_resp = self.client.responses.with_raw_response.create(
                    **base)
                response = raw_api_resp.parse()
                text_output = getattr(response, "output_text", None)

          #  Fallback to manual text extraction
          
            if text_output is None:
                print(
                    "output_text attribute is not provided by the SDK. Aggregating the output text manually")
              #Concatenate the output text
                text_output = ""
                for item in getattr(response, "output", []) or []:
                    for part in getattr(item, "content", []) or []:
                        if getattr(part, "type", None) == "output_text" and getattr(part, "text", None):
                            text_output += part.text

            if not text_output and text_format is None:
                raise LLMClientError(
                    f"Empty output from Responses API (status={status}). Raw: {response}")

        except Exception as e:
            raise LLMClientError(f"OpenAI API error: {e}")

        # Usage information
        usage = getattr(response, "usage", None)
        in_tok = getattr(usage, "input_tokens", None) if usage else None
        out_tok = getattr(usage, "output_tokens", None) if usage else None
        reasoning_tok = getattr(
            usage, "reasoning_tokens", None) if usage else None

        # Calculate Duration
        duration_seconds = max(0.0, time.time() - start_time)
        if not duration_seconds:
            duration_seconds = None

        # Extract rate-limit remaining tokens from headers (if present)
        remaining_tokens: Optional[int] = None
        try:
            headers = getattr(raw_api_resp, "headers", None)
            if headers:
                # Headers may be case-insensitive; try both common casings
                val = headers.get(
                    "x-ratelimit-remaining-tokens") or headers.get("X-RateLimit-Remaining-Tokens")
                if val is not None:
                    remaining_tokens = int(str(val))
                else:
                    remaining_tokens = None
        except Exception:
            remaining_tokens = None

        return LLMResponse(
            text=text_output,
            model=self.model,
            input_tokens=in_tok or 0,
            output_tokens=out_tok or 0,
            finish_reason=status,
            parsed=parsed_resp if text_format is not None else None,
            raw=response,
            remaining_tokens=remaining_tokens,
            reasoning_tokens=reasoning_tok if reasoning_tok is not None else None,
            duration_seconds=duration_seconds,
        )


def get_llm_client(model: str) -> BaseLLMClient:
   
    if model.startswith("gpt"):
        return OpenAIClient(model=model)
    else:
        raise ValueError(f"Unsupported model provider for model: {model}")


class LLMClientError(Exception):
    """Custom exception for all LLM client errors."""
    pass


