# Placeholder for AI service integration logic 

import logging
import uuid
import json
import requests
from typing import Sequence, Protocol, runtime_checkable, Any, Dict, Type, List, Tuple
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold

from app.models import Character, Message, MessageSender
from app.core.config import settings

logger = logging.getLogger(__name__)

# --- Provider Interface ---

@runtime_checkable
class AIProvider(Protocol):
    """Interface for AI model providers."""
    def __init__(self, api_key: str | None):
        ...

    def get_response(
        self, *, character: Character, history: Sequence[Message]
    ) -> str:
        """Generates a response based on character and history."""
        ...


# --- Provider Implementations ---

class GeminiProvider(AIProvider):
    """Google Gemini provider (using gemini-1.5-flash-latest)."""
    def __init__(self, api_key: str | None):
        if not api_key:
            raise ValueError("GEMINI_API_KEY is not configured.")
        genai.configure(api_key=api_key)
        # Using flash model for speed and cost
        self.model = genai.GenerativeModel('gemini-1.5-flash-latest')
        self.safety_settings = {
            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
        }

    def _build_system_prompt(self, character: Character) -> str:
        prompt_parts = [
            f"You are {character.name}. Respond as this character.",
            f"Description: {character.description}" if character.description else "",
            f"Scenario: {character.scenario}" if character.scenario else "",
            f"Personality Traits: {character.personality_traits}" if character.personality_traits else "",
            f"Writing Style: {character.writing_style}" if character.writing_style else "",
            f"Background: {character.background}" if character.background else "",
            f"Knowledge Scope: {character.knowledge_scope}" if character.knowledge_scope else "",
            f"Quirks: {character.quirks}" if character.quirks else "",
            f"Emotional Range: {character.emotional_range}" if character.emotional_range else "",
            f"Language: Respond in {character.language}." if character.language else "Respond in English.",
            "Maintain character consistency throughout the conversation.",
            "Keep responses concise and engaging unless the user prompts for more detail.",
        ]
        return "\n".join(filter(None, prompt_parts)) # Filter out empty strings

    def _format_history(self, history: Sequence[Message]) -> List[Dict[str, Any]]:
        # Gemini uses 'user' and 'model' roles
        formatted_history = []
        for msg in history:
            role = "model" if msg.sender == MessageSender.AI else "user"
            formatted_history.append({"role": role, "parts": [msg.content]})
        return formatted_history

    def get_response(
        self, *, character: Character, history: Sequence[Message]
    ) -> str:
        system_prompt = self._build_system_prompt(character)
        formatted_history = self._format_history(history)

        # Combine system prompt and history
        # Gemini API can take system instruction + history
        contents = formatted_history # History first

        logger.debug(f"--- Gemini Request ---")
        logger.debug(f"System Prompt: {system_prompt}")
        logger.debug(f"Formatted History: {formatted_history}")

        try:
            # Start chat with history and system instruction
            chat = self.model.start_chat(history=formatted_history)

            # Use the latest user message from history as the prompt to send
            last_user_message_content = next((msg.content for msg in reversed(history) if msg.sender == MessageSender.USER), None)
            if not last_user_message_content:
                 # If no user message (e.g., first interaction after greeting), use greeting
                 return character.greeting_message or f"Hi! I'm {character.name}."

            # Send the message with the system instruction applied implicitly by the model
            # Note: The gemini library manages history internally in the chat object.
            # Sending the last user message content continues the chat.
            response = chat.send_message(
                last_user_message_content,
                generation_config=genai.types.GenerationConfig(
                    # candidate_count=1, # Default is 1
                    # max_output_tokens=8192, # Adjust if needed
                    temperature=0.9, # Adjust creativity
                ),
                safety_settings=self.safety_settings,
                # System instruction is set at model level or implicitly via history context
            )

            logger.debug(f"--- Gemini Response ---: {response.text}")
            return response.text.strip()
        except Exception as e:
            logger.error(f"Error calling Gemini API: {e}", exc_info=True)
            # Provide a generic fallback response
            return f"(OOC: Sorry, I encountered an error trying to respond as {character.name}.)"


