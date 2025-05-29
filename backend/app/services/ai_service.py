# Placeholder for AI service integration logic 

import logging
import uuid
import json
import requests
from typing import Sequence, Protocol, runtime_checkable, Any, Dict, Type, List, Tuple, Optional
# Update Gemini import to new format
try:
    from google import genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    genai = None
import importlib
import traceback

from app.models import Character, Message, MessageSender, AIProviderConfig
from app.core.config import settings
from sqlmodel import Session
from openai import OpenAI, APITimeoutError, APIConnectionError, RateLimitError, APIStatusError
from anthropic import Anthropic, HUMAN_PROMPT, AI_PROMPT
import httpx
from app.crud.config import get_ai_provider_config, set_ai_provider_config as crud_set_ai_provider_config

logger = logging.getLogger(__name__)

# --- Provider Interface ---

@runtime_checkable
class AIProvider(Protocol):
    """Interface for AI model providers."""
    def __init__(self, api_key: str | None, api_base: str | None = None):
        ...

    def get_response(
        self, *, character: Character, history: Sequence[Message]
    ) -> str:
        """Generates a response based on character and history."""
        ...

    def _build_system_prompt(self, character: Character) -> str:
        prompt_parts = [
            f"You are {character.name}, a character with the following traits:",
            f"- Personality: {character.personality_traits}",
            f"- Writing Style: {character.writing_style}",
            f"- Background: {character.background}",
            f"- Knowledge Scope: {character.knowledge_scope}",
            f"- Quirks: {character.quirks}",
            f"- Emotional Range: {character.emotional_range}",
            f"- Scenario: {character.scenario}",
            f"- Language: {character.language}",
            "Please embody this character fully in your responses. Be engaging and stay in character."
        ]
        return "\n".join(filter(None, prompt_parts))

    def _format_history(self, history: Sequence[Message]) -> List[Dict[str, Any]]:
        """Format message history for Gemini API."""
        formatted_history = []
        for msg in history:
            role = "user" if msg.sender == MessageSender.USER else "model"
            formatted_history.append({"role": role, "parts": [msg.content]})
        return formatted_history

    def _truncate_history_if_needed(self, history: Sequence[Message], max_tokens: int = 30000) -> Sequence[Message]:
        """Truncate history to prevent token overflow while preserving recent context."""
        current_tokens = sum(len(msg.content) for msg in history) // 4
        if current_tokens > max_tokens:
            logger.warning(f"History ({current_tokens} tokens) exceeds max_tokens ({max_tokens}). Truncating.")
            num_to_keep = int(len(history) * 0.75)
            return history[-num_to_keep:]
        return history

# --- Provider Implementations ---

class GeminiProvider(AIProvider):
    """Google Gemini provider using the new API format."""
    def __init__(self, api_key: str | None, api_base: str | None = None):
        # AIProvider is a Protocol, so no super().__init__ needed
        # Assign api_key from parameter or fallback to settings
        self.api_key = api_key if api_key else settings.GEMINI_API_KEY
        self.api_base = api_base  # Not used for Gemini but kept for consistency
        
        if not GEMINI_AVAILABLE:
            raise ValueError("Google Gemini library is not available. Please install: pip install google-genai")
        
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is not configured.")
            
        # Create Gemini client using new API format
        self.client = genai.Client(api_key=self.api_key)
        # Use new model
        self.model_name = 'gemini-2.0-flash'

    def get_response(
        self, *, character: Character, history: Sequence[Message]
    ) -> str:
        system_prompt = self._build_system_prompt(character)
        
        # Truncate history if too long
        truncated_history = self._truncate_history_if_needed(history)

        logger.info(f"--- Gemini Request for {character.name} ---")
        logger.info(f"System Prompt length: {len(system_prompt)} chars")
        logger.info(f"History length: {len(truncated_history)} messages")

        try:
            # Build conversation contents
            conversation_parts = [system_prompt]
            
            # Add history
            for msg in truncated_history:
                role_prefix = "User:" if msg.sender == MessageSender.USER else "Assistant:"
                conversation_parts.append(f"{role_prefix} {msg.content}")
            
            # Join all parts into single content string
            contents = "\n\n".join(conversation_parts)
            
            # Generate response using new API format
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=contents
            )

            logger.info(f"--- Gemini Response for {character.name} received successfully ---")
            
            # Extract response text
            response_text = response.text if hasattr(response, 'text') and response.text else None
            return response_text.strip() if response_text else (character.fallback_response or f"*{character.name} seems momentarily distracted*")
            
        except Exception as e:
            logger.error(f"Error calling Gemini API for character {character.name}: {e}", exc_info=True)
            # Use character fallback response or generic fallback
            return character.fallback_response or f"*{character.name} seems momentarily distracted*"


