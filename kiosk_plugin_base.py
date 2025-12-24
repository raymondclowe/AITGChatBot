"""
Kiosk Plugin System - Base Classes and Utilities

This module provides the foundational classes and utilities for the extensible
kiosk mode plugin system, enabling AI-powered message transformation and custom logic.
"""

import time
import base64
import logging
from io import BytesIO
from typing import Dict, Any, List, Optional, Union
from functools import wraps

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


# Plugin configuration
class PluginConfig:
    """Configuration for plugin system"""
    enabled = True
    timeout = 5.0  # seconds
    max_failures = 3
    debug = False


class PluginAIHelper:
    """
    Helper class providing AI and utility functions for plugin developers.
    Provides a simple API for calling AI models, converting images, and more.
    """
    
    def __init__(self, session_data, openrouter_api_key, openrouter_url):
        """
        Initialize the AI helper.
        
        Args:
            session_data: Reference to the session data dictionary
            openrouter_api_key: OpenRouter API key
            openrouter_url: OpenRouter API endpoint URL
        """
        self.session_data = session_data
        self.openrouter_api_key = openrouter_api_key
        self.openrouter_url = openrouter_url
        self.logger = logging.getLogger('plugin_ai_helper')
    
    def call_ai(self, prompt: str, model: Optional[str] = None, 
                max_tokens: int = 500, images: Optional[List[str]] = None) -> str:
        """
        Call an AI model with a prompt and optional images.
        
        Args:
            prompt: The text prompt to send to the AI
            model: Model to use (default: gpt-4o-mini)
            max_tokens: Maximum tokens in response
            images: List of base64-encoded images (optional)
        
        Returns:
            The AI's response text
        """
        import requests
        
        if model is None:
            model = "gpt-4o-mini"
        
        # Build message content
        content = [{"type": "text", "text": prompt}]
        
        # Add images if provided
        if images:
            for img_b64 in images:
                content.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}
                })
        
        # Build payload
        payload = {
            "model": model,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": content}]
        }
        
        try:
            response = requests.post(
                self.openrouter_url,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.openrouter_api_key}",
                    "HTTP-Referer": "https://github.com/raymondclowe/AITGChatBot",
                    "X-Title": "AITGChatBot-Plugin",
                },
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            result = response.json()
            
            # Extract text from response
            choices = result.get('choices', [])
            if choices:
                message = choices[0].get('message', {})
                content = message.get('content', '')
                return content
            return ""
        except Exception as e:
            self.logger.error(f"Error calling AI: {e}")
            return ""
    
    def quick_call(self, system: str, user: str, model: Optional[str] = None) -> str:
        """
        Quick AI call with system and user messages.
        
        Args:
            system: System prompt
            user: User message
            model: Model to use (default: gpt-4o-mini)
        
        Returns:
            The AI's response text
        """
        import requests
        
        if model is None:
            model = "gpt-4o-mini"
        
        payload = {
            "model": model,
            "max_tokens": 500,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user}
            ]
        }
        
        try:
            response = requests.post(
                self.openrouter_url,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.openrouter_api_key}",
                    "HTTP-Referer": "https://github.com/raymondclowe/AITGChatBot",
                    "X-Title": "AITGChatBot-Plugin",
                },
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            result = response.json()
            
            choices = result.get('choices', [])
            if choices:
                message = choices[0].get('message', {})
                content = message.get('content', '')
                return content
            return ""
        except Exception as e:
            self.logger.error(f"Error in quick_call: {e}")
            return ""
    
    def base64_to_pil(self, b64_string: str) -> Optional[Any]:
        """
        Convert base64 string to PIL Image.
        
        Args:
            b64_string: Base64-encoded image data
        
        Returns:
            PIL Image object or None if conversion fails
        """
        if not PIL_AVAILABLE:
            self.logger.warning("PIL not available, cannot convert to PIL Image")
            return None
        
        try:
            image_data = base64.b64decode(b64_string)
            image = Image.open(BytesIO(image_data))
            return image
        except Exception as e:
            self.logger.error(f"Error converting base64 to PIL: {e}")
            return None
    
    def pil_to_base64(self, image: Any, format: str = 'JPEG') -> Optional[str]:
        """
        Convert PIL Image to base64 string.
        
        Args:
            image: PIL Image object
            format: Image format (JPEG, PNG, etc.)
        
        Returns:
            Base64-encoded string or None if conversion fails
        """
        if not PIL_AVAILABLE:
            self.logger.warning("PIL not available, cannot convert from PIL Image")
            return None
        
        try:
            buffer = BytesIO()
            image.save(buffer, format=format)
            buffer.seek(0)
            b64_string = base64.b64encode(buffer.read()).decode('utf-8')
            return b64_string
        except Exception as e:
            self.logger.error(f"Error converting PIL to base64: {e}")
            return None