class OpenAIProvider(AIProvider):
    """Placeholder for OpenAI provider."""
    def __init__(self, api_key: str | None):
        if not api_key:
            logger.warning("OPENAI_API_KEY is not configured. OpenAIProvider will not work.")
        # Initialize OpenAI client here (e.g., import openai; openai.api_key = api_key)

    def get_response(
        self, *, character: Character, history: Sequence[Message]
    ) -> str:
        logger.warning("OpenAIProvider.get_response called but not implemented.")
        raise NotImplementedError("OpenAI provider is not yet implemented.")
        # Implementation would involve:
        # 1. Building a system prompt similar to Gemini.
        # 2. Formatting history (roles: system, user, assistant).
        # 3. Calling the OpenAI ChatCompletion API.
        # return f"(OOC: OpenAI provider for {character.name} not implemented)"

class ClaudeProvider(AIProvider):
    """Placeholder for Anthropic Claude provider."""
    def __init__(self, api_key: str | None):
        if not api_key:
             logger.warning("CLAUDE_API_KEY is not configured. ClaudeProvider will not work.")
        # Initialize Claude client here

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

class OpenRouterProvider(AIProvider):
    """OpenRouter provider for accessing various LLMs (using Qwen3 30B A3B by default)."""
    def __init__(self, api_key: str | None):
        if not api_key:
            raise ValueError("OPENROUTER_API_KEY is not configured.")
        self.api_key = api_key
        # OpenRouter API endpoint for chat completions
        self.api_url = "https://openrouter.ai/api/v1/chat/completions"
        # Default to Qwen3 30B A3B (free)
        self.model = "qwen/qwen3-30b-a3b:free"
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "https://imacall.app",  # Replace with your actual site URL
            "X-Title": "ImaCall",  # Replace with your site name
        }

    def _build_system_prompt(self, character: Character) -> str:
        prompt_parts = [
            f"You are {character.name}. Respond as this character.",
            f"Description: {character.description}" if character.description else "",
            f"Scenario: {character.scenario}" if character.scenario else "",
            f"Personality Traits: {character.personality_traits}" if character.personality_traits else "",
            f"Writing Style: {character.writing_style}" if character.writing_style else "",
            f"Background: {character.background}" if character.background else "",
            f"Knowledge Scope: {character.knowledge_scope}" if character.knowledge_scope else "",
            f"Quirks: {character.quirks}" if character.quirks else "",
            f"Emotional Range: {character.emotional_range}" if character.emotional_range else "",
            f"Language: Respond in {character.language}." if character.language else "Respond in English.",
            "Maintain character consistency throughout the conversation.",
            "Keep responses concise and engaging unless the user prompts for more detail.",
        ]
        return "\n".join(filter(None, prompt_parts)) # Filter out empty strings

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
    def __init__(self, api_key: str | None):
        if not api_key:
            raise ValueError("FPT_AI_API_KEY is not configured.")
        self.api_key = api_key
        # URL for FPT AI Marketplace API
        self.api_url = "https://api.fpt.ai/llm/v1/completion"
        self.model = "Llama-3.3-70B-Instruct"
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

    def _build_system_prompt(self, character: Character) -> str:
        prompt_parts = [
            f"You are {character.name}. Respond as this character.",
            f"Description: {character.description}" if character.description else "",
            f"Scenario: {character.scenario}" if character.scenario else "",
            f"Personality Traits: {character.personality_traits}" if character.personality_traits else "",
            f"Writing Style: {character.writing_style}" if character.writing_style else "",
            f"Background: {character.background}" if character.background else "",
            f"Knowledge Scope: {character.knowledge_scope}" if character.knowledge_scope else "",
            f"Quirks: {character.quirks}" if character.quirks else "",
            f"Emotional Range: {character.emotional_range}" if character.emotional_range else "",
            f"Language: Respond in {character.language}." if character.language else "Respond in English.",
            "Maintain character consistency throughout the conversation.",
            "Keep responses concise and engaging unless the user prompts for more detail.",
        ]
        return "\n".join(filter(None, prompt_parts)) # Filter out empty strings

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