class OpenAIProvider(AIProvider):
    """Direct OpenAI provider."""
    def __init__(self, api_key: str | None, api_base: str | None = None, model_name: str = "gpt-4o"):
        # AIProvider is a Protocol, so no super().__init__ needed
        # Assign parameters to instance variables
        self.api_key = api_key
        self.api_base = api_base or "https://api.openai.com/v1"  # Default to OpenAI API
        self.model_name = model_name

        # Check if API key is configured
        if not self.api_key:
            logger.warning(f"API_KEY for {self.__class__.__name__} (model: {model_name}) is not configured. Provider will not work.")
            raise ValueError(f"OPENAI_API_KEY (model: {model_name}) is not configured.")

        self.client_params = {"api_key": self.api_key, "base_url": self.api_base}
        self.client = OpenAI(**self.client_params)
        self.extra_headers = {}  # No special headers for direct OpenAI

    def _format_history_for_openai(self, history: Sequence[Message]) -> List[Dict[str, Any]]:
        """Format message history for OpenAI API (roles: user, assistant)."""
        formatted_history = []
        for msg in history:
            role = "assistant" if msg.sender == MessageSender.AI else "user"
            formatted_history.append({"role": role, "content": msg.content})
        return formatted_history

    def get_response(
        self, *, character: Character, history: Sequence[Message]
    ) -> str:
        if not self.api_key:
            logger.error(f"API key not configured for {self.__class__.__name__} using model {self.model_name}. Cannot make API call.")
            return f"(OOC: Configuration error - API key missing for {character.name})"

        system_prompt_content = self._build_system_prompt(character)
        truncated_history = self._truncate_history_if_needed(history, max_tokens=160000)
        formatted_openai_history = self._format_history_for_openai(truncated_history)

        messages = [
            {"role": "system", "content": system_prompt_content}
        ] + formatted_openai_history

        logger.debug(f"--- OpenAI Request for {character.name} (Model: {self.model_name}) ---")
        logger.debug(f"System Prompt: {system_prompt_content}")
        logger.debug(f"Formatted History (last 2): {formatted_openai_history[-2:] if len(formatted_openai_history) > 1 else formatted_openai_history}")

        try:
            completion = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=0.8, 
                max_tokens=1024,
                top_p=0.9,
                extra_headers=self.extra_headers if self.extra_headers else None
            )
            response_text = completion.choices[0].message.content
            logger.debug(f"--- OpenAI Response for {character.name} ---: {response_text[:100]}...")
            return response_text.strip() if response_text else f"(OOC: {character.name} received an empty response.)"
        except APITimeoutError as e:
            logger.error(f"OpenAI API timeout for {character.name} (Model: {self.model_name}): {e}")
            return f"(OOC: Sorry, my thoughts got lost in hyperspace... timed out!)"
        except APIConnectionError as e:
            logger.error(f"OpenAI API connection error for {character.name} (Model: {self.model_name}): {e}")
            return f"(OOC: Hmm, can't seem to connect to the ethereal plane of ideas right now.)"
        except RateLimitError as e:
            logger.error(f"OpenAI API rate limit exceeded for {character.name} (Model: {self.model_name}): {e}")
            return f"(OOC: Wooah, too many ideas flowing! I need a moment to catch my breath.)"
        except APIStatusError as e:
            logger.error(f"OpenAI API status error for {character.name} (Model: {self.model_name}). Status: {e.status_code}, Response: {e.response.text}")
            return f"(OOC: Uh oh, the universal translator seems to be on the fritz. Status: {e.status_code})"
        except Exception as e:
            logger.error(f"Generic error calling OpenAI API for {character.name} (Model: {self.model_name}): {e}", exc_info=True)
            return f"(OOC: My apologies, a cosmic ray seems to have hit my thinking circuits!)"


