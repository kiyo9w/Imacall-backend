import pytest
from unittest.mock import patch, MagicMock, Mock
import json
from app.services.ai_service import OpenRouterProvider
from app.models import Character, Message, MessageSender

@pytest.fixture
def mock_character():
    return Character(
        id=1,
        name="Test Character",
        description="A test character for unit tests",
        scenario="Testing scenario",
        personality_traits="Helpful, friendly",
        writing_style="Clear, concise",
        background="Created for testing",
        knowledge_scope="Testing frameworks",
        quirks="Occasionally makes testing jokes",
        emotional_range="Neutral",
        language="English",
        greeting_message="Hello, I'm a test character!",
        created_by_id=1
    )

@pytest.fixture
def mock_history():
    return [
        Message(id=1, conversation_id=1, content="Hello", sender=MessageSender.USER),
        Message(id=2, conversation_id=1, content="Hi there! How can I help?", sender=MessageSender.AI),
        Message(id=3, conversation_id=1, content="Tell me about yourself", sender=MessageSender.USER),
    ]

@pytest.fixture
def mock_response():
    return {
        "choices": [
            {
                "message": {
                    "content": "I'm Test Character, a friendly AI created for testing purposes. I have a background in testing frameworks and enjoy helping users with clear and concise responses. Is there anything specific about testing you'd like to know?"
                }
            }
        ]
    }

class TestOpenRouterProvider:
    
    def test_initialization(self):
        # Test successful initialization
        provider = OpenRouterProvider(api_key="test_key")
        assert provider.api_key == "test_key"
        assert provider.model == "qwen/qwen3-30b-a3b:free"
        
        # Test initialization with missing API key
        with pytest.raises(ValueError):
            OpenRouterProvider(api_key=None)
    
    def test_build_system_prompt(self, mock_character):
        provider = OpenRouterProvider(api_key="test_key")
        prompt = provider._build_system_prompt(mock_character)
        
        # Check that the prompt contains key character information
        assert "Test Character" in prompt
        assert "A test character for unit tests" in prompt
        assert "Testing scenario" in prompt
        assert "Helpful, friendly" in prompt
        assert "Clear, concise" in prompt
    
    def test_format_history(self, mock_history):
        provider = OpenRouterProvider(api_key="test_key")
        formatted = provider._format_history(mock_history)
        
        # Check that history is correctly formatted
        assert len(formatted) == 3
        assert formatted[0]["role"] == "user"
        assert formatted[0]["content"] == "Hello"
        assert formatted[1]["role"] == "assistant"
        assert formatted[1]["content"] == "Hi there! How can I help?"
        assert formatted[2]["role"] == "user"
        assert formatted[2]["content"] == "Tell me about yourself"
    
    @patch('requests.post')
    def test_get_response_success(self, mock_post, mock_character, mock_history, mock_response):
        # Setup mock response
        mock_response_obj = Mock()
        mock_response_obj.status_code = 200
        mock_response_obj.json.return_value = mock_response
        mock_post.return_value = mock_response_obj
        
        provider = OpenRouterProvider(api_key="test_key")
        response = provider.get_response(character=mock_character, history=mock_history)
        
        # Verify the response is what we expect
        assert response == "I'm Test Character, a friendly AI created for testing purposes. I have a background in testing frameworks and enjoy helping users with clear and concise responses. Is there anything specific about testing you'd like to know?"
        
        # Verify the API was called with expected parameters
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        
        # Check that URL, headers, and timeout are correct
        assert call_args[1]["url"] == "https://openrouter.ai/api/v1/chat/completions"
        assert call_args[1]["headers"]["Authorization"] == "Bearer test_key"
        assert call_args[1]["timeout"] == 30
        
        # Check payload
        payload = call_args[1]["json"]
        assert payload["model"] == "qwen/qwen3-30b-a3b:free"
        assert len(payload["messages"]) == 4  # system prompt + 3 messages
        assert payload["messages"][0]["role"] == "system"
        assert "Test Character" in payload["messages"][0]["content"]
    
    @patch('requests.post')
    def test_get_response_api_error(self, mock_post, mock_character, mock_history):
        # Setup mock response for API error
        mock_response_obj = Mock()
        mock_response_obj.status_code = 400
        mock_response_obj.text = "Bad Request"
        mock_post.return_value = mock_response_obj
        
        provider = OpenRouterProvider(api_key="test_key")
        response = provider.get_response(character=mock_character, history=mock_history)
        
        # Verify we get a fallback response with error information
        assert response.startswith("(OOC: Sorry, I encountered an error")
        assert "API returned status 400" in response
    
    @patch('requests.post')
    def test_get_response_empty_content(self, mock_post, mock_character, mock_history):
        # Setup mock response with empty content
        mock_response_obj = Mock()
        mock_response_obj.status_code = 200
        mock_response_obj.json.return_value = {"choices": [{"message": {"content": ""}}]}
        mock_post.return_value = mock_response_obj
        
        provider = OpenRouterProvider(api_key="test_key")
        response = provider.get_response(character=mock_character, history=mock_history)
        
        # Verify we get a fallback response about empty content
        assert response.startswith("(OOC: Sorry, I received an empty response")
    
    @patch('requests.post')
    def test_get_response_exception(self, mock_post, mock_character, mock_history):
        # Setup mock response to raise exception
        mock_post.side_effect = Exception("Test exception")
        
        provider = OpenRouterProvider(api_key="test_key")
        response = provider.get_response(character=mock_character, history=mock_history)
        
        # Verify we get a fallback response about the error
        assert response.startswith("(OOC: Sorry, I encountered an error")
    
    def test_greeting_when_no_user_message(self, mock_character):
        # Test empty history
        provider = OpenRouterProvider(api_key="test_key")
        response = provider.get_response(character=mock_character, history=[])
        
        # Should return greeting message
        assert response == "Hello, I'm a test character!"
        
        # Test history with only AI messages (no user messages)
        ai_only_history = [
            Message(id=1, conversation_id=1, content="Initial greeting", sender=MessageSender.AI)
        ]
        response = provider.get_response(character=mock_character, history=ai_only_history)
        
        # Should also return greeting message
        assert response == "Hello, I'm a test character!" 