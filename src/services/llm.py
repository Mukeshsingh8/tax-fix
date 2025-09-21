# src/services/llm.py
"""LLM service for Groq and Gemini integration (streaming + robust JSON)."""

from __future__ import annotations

import asyncio
import json
import re
from typing import Dict, List, Optional, Any, AsyncGenerator, Iterable, Tuple, Union, Callable

from langchain.schema import HumanMessage, SystemMessage, AIMessage, BaseMessage
from langchain.callbacks.base import BaseCallbackHandler
from langchain_groq import ChatGroq
from langchain_google_genai import ChatGoogleGenerativeAI

from .base_service import BaseService, LLMMixin



# Callback (kept for compatibility)
class StreamingCallbackHandler(BaseCallbackHandler):
    """Callback handler for streaming responses (token capture)."""

    def __init__(self):
        self.tokens: List[str] = []
        self.finished: bool = False

    def on_llm_new_token(self, token: str, **kwargs) -> None:
        self.tokens.append(token)

    def on_llm_end(self, response, **kwargs) -> None:
        self.finished = True

    def get_tokens(self) -> List[str]:
        return self.tokens

    def is_finished(self) -> bool:
        return self.finished



# LLM Service
class LLMService(BaseService, LLMMixin):
    """
    Unified LLM service with:
    - Groq + Gemini backends
    - Non-streaming and streaming completions
    - Robust JSON extraction
    - Timeouts, retries, and fallback
    """

    def __init__(self):
        super().__init__("LLMService")
        self.groq_client: Optional[ChatGroq] = None
        self.gemini_client: Optional[ChatGoogleGenerativeAI] = None
        self.initialize_clients()

    # client bootstrap
    def initialize_clients(self) -> None:
        self.log_operation_start("initialize_clients")
        try:
            # Validate required settings first
            if not self.settings.groq_api_key and not self.settings.google_api_key:
                raise ValueError("At least one LLM API key (Groq or Google) is required")

            # Groq
            if self.settings.groq_api_key:
                self.groq_client = ChatGroq(
                    groq_api_key=self.settings.groq_api_key,
                    model_name=self.settings.groq_model,
                    temperature=self.settings.temperature,
                    max_tokens=self.settings.max_tokens,
                )
                self.logger.info("Groq client initialized")
            else:
                self.logger.warning("GROQ_API_KEY not provided. Groq client not initialized.")

            # Gemini (optional)
            if self.settings.google_api_key:
                self.gemini_client = ChatGoogleGenerativeAI(
                    google_api_key=self.settings.google_api_key,
                    model=self.settings.google_model,
                    temperature=self.settings.temperature,
                    max_output_tokens=self.settings.max_tokens,
                )
                self.logger.info("Gemini client initialized")
            else:
                self.logger.warning("GOOGLE_API_KEY not provided. Gemini client not initialized.")

            self.log_operation_success("initialize_clients", f"groq={self.groq_client is not None}, gemini={self.gemini_client is not None}")
        except Exception as e:
            self.log_operation_error("initialize_clients", e)
            raise

    # utilities
    @staticmethod
    def to_lc_messages(
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None
    ) -> List[BaseMessage]:
        lc_msgs: List[BaseMessage] = []
        if system_prompt:
            lc_msgs.append(SystemMessage(content=system_prompt))
        for m in messages:
            role = m.get("role")
            content = m.get("content", "")
            if role == "user":
                lc_msgs.append(HumanMessage(content=content))
            elif role == "assistant":
                lc_msgs.append(AIMessage(content=content))
            elif role == "system":
                lc_msgs.append(SystemMessage(content=content))
            else:
                # Default to user for unknown role to avoid silent drops
                lc_msgs.append(HumanMessage(content=content))
        return lc_msgs

    def pick_client(self, provider: str):
        """provider in {'groq','gemini'}"""
        if provider == "groq":
            return self.groq_client
        if provider == "gemini":
            return self.gemini_client
        raise ValueError(f"Unknown provider: {provider}")

    @staticmethod
    def strip_code_fences(text: str) -> str:
        """Remove ```json/``` fences if present and trim."""
        text = text.strip()
        text = re.sub(r"^\s*```json\s*|\s*```\s*$", "", text, flags=re.I | re.M)
        text = re.sub(r"^\s*```\s*|\s*```\s*$", "", text, flags=re.I | re.M)
        return text.strip()

    @staticmethod
    def extract_first_json(text: str) -> str:
        """Extract the first JSON object from text; raises if not found."""
        match = re.search(r"\{.*\}", text, re.S)
        if not match:
            raise ValueError("No JSON object found in LLM output.")
        return match.group(0)

    async def with_timeout(self, coro, timeout_s: Optional[float]):
        if timeout_s is None or timeout_s <= 0:
            return await coro
        return await asyncio.wait_for(coro, timeout=timeout_s)

    async def try_providers_in_order(
        self,
        fn: Callable[[Any], Any],
        providers: Iterable[str]
    ):
        """Try a function across providers in order; return first success."""
        last_err = None
        for provider in providers:
            try:
                return await fn(provider)
            except Exception as e:
                last_err = e
                self.logger.warning(f"Provider {provider} failed: {e}")
        if last_err:
            raise last_err
        raise RuntimeError("No provider available")

    # Core API
    async def generate_response(
        self,
        messages: List[Dict[str, str]],
        model: str = "groq",            # keep param name for compatibility
        stream: bool = False,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        timeout_s: Optional[float] = None,
        retries: int = 1,               # total attempts per provider
        fallback: bool = True,          # try the other provider if available
    ) -> Union[str, AsyncGenerator[str, None]]:
        """
        Non-streaming: returns a string.
        Streaming: returns an async generator yielding token strings.

        NOTE: `model` parameter is treated as a provider selector {"groq","gemini"}.
        """
        provider = "groq" if model == "groq" else "gemini"
        lc_msgs = self.to_lc_messages(messages, system_prompt)

        async def run_once(pvdr: str) -> str:
            client = self.pick_client(pvdr)
            if not client:
                raise ValueError(f"Client not available for provider: {pvdr}")

            # Apply per-call params if provided (LangChain chat models accept these kwargs)
            invoke_kwargs: Dict[str, Any] = {}
            if temperature is not None:
                invoke_kwargs["temperature"] = temperature
            if max_tokens is not None:
                # groq: max_tokens, gemini: max_output_tokens – LangChain normalizes this, but keep safe:
                if pvdr == "groq":
                    invoke_kwargs["max_tokens"] = max_tokens
                else:
                    invoke_kwargs["max_output_tokens"] = max_tokens

            resp = await self.with_timeout(client.ainvoke(lc_msgs, **invoke_kwargs), timeout_s)
            return resp.content

        async def run_stream(pvdr: str) -> AsyncGenerator[str, None]:
            client = self.pick_client(pvdr)
            if not client:
                raise ValueError(f"Client not available for provider: {pvdr}")

            # LangChain chat models support astream(messages)
            async def gen():
                try:
                    async for chunk in client.astream(lc_msgs):
                        # Some providers yield AIMessage-like chunks with .content
                        if hasattr(chunk, "content") and chunk.content:
                            yield chunk.content
                except Exception as e:
                    self.logger.error(f"Error streaming from {pvdr}: {e}")
                    # surface error as a stream token (optional)
                    yield f"\n[stream error: {pvdr}: {e}]\n"
            return gen()

        # Streaming path: return generator, but keep retries/fallback simple (first available)
        if stream:
            try_order = [provider]
            if fallback and (provider == "groq") and self.gemini_client:
                try_order.append("gemini")
            if fallback and (provider == "gemini") and self.groq_client:
                try_order.append("groq")

            # Return the first available provider's stream
            for pvdr in try_order:
                client_ok = self.pick_client(pvdr) is not None
                if client_ok:
                    return await run_stream(pvdr)
            # If none available:
            async def err_stream():
                yield "[stream error: no provider available]"
            return err_stream()

        # Non-streaming path with retries + fallback
        async def run_with_retries(pvdr: str) -> str:
            attempt = 0
            while True:
                attempt += 1
                try:
                    return await run_once(pvdr)
                except Exception as e:
                    if attempt > max(1, retries):
                        raise
                    backoff = min(2 ** (attempt - 1), 4)
                    self.logger.warning(f"{pvdr} attempt {attempt} failed: {e}; retrying in {backoff}s")
                    await asyncio.sleep(backoff)

        try_order = [provider]
        if fallback and (provider == "groq") and self.gemini_client:
            try_order.append("gemini")
        if fallback and (provider == "gemini") and self.groq_client:
            try_order.append("groq")

        return await self.try_providers_in_order(run_with_retries, try_order)

    # Convenience: strict JSON completion with parsing and guardrails
    async def generate_json(
        self,
        messages: List[Dict[str, str]],
        model: str = "groq",
        system_prompt: Optional[str] = None,
        timeout_s: Optional[float] = 20.0,
        retries: int = 1,
        fallback: bool = True,
    ) -> Dict[str, Any]:
        """
        Ask the model for JSON, then sanitize and parse it.
        Raises if parsing fails after retries/fallback.
        """
        json_guard = "Return strictly valid JSON. Do not include any commentary or code fences."
        sys = f"{json_guard}" if not system_prompt else f"{system_prompt}\n\n{json_guard}"

        text = await self.generate_response(
            messages=messages,
            model=model,
            stream=False,
            system_prompt=sys,
            timeout_s=timeout_s,
            retries=retries,
            fallback=fallback,
        )
        cleaned = self.strip_code_fences(text)
        try:
            # Try direct parse first (fast path)
            return json.loads(cleaned)
        except json.JSONDecodeError:
            # Extract the first JSON object if extra text leaked
            try:
                obj = self.extract_first_json(cleaned)
                return json.loads(obj)
            except Exception as e:
                self.logger.error(f"Failed to parse JSON from model output. Raw:\n{text}")
                raise ValueError(f"Invalid JSON from LLM: {e}") from e

    # Streaming (explicit helper kept for compatibility with callers)
    async def stream_response(
        self,
        client,                   # kept for backwards compat
        messages: List[BaseMessage],
    ) -> AsyncGenerator[str, None]:
        """(Deprecated internal) Stream response from a given client."""
        try:
            async for chunk in client.astream(messages):
                if hasattr(chunk, "content") and chunk.content:
                    yield chunk.content
        except Exception as e:
            self.logger.error(f"Error streaming response: {e}")
            yield f"[stream error: {e}]"
    
    # Extra helpers (kept and improved)
    async def generate_with_callback(
        self,
        messages: List[Dict[str, str]],
        model: str = "groq",
        system_prompt: Optional[str] = None,
        timeout_s: Optional[float] = 20.0,
    ) -> Tuple[str, List[str]]:
        """
        Non-streaming completion with token-capture callback (Groq/Gemini).
        Returns (content, tokens_seen).
        """
        provider = "groq" if model == "groq" else "gemini"
        lc_msgs = self.to_lc_messages(messages, system_prompt)
        client = self.pick_client(provider)
        if not client:
            raise ValueError(f"Client not available for provider: {provider}")

        callback_handler = StreamingCallbackHandler()
        resp = await self.with_timeout(
            client.ainvoke(lc_msgs, callbacks=[callback_handler]),
            timeout_s,
        )
        return resp.content, callback_handler.get_tokens()

    async def analyze_text(
        self,
        text: str,
        analysis_type: str = "general",
        model: str = "gemini",
    ) -> Dict[str, Any]:
        system_prompts = {
            "tax_related": "You are a tax expert. Analyze the following text for tax-related information, deductions, and advice.",
            "sentiment": "You are a sentiment analysis expert. Analyze the sentiment of the following text.",
            "intent": "You are an intent recognition expert. Identify the user's intent from the following text.",
            "general": "You are a helpful assistant. Analyze the following text and provide insights.",
        }
        system_prompt = system_prompts.get(analysis_type, system_prompts["general"])

        messages = [{"role": "user", "content": text}]
        try:
            response = await self.generate_response(
                messages=messages,
                model=model,
                system_prompt=system_prompt,
            )
            return {
                "analysis_type": analysis_type,
                "text": text,
                "analysis": response,
                "model_used": model,
            }
        except Exception as e:
            self.logger.error(f"Error analyzing text: {e}")
            return {
                "analysis_type": analysis_type,
                "text": text,
                "analysis": f"Error: {str(e)}",
                "model_used": model,
            }

    async def extract_entities(
        self,
        text: str,
        entity_types: Optional[List[str]] = None,
        model: str = "gemini",
    ) -> Dict[str, Any]:
        if entity_types is None:
            entity_types = ["amounts", "dates", "tax_terms", "locations"]

        prompt = f"""
Extract the following entities from the text and return JSON with each entity type as a key and a list of strings as values.
If none found, return an empty list for that key.

entity_types: {', '.join(entity_types)}
text: {text}
"""
        try:
            data = await self.generate_json(
                messages=[{"role": "user", "content": prompt}],
                model=model,
                system_prompt="You are an expert at extracting structured information. Always return valid JSON.",
            )
            # Ensure all requested keys exist
            for key in entity_types:
                data.setdefault(key, [])
            return data
        except Exception as e:
            self.logger.error(f"Error extracting entities: {e}")
            return {"error": str(e)}

    async def generate_suggestions(
        self,
        context: Dict[str, Any],
        suggestion_type: str = "actions",
        model: str = "groq",
    ) -> List[Dict[str, Any]]:
        suggestion_prompts = {
            "actions": "Based on the context, suggest concrete next actions for the user.",
            "questions": "Based on the context, suggest clarifying questions to ask the user.",
            "deductions": "Based on the user's profile and context, suggest relevant German tax deductions.",
            "next_steps": "Given the conversation, suggest logical next steps.",
        }
        system_prompt = suggestion_prompts.get(suggestion_type, suggestion_prompts["actions"])

        messages = [{"role": "user", "content": f"Context: {json.dumps(context, ensure_ascii=False)}"}]
        try:
            text = await self.generate_response(messages=messages, model=model, system_prompt=system_prompt)
            # Heuristic line split (you may replace with JSON in the future)
            suggestions: List[Dict[str, Any]] = []
            for line in [ln.strip("-• ").strip() for ln in text.splitlines()]:
                if line:
                    suggestions.append({"text": line, "type": suggestion_type, "confidence": 0.8})
            return suggestions
        except Exception as e:
            self.logger.error(f"Error generating suggestions: {e}")
            return []

    async def validate_response(
        self,
        response: str,
        context: Dict[str, Any],
        model: str = "gemini",
    ) -> Dict[str, Any]:
        prompt = f"""
Validate the following response for accuracy, helpfulness, and appropriateness.

Return JSON:
{{
  "accuracy_score": 0-1,
  "helpfulness_score": 0-1,
  "appropriateness_score": 0-1,
  "issues": [string],
  "suggestions": [string]
}}

Response: {response}
Context: {json.dumps(context, ensure_ascii=False)}
"""
        try:
            data = await self.generate_json(
                messages=[{"role": "user", "content": prompt}],
                model=model,
                system_prompt="You are an expert validator. Always return valid JSON only.",
            )
            # Fill defaults
            data.setdefault("accuracy_score", 0.5)
            data.setdefault("helpfulness_score", 0.5)
            data.setdefault("appropriateness_score", 0.5)
            data.setdefault("issues", [])
            data.setdefault("suggestions", [])
            return data
        except Exception as e:
            self.logger.error(f"Error validating response: {e}")
            return {
                "accuracy_score": 0.0,
                "helpfulness_score": 0.0,
                "appropriateness_score": 0.0,
                "issues": [f"Validation error: {str(e)}"],
                "suggestions": ["Improve validation pipeline"],
            }