# --- Service Management ---

_providers: Dict[str, AIProvider] = {}
_active_provider_name: str = "gemini"  # Default provider

def initialize_providers():
    """Initializes available providers based on configured API keys."""
    global _providers
    _providers = {} # Reset on initialization

    provider_classes: Dict[str, Tuple[Type[AIProvider], str | None]] = {
        "gemini": (GeminiProvider, settings.GEMINI_API_KEY),
        "openai": (OpenAIProvider, settings.OPENAI_API_KEY),
        "claude": (ClaudeProvider, settings.CLAUDE_API_KEY),
        "fptai": (FPTAIProvider, settings.FPT_AI_API_KEY),
        "openrouter": (OpenRouterProvider, settings.OPENROUTER_API_KEY),
    }

    for name, (provider_class, api_key) in provider_classes.items():
        try:
            # Only initialize if the key is present, even if the constructor handles None
            if api_key:
                 _providers[name] = provider_class(api_key=api_key)
                 logger.info(f"Initialized AI provider: {name}")
            else:
                logger.warning(f"API key for {name} not found. Provider not initialized.")
        except Exception as e:
            logger.error(f"Failed to initialize AI provider {name}: {e}", exc_info=True)

def get_available_providers() -> List[str]:
    """Returns a list of successfully initialized provider names."""
    return list(_providers.keys())

def set_active_provider(provider_name: str) -> bool:
    """Sets the active AI provider."""
    global _active_provider_name
    if provider_name in _providers:
        _active_provider_name = provider_name
        logger.info(f"Active AI provider set to: {provider_name}")
        return True
    else:
        logger.error(f"Attempted to set active provider to unavailable service: {provider_name}")
        return False

def get_active_provider_name() -> str:
    """Gets the name of the currently active AI provider."""
    return _active_provider_name


# --- Main Service Function ---

def get_ai_response(
    *, character: Character, history: Sequence[Message]
) -> str:
    """
    Gets a response from the currently active AI provider.

    Args:
        character: The character the user is talking to.
        history: A sequence of recent messages in the conversation.

    Returns:
        A string containing the AI's response.
    """
    if not _providers:
        logger.critical("No AI providers initialized. Trying to initialize now.")
        initialize_providers()
        if not _providers:
             logger.error("AI Service unavailable: No providers could be initialized.")
             return f"(OOC: AI Service is currently unavailable for {character.name}. No providers configured.)"

    if _active_provider_name not in _providers:
        logger.error(f"Active provider '{_active_provider_name}' is not available. Falling back to first available.")
        # Fallback logic: try gemini first, then the first available one
        fallback_order = ["gemini"] + get_available_providers()
        for name in fallback_order:
            if name in _providers:
                logger.warning(f"Falling back to provider: {name}")
                set_active_provider(name)
                break
        else:
            # Should not happen if _providers is not empty, but safety check
            logger.error("AI Service unavailable: Could not find any fallback provider.")
            return f"(OOC: AI Service is currently unavailable for {character.name}. Fallback failed.)"

    provider = _providers[_active_provider_name]

    logger.info(f"Getting AI response for character '{character.name}' using provider: '{_active_provider_name}'")
    logger.debug(f"History provided: {[(msg.sender, msg.content) for msg in history]}")

    try:
        response = provider.get_response(character=character, history=history)
        logger.debug(f"AI Response received: {response}")
        return response
    except NotImplementedError:
         logger.error(f"Provider '{_active_provider_name}' is not fully implemented.")
         return f"(OOC: The selected AI provider ({_active_provider_name}) is not implemented yet for {character.name}.)"
    except Exception as e:
        logger.error(f"Error getting response from provider '{_active_provider_name}': {e}", exc_info=True)
        return f"(OOC: Sorry, I encountered an error trying to respond as {character.name} using {_active_provider_name}.)"

# Initialize providers on module load
initialize_providers() 