class BaseOpenRouterProvider(AIProvider):
    """Base OpenRouter provider that other OpenRouter model providers inherit from."""
    def __init__(self, api_key: str | None, model_name: str):
        # AIProvider is a Protocol, so no super().__init__ needed
        self.api_key = api_key
        self.api_base = "https://openrouter.ai/api/v1"
        self.model_name = model_name

        # Check if API key is configured
        if not self.api_key:
            logger.warning(f"OPENROUTER_API_KEY for {self.__class__.__name__} (model: {model_name}) is not configured. Provider will not work.")
            raise ValueError(f"OPENROUTER_API_KEY (model: {model_name}) is not configured.")

        self.client_params = {"api_key": self.api_key, "base_url": self.api_base}
        self.client = OpenAI(**self.client_params)

        # Prepare OpenRouter specific headers
        self.extra_headers = {
            "HTTP-Referer": getattr(settings, "FRONTEND_HOST", "https://imacall.app"),
            "X-Title": getattr(settings, "PROJECT_NAME", "ImaCall")
        }
        logger.info(f"OpenRouter headers configured for {self.__class__.__name__}: Referer='{self.extra_headers['HTTP-Referer']}', X-Title='{self.extra_headers['X-Title']}'")

    def _build_system_prompt(self, character: Character) -> str:
        """Build system prompt for the character."""
        prompt_parts = [
            f"You are {character.name}, a character with the following traits:",
            f"- Personality: {character.personality_traits}",
            f"- Writing Style: {character.writing_style}",
            f"- Background: {character.background}",
            f"- Knowledge Scope: {character.knowledge_scope}",
            f"- Quirks: {character.quirks}",
            f"- Emotional Range: {character.emotional_range}",
            f"- Scenario: {character.scenario}",
            f"- Language: {character.language}",
            "Please embody this character fully in your responses. Be engaging and stay in character."
        ]
        return "\n".join(filter(None, prompt_parts))

    def _truncate_history_if_needed(self, history: Sequence[Message], max_tokens: int = 30000) -> Sequence[Message]:
        """Truncate history to prevent token overflow while preserving recent context."""
        current_tokens = sum(len(msg.content) for msg in history) // 4
        if current_tokens > max_tokens:
            logger.warning(f"History ({current_tokens} tokens) exceeds max_tokens ({max_tokens}). Truncating.")
            num_to_keep = int(len(history) * 0.75)
            return history[-num_to_keep:]
        return history

    def _format_history_for_openai(self, history: Sequence[Message]) -> List[Dict[str, Any]]:
        """Format message history for OpenAI API (roles: user, assistant)."""
        formatted_history = []
        for msg in history:
            role = "assistant" if msg.sender == MessageSender.AI else "user"
            formatted_history.append({"role": role, "content": msg.content})
        return formatted_history

    def get_response(
        self, *, character: Character, history: Sequence[Message]
    ) -> str:
        try:
            if not self.api_key:
                logger.error(f"API key not configured for {self.__class__.__name__} using model {self.model_name}. Cannot make API call.")
                return character.fallback_response or f"(OOC: Configuration error - API key missing for {character.name})"

            system_prompt_content = self._build_system_prompt(character)
            truncated_history = self._truncate_history_if_needed(history, max_tokens=8000)  # Reduced from 160000
            formatted_openai_history = self._format_history_for_openai(truncated_history)

            messages = [
                {"role": "system", "content": system_prompt_content}
            ] + formatted_openai_history

            logger.info(f"--- OpenRouter Request for {character.name} (Model: {self.model_name}) ---")
            logger.info(f"System Prompt length: {len(system_prompt_content)} chars")
            logger.info(f"History messages: {len(formatted_openai_history)}")
            logger.info(f"Extra Headers for OpenRouter: {self.extra_headers}")
            
            # Log the actual request payload (truncated for readability)
            logger.info(f"Request payload preview:")
            logger.info(f"- Model: {self.model_name}")
            logger.info(f"- Messages count: {len(messages)}")
            logger.info(f"- Last user message: {messages[-1]['content'][:100] if messages else 'None'}...")
            logger.info(f"- Temperature: 0.8, Max tokens: 1024")

            completion = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=0.8, 
                max_tokens=1024,
                top_p=0.9,
                extra_headers=self.extra_headers
            )
            
            # Debug the response structure
            logger.info(f"OpenRouter API Response Debug:")
            logger.info(f"- Completion object type: {type(completion)}")
            logger.info(f"- Choices length: {len(completion.choices) if completion.choices else 'None'}")
            if completion.choices and len(completion.choices) > 0:
                logger.info(f"- First choice: {completion.choices[0]}")
                logger.info(f"- Message: {completion.choices[0].message}")
                logger.info(f"- Content: '{completion.choices[0].message.content}'")
                logger.info(f"- Content type: {type(completion.choices[0].message.content)}")
            
            response_text = completion.choices[0].message.content
            logger.info(f"--- OpenRouter Response for {character.name} received successfully ---")
            logger.info(f"Response text: '{response_text}' (length: {len(response_text) if response_text else 0})")
            return response_text.strip() if response_text else (character.fallback_response or f"(OOC: {character.name} received an empty response.)")

        except APITimeoutError as e:
            logger.error(f"OpenRouter API timeout for {character.name} (Model: {self.model_name}): {e}")
            return character.fallback_response or f"(OOC: Sorry, my thoughts got lost in hyperspace... timed out!)"
        except APIConnectionError as e:
            logger.error(f"OpenRouter API connection error for {character.name} (Model: {self.model_name}): {e}")
            return character.fallback_response or f"(OOC: Hmm, can't seem to connect to the ethereal plane of ideas right now.)"
        except RateLimitError as e:
            logger.error(f"OpenRouter API rate limit exceeded for {character.name} (Model: {self.model_name}): {e}")
            return character.fallback_response or f"(OOC: Wooah, too many ideas flowing! I need a moment to catch my breath.)"
        except APIStatusError as e:
            logger.error(f"OpenRouter API status error for {character.name} (Model: {self.model_name}). Status: {e.status_code}, Response: {e.response.text}")
            return character.fallback_response or f"(OOC: Uh oh, the universal translator seems to be on the fritz. Status: {e.status_code})"
        except Exception as e:
            logger.error(f"CRITICAL: Unexpected error calling OpenRouter API for {character.name} (Model: {self.model_name}): {e}", exc_info=True)
            return character.fallback_response or f"(OOC: My apologies, a cosmic ray seems to have hit my thinking circuits!)"