class KioskPlugin:
    """
    Base class for kiosk mode plugins.
    
    All plugins must implement all 10 hook methods, even if they just pass through data.
    Hooks are called at specific points in the message processing pipeline and can
    transform data, add metadata, or trigger custom logic.
    
    Context Dictionary Structure:
        session_data: The full session data dict (be careful with mutations!)
        chat_id: The chat/session ID
        history: Conversation history
        metadata: Plugin-specific metadata dict
        ai_helper: PluginAIHelper instance for AI calls
        model: Current model name
        kiosk_mode: Boolean indicating if kiosk mode is active
    """
    
    def pre_user_text(self, text: str, context: Dict[str, Any]) -> str:
        """
        Process user text before it enters the system.
        Called immediately after receiving user text but before any processing.
        
        Args:
            text: The user's text message
            context: Rich context dictionary
        
        Returns:
            Modified text (or original if no changes)
        """
        return text
    
    def post_user_text(self, text: str, context: Dict[str, Any]) -> str:
        """
        Process user text after initial processing but before sending to AI.
        Called after prompt enhancement but before adding to conversation.
        
        Args:
            text: The processed user text
            context: Rich context dictionary
        
        Returns:
            Modified text (or original if no changes)
        """
        return text
    
    def pre_user_images(self, images: List[str], text: str, context: Dict[str, Any]) -> List[str]:
        """
        Process user images before they enter the system.
        Called after receiving images but before adding to message.
        
        Args:
            images: List of base64-encoded images
            text: Associated user text
            context: Rich context dictionary
        
        Returns:
            Modified images list (or original if no changes)
        """
        return images
    
    def post_user_images(self, images: List[str], text: str, context: Dict[str, Any]) -> List[str]:
        """
        Process user images after initial processing.
        Called after images are added to the message but before sending to AI.
        
        Args:
            images: List of base64-encoded images
            text: Associated user text
            context: Rich context dictionary
        
        Returns:
            Modified images list (or original if no changes)
        """
        return images
    
    def pre_assistant_text(self, text: str, context: Dict[str, Any]) -> str:
        """
        Process assistant text immediately after receiving from AI.
        Called right after extracting text from AI response.
        
        Args:
            text: The assistant's response text
            context: Rich context dictionary
        
        Returns:
            Modified text (or original if no changes)
        """
        return text
    
    def post_assistant_text(self, text: str, context: Dict[str, Any]) -> str:
        """
        Process assistant text before sending to user.
        Called after all processing but before sending to Telegram.
        
        Args:
            text: The final assistant text
            context: Rich context dictionary
        
        Returns:
            Modified text (or original if no changes)
        """
        return text
    
    def pre_assistant_images(self, images: List[str], text: str, context: Dict[str, Any]) -> List[str]:
        """
        Process assistant images immediately after receiving from AI.
        Called right after extracting images from AI response.
        
        Args:
            images: List of base64-encoded images
            text: Associated assistant text
            context: Rich context dictionary
        
        Returns:
            Modified images list (or original if no changes)
        """
        return images
    
    def post_assistant_images(self, images: List[str], text: str, context: Dict[str, Any]) -> List[str]:
        """
        Process assistant images before sending to user.
        Called after all processing but before sending to Telegram.
        
        Args:
            images: List of base64-encoded images
            text: Associated assistant text
            context: Rich context dictionary
        
        Returns:
            Modified images list (or original if no changes)
        """
        return images
    
    def on_session_start(self, context: Dict[str, Any]) -> None:
        """
        Called when a new session is initialized.
        Use for setup, initialization, or welcome logic.
        
        Args:
            context: Rich context dictionary
        """
        pass
    
    def on_message_complete(self, context: Dict[str, Any]) -> None:
        """
        Called after a complete message exchange (user + assistant).
        Use for logging, analytics, or cleanup.
        
        Args:
            context: Rich context dictionary
        """
        pass
    
    def get_commands(self) -> Dict[str, Dict[str, Any]]:
        """
        Register custom slash commands that this plugin provides.
        
        Returns:
            Dictionary mapping command names (without /) to command info:
            {
                'command_name': {
                    'description': 'Brief description',
                    'handler': method_reference,
                    'available_in_kiosk': True/False
                }
            }
        
        Example:
            {
                'generate-worksheets': {
                    'description': 'Generate practice worksheets',
                    'handler': self.handle_generate_worksheets,
                    'available_in_kiosk': True
                }
            }
        """
        return {}
    
    def send_message(self, chat_id: str, text: str, context: Dict[str, Any]) -> None:
        """
        Send a message to the user. Use this in command handlers to send responses.
        
        Args:
            chat_id: The chat ID to send to
            text: The message text to send
            context: Rich context dictionary (contains send_message_fn)
        """
        send_fn = context.get('send_message_fn')
        if send_fn:
            send_fn(chat_id, text)
        else:
            self.logger.warning("send_message_fn not available in context")
    
    def send_document(self, chat_id: str, document_data: bytes, filename: str, 
                     caption: str, context: Dict[str, Any]) -> None:
        """
        Send a document/file to the user. Use this in command handlers.
        
        Args:
            chat_id: The chat ID to send to
            document_data: Binary data of the document
            filename: Name for the file
            caption: Caption for the document
            context: Rich context dictionary (contains send_document_fn)
        """
        send_fn = context.get('send_document_fn')
        if send_fn:
            send_fn(chat_id, document_data, filename, caption)
        else:
            self.logger.warning("send_document_fn not available in context")


