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

    def generate(self, system_prompt, user_prompt, max_output_tokens, **kwargs) -> LLMResponse:

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

    def generate(self, system_prompt: str, user_prompt: str, max_output_tokens: int,
                 effort_level: Optional[str] = "medium",
                 text_format: Optional[Type[BaseModel]] = None) -> LLMResponse:

        base = {
            "model": self.model,
            "instructions": system_prompt,
            "input": user_prompt,
            "max_output_tokens": max_output_tokens,

        }
        if effort_level and self.model == "gpt-5":
            base["reasoning"] = {"effort": effort_level}

        try:
            start_time = time.time()

            # Use raw responses to access headers (rate limit info)
            if text_format is not None:
                raw_api_resp = self.client.responses.with_raw_response.parse(
                    **base,
                    text_format=text_format,
                )
                response = raw_api_resp.parse()
                parsed_resp = getattr(response, "output_parsed", None)
                text_output = parsed_resp.json() if parsed_resp is not None else ""
            else:
                raw_api_resp = self.client.responses.with_raw_response.create(
                    **base)
                response = raw_api_resp.parse()
                text_output = getattr(response, "output_text", None)

            # Status available on parsed SDK object
            status = getattr(response, "status", None) or "unknown"

            if text_output is None:
                print(
                    "output_text attribute is not provided by the SDK. Aggregating the output text manually")
                # fallback
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

        # Usage (may be missing depending on model/tooling)
        usage = getattr(response, "usage", None)
        in_tok = getattr(usage, "input_tokens", None) if usage else None
        out_tok = getattr(usage, "output_tokens", None) if usage else None
        reasoning_tok = getattr(
            usage, "reasoning_tokens", None) if usage else None

        # Duration
        try:
            duration_seconds = max(0.0, time.time() - start_time)
        except Exception:
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



prompt = """
Read the user’s structured request and transform it into a complete prompt that another LLM will use. 
Your task is to synthesize the user’s requirements into a clear, detailed prompt that will guide the LLM 
to generate relevant, accurate, and well-structured summaries of corporate financial documents. 
You should strictly follow the instructions in the recipe below. 

# USER REQUEST
The user will provide a structured request in the following format:

    [ Summary Goal ] 
    [ Information Source (e.g., earnings call transcript, conference) ] 
    [ Key Information Needs ] 
    [ Edge Cases ] 
    [ Non-Negotiable Data and Business Requirements ]
    [ Output Structure ]


# RECIPE FOR WRITING A PROMPT

## TASK GOAL
**Purpose:** Clearly and objectively define the TASK GOAL for the LLM.  
This section must include the **Summary Goal** and the **Information Source**.  
It should explain what the LLM should strive for and the source(s) it will analyze.  

_Derived from: [Summary Goal] + [Information Source]_  

---

## FUNDAMENTAL RULES
**Purpose:** Provide a clear and specific set of rules that the LLM must follow when conducting the task.  
This section should reflect **mandatory conditions** to ensure accuracy and compliance.  

_Derived from: [Non-Negotiable Data and Business Requirements] + [Edge Cases]_  

---

## RELEVANT INFORMATION
**Purpose:** List what information is considered **relevant** and must be prioritized from the transcript/source.  
This ensures the summary is **focused** and aligned with user intent.  

_Derived from: [Summary Goal] + [Key Information Needs]_  

---

## INSTRUCTIONS
**Purpose:** Break down the TASK GOAL into clear sub-problems.  
Provide a **step-by-step ordered list** of how the LLM should process the input material to achieve the TASK GOAL, 
while respecting the RELEVANT INFORMATION and FUNDAMENTAL RULES.  

- If **Edge Cases** exist, map them explicitly to the relevant step and provide a clear handling instruction.  

---

## OUTPUT STRUCTURE
**Purpose:** Define the structure that the LLM must use when delivering the final summary.  
The format must be **logical, markdown-formatted, and clean** for easy transfer into Google Docs.  

The structure must follow the OUTPUT STRUCTURE  and ensure readability, clarity, and professional presentation.  

-----------------------
# Your Output Structure: 
It should be a JSON object with two main components: 1) a prompt_generation_reasoning section that explains your reasoning behind generating the prompt, and 2) a prompt section that includes the prompt that will be used to generate the summary. 

```json
{OUTPUT_STRUCTURE}
```
"""

user_prompt = """

#User request
    
    [ What’s the summary goal  ] : Write a short summary of the Q&A section of an earning call transcript. From the Q&A summary,  I want to undestand :
    - Outlook and Guidance of Revenue and Margin (include other if mentioned in the Q&A)
    - The quarter's main financial results and KPIs
    -  What the analysts are most interested in and the key higlights of the executive's answers. 
   

    [ What they want to know from the summary ] : I want to know what are the main topics discussed in the Q&A section , including all the analysts' questions and any reference to investors ,  and the corresponding answers , including, but not limited to, key financial metrics and KPIs, guidance and outlook, events in company's strategy or management, and any relevant sentiment from the analyst and executive. 

    
    [ What’s the Information Source ( e.g. earing call transcript, conference)]
    -Q &A section of an Earning call transcript ,
    
    
    [ Edge cases ] 
    - LLM can fabricate metric or information even if transcript is empty
    - LLM include all of the information without prioritizing the most relevant topics. 
    - LLM missing some of the analysts or questions from a mentioned analyst. 
    
    [ Non-negotiable data requirements and business requirements]
    - Short 1-2 page summary focusing on the most relevant topics. 
    - Single source only: Use only the provided transcript between <START TRANSCRIPT> and <END TRANSCRIPT>. If empty, answer "No transcript provided."
    - Include ALL  the analysts' questions and corresponding answers. 
    - NEVER FABRICATE any metric, insight. 

    [OUTPUT STRUCTURE]

    Title of the Earning Call 

    Main Guidance and Outlook 



    Analyst name and role: Question 
    Answer 

    ( repeat for all questions and answers )
    

"""

output_structure = {
        "prompt_generation_reasoning": "[Explain your reasoning behind generating this prompt ]",
        "prompt": 
        {
            "task_goal": "[Explain the task goal in detail]",
            "fundamental_rules": "[Explain the fundamental rules in detail]",
            "relevant_information": "[Explain the relevant information in detail]",
            "instructions": "[Explain the instructions in detail]",
            "output_structure": "[Explain the output structure in detail]"
        }
}
    
# llm = get_llm_client(model="gpt-5")
# prompt = prompt.format(OUTPUT_STRUCTURE=output_structure)


# response = llm.generate(system_prompt=prompt, user_prompt=user_prompt, max_output_tokens=40000)

# print(response)