# Individual OpenRouter Model Providers
class DeepSeekR1Provider(BaseOpenRouterProvider):
    """DeepSeek R1 provider using OpenRouter."""
    def __init__(self, api_key: str | None, api_base: str | None = None):
        # Call BaseOpenRouterProvider init directly, no super() needed
        BaseOpenRouterProvider.__init__(self, api_key, "deepseek/deepseek-r1-0528-qwen3-8b:free")


class SarvamProvider(BaseOpenRouterProvider):
    """Sarvam M provider using OpenRouter."""
    def __init__(self, api_key: str | None, api_base: str | None = None):
        # Call BaseOpenRouterProvider init directly, no super() needed
        BaseOpenRouterProvider.__init__(self, api_key, "sarvamai/sarvam-m:free")


class DeepSeekChatProvider(BaseOpenRouterProvider):
    """DeepSeek Chat V3 provider using OpenRouter."""
    def __init__(self, api_key: str | None, api_base: str | None = None):
        # Call BaseOpenRouterProvider init directly, no super() needed
        BaseOpenRouterProvider.__init__(self, api_key, "deepseek/deepseek-chat-v3-0324:free")


class Qwen3Provider(BaseOpenRouterProvider):
    """Qwen 3 235B provider using OpenRouter."""
    def __init__(self, api_key: str | None, api_base: str | None = None):
        # Call BaseOpenRouterProvider init directly, no super() needed
        BaseOpenRouterProvider.__init__(self, api_key, "qwen/qwen3-235b-a22b:free")


