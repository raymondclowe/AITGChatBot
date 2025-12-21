"""
Kiosk Plugin Manager

This module handles loading, managing, and invoking plugins for kiosk mode.
It provides safe plugin execution with error handling, timeouts, and health monitoring.
"""

import os
import sys
import importlib.util
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime

from kiosk_plugin_base import (
    KioskPlugin, PluginAIHelper, PluginConfig, 
    PluginHealthMonitor, with_timeout
)


class PluginManager:
    """
    Manages the lifecycle and execution of kiosk plugins.
    
    Responsibilities:
    - Load plugin from kiosk-custom.py if present
    - Provide safe hook invocation with error handling
    - Monitor plugin health and disable on repeated failures
    - Build rich context for plugin hooks
    """
    
    def __init__(self, config: PluginConfig, session_data: dict, 
                 openrouter_api_key: str, openrouter_url: str):
        """
        Initialize the plugin manager.
        
        Args:
            config: Plugin configuration
            session_data: Reference to session_data dictionary
            openrouter_api_key: OpenRouter API key for AI calls
            openrouter_url: OpenRouter API endpoint
        """
        self.config = config
        self.session_data = session_data
        self.plugin: Optional[KioskPlugin] = None
        self.health_monitor = PluginHealthMonitor(max_failures=config.max_failures)
        self.logger = logging.getLogger('plugin_manager')
        
        # Create AI helper
        self.ai_helper = PluginAIHelper(
            session_data=session_data,
            openrouter_api_key=openrouter_api_key,
            openrouter_url=openrouter_url
        )
        
        # Plugin metadata storage (per-session)
        self.plugin_metadata: Dict[str, Dict[str, Any]] = {}
        
        if self.config.enabled:
            self.load_plugin()
    
    def load_plugin(self) -> bool:
        """
        Load plugin from kiosk-custom.py if it exists.
        
        Returns:
            True if plugin loaded successfully, False otherwise
        """
        plugin_file = 'kiosk-custom.py'
        
        if not os.path.exists(plugin_file):
            self.logger.info(f"No plugin file found at {plugin_file}, using default pass-through hooks")
            return False
        
        try:
            # Load the module
            spec = importlib.util.spec_from_file_location("kiosk_custom_plugin", plugin_file)
            if spec is None or spec.loader is None:
                self.logger.error(f"Failed to load plugin spec from {plugin_file}")
                return False
            
            module = importlib.util.module_from_spec(spec)
            
            # Add to sys.modules with unique name to avoid conflicts with future multi-plugin support
            sys.modules['kiosk_custom_plugin'] = module
            
            # Execute the module
            spec.loader.exec_module(module)
            
            # Look for a class that inherits from KioskPlugin
            plugin_class = None
            for name in dir(module):
                obj = getattr(module, name)
                if (isinstance(obj, type) and 
                    issubclass(obj, KioskPlugin) and 
                    obj is not KioskPlugin):
                    plugin_class = obj
                    break
            
            if plugin_class is None:
                self.logger.error(f"No KioskPlugin subclass found in {plugin_file}")
                return False
            
            # Instantiate the plugin
            self.plugin = plugin_class()
            
            # Validate that all required methods are present
            required_methods = [
                'pre_user_text', 'post_user_text',
                'pre_user_images', 'post_user_images',
                'pre_assistant_text', 'post_assistant_text',
                'pre_assistant_images', 'post_assistant_images',
                'on_session_start', 'on_message_complete'
            ]
            
            for method_name in required_methods:
                if not hasattr(self.plugin, method_name):
                    self.logger.error(f"Plugin missing required method: {method_name}")
                    self.plugin = None
                    return False
            
            self.logger.info(f"Successfully loaded plugin from {plugin_file}")
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 🔌 Plugin loaded: {plugin_class.__name__}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error loading plugin from {plugin_file}: {e}", exc_info=True)
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ⚠️  Failed to load plugin: {e}")
            return False
    
    def build_context(self, chat_id: str, **kwargs) -> Dict[str, Any]:
        """
        Build a rich context dictionary for plugin hooks.
        
        Args:
            chat_id: The chat/session ID
            **kwargs: Additional context data
        
        Returns:
            Context dictionary with session data, metadata, and helper
        """
        # Get or create plugin metadata for this session
        if chat_id not in self.plugin_metadata:
            self.plugin_metadata[chat_id] = {}
        
        # Build base context
        context = {
            'session_data': self.session_data.get(chat_id, {}),
            'chat_id': chat_id,
            'history': self.session_data.get(chat_id, {}).get('CONVERSATION', []),
            'metadata': self.plugin_metadata[chat_id],
            'ai_helper': self.ai_helper,
            'model': self.session_data.get(chat_id, {}).get('model_version', 'unknown'),
            'kiosk_mode': True,  # Plugins only work in kiosk mode
        }
        
        # Merge additional kwargs
        context.update(kwargs)
        
        return context
    
    def invoke_hook(self, hook_name: str, *args, chat_id: str, **kwargs) -> Any:
        """
        Safely invoke a plugin hook with error handling and timeout.
        
        Args:
            hook_name: Name of the hook method to call
            *args: Positional arguments for the hook
            chat_id: Chat/session ID
            **kwargs: Additional context data
        
        Returns:
            The hook's return value, or original data if hook fails/disabled
        """
        # If no plugin or health check fails, return original data
        if self.plugin is None or not self.health_monitor.is_healthy():
            return args[0] if args else None
        
        # Build context
        context = self.build_context(chat_id, **kwargs)
        
        try:
            # Get the hook method
            hook_method = getattr(self.plugin, hook_name)
            
            # Invoke with timeout
            if self.config.timeout > 0:
                # Create timeout wrapper
                @with_timeout(self.config.timeout)
                def timed_hook():
                    return hook_method(*args, context)
                
                result = timed_hook()
            else:
                result = hook_method(*args, context)
            
            # Record success
            self.health_monitor.record_success(hook_name)
            
            if self.config.debug:
                self.logger.debug(f"Hook {hook_name} executed successfully")
            
            return result
            
        except TimeoutError as e:
            self.logger.error(f"Timeout in hook {hook_name}: {e}")
            should_disable = self.health_monitor.record_failure(hook_name)
            if should_disable:
                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ⚠️  Plugin disabled due to repeated failures")
            return args[0] if args else None
            
        except Exception as e:
            self.logger.error(f"Error in hook {hook_name}: {e}", exc_info=True)
            should_disable = self.health_monitor.record_failure(hook_name)
            if should_disable:
                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ⚠️  Plugin disabled due to repeated failures")
            return args[0] if args else None
    
    def pre_user_text(self, text: str, chat_id: str) -> str:
        """Hook: Process user text before it enters the system."""
        return self.invoke_hook('pre_user_text', text, chat_id=chat_id)
    
    def post_user_text(self, text: str, chat_id: str) -> str:
        """Hook: Process user text after initial processing."""
        return self.invoke_hook('post_user_text', text, chat_id=chat_id)
    
    def pre_user_images(self, images: List[str], text: str, chat_id: str) -> List[str]:
        """Hook: Process user images before they enter the system."""
        return self.invoke_hook('pre_user_images', images, text, chat_id=chat_id)
    
    def post_user_images(self, images: List[str], text: str, chat_id: str) -> List[str]:
        """Hook: Process user images after initial processing."""
        return self.invoke_hook('post_user_images', images, text, chat_id=chat_id)
    
    def pre_assistant_text(self, text: str, chat_id: str) -> str:
        """Hook: Process assistant text immediately after receiving from AI."""
        return self.invoke_hook('pre_assistant_text', text, chat_id=chat_id)
    
    def post_assistant_text(self, text: str, chat_id: str) -> str:
        """Hook: Process assistant text before sending to user."""
        return self.invoke_hook('post_assistant_text', text, chat_id=chat_id)
    
    def pre_assistant_images(self, images: List[str], text: str, chat_id: str) -> List[str]:
        """Hook: Process assistant images immediately after receiving from AI."""
        return self.invoke_hook('pre_assistant_images', images, text, chat_id=chat_id)
    
    def post_assistant_images(self, images: List[str], text: str, chat_id: str) -> List[str]:
        """Hook: Process assistant images before sending to user."""
        return self.invoke_hook('post_assistant_images', images, text, chat_id=chat_id)
    
    def on_session_start(self, chat_id: str) -> None:
        """Hook: Called when a new session is initialized."""
        self.invoke_hook('on_session_start', chat_id=chat_id)
    
    def on_message_complete(self, chat_id: str) -> None:
        """Hook: Called after a complete message exchange."""
        self.invoke_hook('on_message_complete', chat_id=chat_id)