def with_timeout(timeout_seconds: float):
    """
    Decorator to add timeout handling to plugin hooks.
    
    Args:
        timeout_seconds: Maximum execution time in seconds
    
    Note:
        Uses signal-based timeout on Unix-like systems. On Windows or in 
        multi-threaded contexts, timeout may not work reliably. Consider
        using threading.Timer or asyncio for production Windows deployments.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Check if we can use signal-based timeout
            try:
                import signal
                
                def timeout_handler(signum, frame):
                    raise TimeoutError(f"Plugin hook {func.__name__} exceeded timeout of {timeout_seconds}s")
                
                # Set the alarm
                old_handler = signal.signal(signal.SIGALRM, timeout_handler)
                signal.alarm(int(timeout_seconds))
                
                try:
                    result = func(*args, **kwargs)
                    return result
                finally:
                    # Cancel the alarm and restore old handler
                    signal.alarm(0)
                    signal.signal(signal.SIGALRM, old_handler)
            except (AttributeError, ValueError):
                # SIGALRM not available (e.g., Windows) - run without timeout
                # In production, consider using threading.Timer as fallback
                return func(*args, **kwargs)
        
        return wrapper
    return decorator


class PluginHealthMonitor:
    """
    Monitor plugin health and automatically disable plugins with repeated failures.
    """
    
    def __init__(self, max_failures: int = 3):
        self.max_failures = max_failures
        self.failure_counts = {}
        self.disabled = False
        self.logger = logging.getLogger('plugin_health')
    
    def record_failure(self, hook_name: str) -> bool:
        """
        Record a failure for a specific hook.
        
        Args:
            hook_name: Name of the hook that failed
        
        Returns:
            True if plugin should be disabled
        """
        if hook_name not in self.failure_counts:
            self.failure_counts[hook_name] = 0
        
        self.failure_counts[hook_name] += 1
        total_failures = sum(self.failure_counts.values())
        
        if total_failures >= self.max_failures:
            self.disabled = True
            self.logger.error(f"Plugin disabled after {total_failures} failures")
            return True
        
        return False
    
    def record_success(self, hook_name: str) -> None:
        """
        Record a successful hook execution.
        
        Args:
            hook_name: Name of the hook that succeeded
        """
        # Reset failure count for this hook on success
        if hook_name in self.failure_counts:
            self.failure_counts[hook_name] = 0
    
    def is_healthy(self) -> bool:
        """Check if plugin is healthy (not disabled)."""
        return not self.disabled