class Gemma3Provider(BaseOpenRouterProvider):
    """Gemma 3 27B provider using OpenRouter."""
    def __init__(self, api_key: str | None, api_base: str | None = None):
        # Call BaseOpenRouterProvider init directly, no super() needed  
        BaseOpenRouterProvider.__init__(self, api_key, "google/gemma-3-27b-it:free")


class ClaudeProvider(AIProvider):
    """Placeholder for Anthropic Claude provider."""
    def __init__(self, api_key: str | None, api_base: str | None = None, model_name: str = "claude-3-haiku-20240307"):
        # AIProvider is a Protocol, so no super().__init__ needed
        # Assign parameters to instance variables
        self.api_key = api_key
        self.api_base = api_base  # Not used for Claude but kept for consistency
        self.model_name = model_name
        
        if not self.api_key:
             logger.warning("CLAUDE_API_KEY is not configured. ClaudeProvider will not work.")
        # Initialize Claude client here
        self.client = Anthropic(api_key=self.api_key)

    def get_response(
        self, *, character: Character, history: Sequence[Message]
    ) -> str:
        logger.warning("ClaudeProvider.get_response called but not implemented.")
        raise NotImplementedError("Claude provider is not yet implemented.")
        # Implementation would involve:
        # 1. Building a system prompt.
        # 2. Formatting history (roles: user, assistant).
        # 3. Calling the Anthropic Messages API.
        # return f"(OOC: Claude provider for {character.name} not implemented)"

class OldOpenRouterProvider(AIProvider):
    """DEPRECATED: Old OpenRouter provider using direct requests. Use OpenAIProvider with OpenRouter base URL instead."""
    def __init__(self, api_key: str | None, api_base: str | None = None):
        # AIProvider is a Protocol, so no super().__init__ needed
        # Assign parameters to instance variables
        self.api_key = api_key
        self.api_base = api_base  # Not used but kept for consistency
        
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY is not configured.")
            
        self.api_url = "https://openrouter.ai/api/v1/chat/completions"
        # Default to Qwen3 30B A3B (free)
        self.model = "qwen/qwen3-30b-a3b:free"
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "https://imacall.app",  # Replace with your actual site URL
            "X-Title": "ImaCall",  # Replace with your site name
        }

    def _format_history(self, history: Sequence[Message]) -> List[Dict[str, Any]]:
        # Format messages for the OpenRouter API (OpenAI-compatible format)
        formatted_history = []
        for msg in history:
            role = "assistant" if msg.sender == MessageSender.AI else "user"
            formatted_history.append({"role": role, "content": msg.content})
        return formatted_history

    def get_response(
        self, *, character: Character, history: Sequence[Message]
    ) -> str:
        system_prompt = self._build_system_prompt(character)
        formatted_history = self._format_history(history)
        
        # Add system message at the beginning
        messages = [{"role": "system", "content": system_prompt}] + formatted_history
        
        # Check for empty history or last user message
        last_user_message_content = next((msg.content for msg in reversed(history) if msg.sender == MessageSender.USER), None)
        if not last_user_message_content:
            # If no user message (e.g., first interaction after greeting), use greeting
            return character.greeting_message or f"Hi! I'm {character.name}."

        logger.debug(f"--- OpenRouter Request ---")
        logger.debug(f"System Prompt: {system_prompt}")
        logger.debug(f"Formatted History: {formatted_history}")
        
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.9,
            "max_tokens": 1024,
        }
        
        try:
            response = requests.post(
                self.api_url,
                headers=self.headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code != 200:
                logger.error(f"OpenRouter API error: {response.status_code} - {response.text}")
                return f"(OOC: Sorry, I encountered an error trying to respond as {character.name}. API returned status {response.status_code}.)"
            
            result = response.json()
            # Extract response using OpenAI-compatible format
            content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
            
            if not content:
                logger.error(f"OpenRouter API returned empty content: {result}")
                return f"(OOC: Sorry, I received an empty response when trying to respond as {character.name}.)"
            
            logger.debug(f"--- OpenRouter Response ---: {content}")
            return content.strip()
            
        except Exception as e:
            logger.error(f"Error calling OpenRouter API: {e}", exc_info=True)
            # Provide a generic fallback response
            return f"(OOC: Sorry, I encountered an error trying to respond as {character.name}.)"

class FPTAIProvider(AIProvider):
    """FPT AI Marketplace provider (using Llama-3.3-70B-Instruct)."""
    def __init__(self, api_key: str | None, api_base: str | None = None):
        # AIProvider is a Protocol, so no super().__init__ needed
        # Assign parameters to instance variables
        self.api_key = api_key
        self.api_base = api_base
        
        if not self.api_key:
            raise ValueError("FPT_AI_API_KEY is not configured.")
            
        self.api_url = "https://api.fpt.ai/llm/v1/completion"
        self.model = "Llama-3.3-70B-Instruct"
        self.headers = {
            "Content-Type": "application/json",
            "api_key": self.api_key  # FPT AI uses api_key in headers, not Bearer token
        }

    def _format_history(self, history: Sequence[Message]) -> List[Dict[str, Any]]:
        # Format messages for the chat completion API
        formatted_history = []
        for msg in history:
            role = "assistant" if msg.sender == MessageSender.AI else "user"
            formatted_history.append({"role": role, "content": msg.content})
        return formatted_history

    def get_response(
        self, *, character: Character, history: Sequence[Message]
    ) -> str:
        system_prompt = self._build_system_prompt(character)
        formatted_history = self._format_history(history)
        
        # Add system message at the beginning
        messages = [{"role": "system", "content": system_prompt}] + formatted_history
        
        # Last user message check
        last_user_message_content = next((msg.content for msg in reversed(history) if msg.sender == MessageSender.USER), None)
        if not last_user_message_content:
            # If no user message (e.g., first interaction after greeting), use greeting
            return character.greeting_message or f"Hi! I'm {character.name}."

        logger.debug(f"--- FPT AI Request ---")
        logger.debug(f"System Prompt: {system_prompt}")
        logger.debug(f"Formatted History: {formatted_history}")
        
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.9,
            "max_tokens": 1024,
            "stream": False
        }
        
        try:
            response = requests.post(
                self.api_url,
                headers=self.headers,
                data=json.dumps(payload),
                timeout=30
            )
            
            if response.status_code != 200:
                logger.error(f"FPT AI API error: {response.status_code} - {response.text}")
                return f"(OOC: Sorry, I encountered an error trying to respond as {character.name}. API returned status {response.status_code}.)"
            
            result = response.json()
            # Extract response based on FPT AI API response format
            # Assuming the response structure is {"choices": [{"message": {"content": "..."}}]}
            content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
            
            if not content:
                logger.error(f"FPT AI API returned empty content: {result}")
                return f"(OOC: Sorry, I received an empty response when trying to respond as {character.name}.)"
            
            logger.debug(f"--- FPT AI Response ---: {content}")
            return content.strip()
            
        except Exception as e:
            logger.error(f"Error calling FPT AI API: {e}", exc_info=True)
            # Provide a generic fallback response
            return f"(OOC: Sorry, I encountered an error trying to respond as {character.name}.)"


# --- Provider Management ---
_provider_instances_cache: Dict[str, AIProvider] = {}
_DEFAULT_PROVIDER_NAME = "gemini" # Fallback default

SUPPORTED_PROVIDERS: Dict[str, Type[AIProvider]] = {
    "gemini": GeminiProvider,
    "openai": OpenAIProvider,       # For direct OpenAI API
    "claude": ClaudeProvider,
    "fptai": FPTAIProvider,
    # OpenRouter model providers
    "deepseek-r1": DeepSeekR1Provider,
    "sarvam": SarvamProvider,
    "deepseek-chat": DeepSeekChatProvider,
    "qwen3": Qwen3Provider,
    "gemma3": Gemma3Provider,
    # "old_openrouter": OldOpenRouterProvider, # Keep if needed for transition, otherwise remove
}

def _get_active_provider_name_from_db(session: Session) -> str:
    config = get_ai_provider_config(session)
    if config and config.active_provider_name in SUPPORTED_PROVIDERS:
        return config.active_provider_name
    
    # If no config or invalid, set to default and return default
    default_to_set = _DEFAULT_PROVIDER_NAME
    for potential_default in [settings.DEFAULT_AI_PROVIDER, _DEFAULT_PROVIDER_NAME]: # Check settings first
        if potential_default in SUPPORTED_PROVIDERS:
            default_to_set = potential_default
            
    logger.warning(f"AI Config not found or invalid in DB. Setting and using default: {default_to_set}")
    crud_set_ai_provider_config(session, default_to_set) # This commits
    return default_to_set

def get_ai_provider(session: Session) -> AIProvider:
    active_provider_name = _get_active_provider_name_from_db(session)

    if active_provider_name not in _provider_instances_cache:
        logger.info(f"AI Service: Initializing provider instance for {active_provider_name}")
        if active_provider_name not in SUPPORTED_PROVIDERS:
            logger.error(f"Misconfigured/Unsupported AI provider in DB: {active_provider_name}. Falling back to {_DEFAULT_PROVIDER_NAME}.")
            active_provider_name = _DEFAULT_PROVIDER_NAME # Fallback logic
            # Attempt to fix in DB for next time
            crud_set_ai_provider_config(session, active_provider_name)

        provider_class = SUPPORTED_PROVIDERS[active_provider_name]
        api_key, api_base, model_name = None, None, None # model_name can be set per provider class default

        if active_provider_name == "gemini":
            api_key = settings.GEMINI_API_KEY
        elif active_provider_name == "openai": # Direct OpenAI usage
            api_key = settings.OPENAI_API_KEY
            model_name = settings.OPENAI_DEFAULT_MODEL or "gpt-4o" # Default for direct OpenAI
        elif active_provider_name in ["deepseek-r1", "sarvam", "deepseek-chat", "qwen3", "gemma3"]:
            # All OpenRouter model providers
            api_key = settings.OPENROUTER_API_KEY
        elif active_provider_name == "claude":
            api_key = settings.ANTHROPIC_API_KEY
        elif active_provider_name == "fptai":
            api_key = settings.FPT_AI_API_KEY
            api_base = "https://mkp-api.fptcloud.com" # If FPT has a configurable base
            model_name = "llama-3.3-70b-instruct" # FPT's default, as example

        try:
            constructor_args = {"api_key": api_key, "api_base": api_base}
            if active_provider_name in ["openai", "claude"]: # Providers that accept model_name
                constructor_args["model_name"] = model_name
            
            _provider_instances_cache[active_provider_name] = provider_class(**constructor_args)
            logger.info(f"AI Service: Provider {active_provider_name} initialized and cached.")
        except ValueError as e: # Catch API key missing, etc.
            logger.error(f"AI Service: Failed to initialize {active_provider_name}: {e}. Clearing from cache and re-raising.")
            if active_provider_name in _provider_instances_cache:
                del _provider_instances_cache[active_provider_name]
            raise # Re-raise to signal failure to caller
        except Exception as e_generic:
            logger.error(f"AI Service: Generic error initializing {active_provider_name}: {e_generic}. Clearing and re-raising.", exc_info=True)
            if active_provider_name in _provider_instances_cache:
                del _provider_instances_cache[active_provider_name]
            raise
            
    return _provider_instances_cache[active_provider_name]

def get_ai_response(*, session: Session, character: Character, history: Sequence[Message]) -> str:
    try:
        provider = get_ai_provider(session=session)
    except Exception as e_get_provider:
        logger.error(f"Failed to get AI provider for {character.name}: {e_get_provider}", exc_info=True)
        return character.fallback_response or "I'm having trouble reaching my AI brain at the moment."
        
    logger.info(f"Using AI provider: {provider.__class__.__name__} (model: {getattr(provider, 'model_name', 'N/A')}) for character {character.name}")
    
    # Removed character-specific model override logic.
    # The provider instance fetched by get_ai_provider (using global settings) will always be used.
            
    return provider.get_response(character=character, history=history)

def get_available_providers() -> List[str]:
    available = []
    # Use getattr to safely access API keys, providing None if the attribute doesn't exist.
    # This prevents AttributeError if a key isn't defined in the Settings model or environment.
    # The subsequent `if` check will correctly evaluate to false if the key is None or an empty string.
    if getattr(settings, "GEMINI_API_KEY", None): available.append("gemini")
    if getattr(settings, "OPENAI_API_KEY", None): available.append("openai")
    if getattr(settings, "OPENROUTER_API_KEY", None): 
        # Add all OpenRouter model providers if OpenRouter API key is configured
        available.extend(["deepseek-r1", "sarvam", "deepseek-chat", "qwen3", "gemma3"])
    if getattr(settings, "ANTHROPIC_API_KEY", None): available.append("claude")
    if getattr(settings, "FPT_AI_API_KEY", None): available.append("fptai")
    return sorted(list(set(available))) # Ensure unique and sorted

def set_active_provider(name: str, session: Session) -> None:
    if name not in SUPPORTED_PROVIDERS:
        raise ValueError(f"Unsupported AI provider: {name}. Must be one of {list(SUPPORTED_PROVIDERS.keys())}")
    if name not in get_available_providers():
        raise ValueError(f"AI Provider '{name}' is not configured with necessary API keys/settings.")
        
    crud_set_ai_provider_config(session, name)
    logger.info(f"AI Service: Active provider set to '{name}' in DB.")
    
    # Clear instance from cache to force re-initialization with new config if necessary
    if name in _provider_instances_cache:
        del _provider_instances_cache[name]
        logger.info(f"AI Service: Cleared cached instance for {name}. It will be re-initialized on next use.")
    # Clear all cached instances to be safe, as some providers might share base classes or settings
    _provider_instances_cache.clear()
    logger.info("AI Service: All provider instances cleared from cache due to active provider change.")

def get_active_ai_provider_name_from_service(session: Session) -> str:
    return _get_active_provider_name_from_db(session)

# Example of how a FastAPI dependency for session could be used (conceptual)
# Needs to be defined in api.deps or similar
# def get_ai_session() -> Session:
#     with Session(engine) as session: # Assuming 'engine' is your SQLModel engine
#         yield session

# To be called by routes in config.py:
# get_active_ai_provider_name_from_service(session=SessionDep)
# set_active_provider(name=provider_name, session=SessionDep)

# To be called by message sending logic:
# get_ai_response(session=SessionDep, character=..., history=...)

# Initialize providers on module load