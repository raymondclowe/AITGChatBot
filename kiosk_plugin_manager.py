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
        
        # Plugin command registration
        self.registered_commands: Dict[str, Dict[str, Any]] = {}
        
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
            
            # Register commands from the plugin
            self._register_plugin_commands()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error loading plugin from {plugin_file}: {e}", exc_info=True)
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ⚠️  Failed to load plugin: {e}")
            return False
    
    def _register_plugin_commands(self) -> None:
        """Register commands provided by the plugin."""
        if self.plugin is None:
            return
        
        try:
            commands = self.plugin.get_commands()
            if commands:
                self.registered_commands = commands
                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 🔌 Registered {len(commands)} plugin command(s): {', '.join(['/' + cmd for cmd in commands.keys()])}")
                for cmd_name, cmd_info in commands.items():
                    self.logger.info(f"Registered command: /{cmd_name} - {cmd_info.get('description', 'No description')}")
        except Exception as e:
            self.logger.error(f"Error registering plugin commands: {e}", exc_info=True)
    
    def handle_command(self, command: str, chat_id: str, kiosk_mode: bool, **kwargs) -> Optional[bool]:
        """
        Handle a plugin command.
        
        Args:
            command: The command string (with or without leading /)
            chat_id: The chat/session ID
            kiosk_mode: Whether kiosk mode is active
            **kwargs: Additional context (e.g., send_message_fn, send_document_fn)
        
        Returns:
            True if command was handled, False if not recognized, None if error
        """
        if self.plugin is None or not self.health_monitor.is_healthy():
            return False
        
        # Normalize command (remove leading / if present)
        cmd_name = command.lstrip('/')
        
        # Check if this command is registered
        if cmd_name not in self.registered_commands:
            return False
        
        cmd_info = self.registered_commands[cmd_name]
        
        # Check if command is available in current mode
        if kiosk_mode and not cmd_info.get('available_in_kiosk', True):
            self.logger.warning(f"Command /{cmd_name} not available in kiosk mode")
            return False
        
        # Build context with command-specific additions
        context = self.build_context(chat_id, **kwargs)
        
        try:
            # Get the handler
            handler = cmd_info.get('handler')
            if handler is None:
                self.logger.error(f"No handler found for command /{cmd_name}")
                return None
            
            # Execute the command handler with timeout
            if self.config.timeout > 0:
                @with_timeout(self.config.timeout)
                def timed_handler():
                    return handler(chat_id, context)
                
                result = timed_handler()
            else:
                result = handler(chat_id, context)
            
            # Record success
            self.health_monitor.record_success(f'command_{cmd_name}')
            
            if self.config.debug:
                self.logger.debug(f"Command /{cmd_name} executed successfully")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error executing command /{cmd_name}: {e}", exc_info=True)
            should_disable = self.health_monitor.record_failure(f'command_{cmd_name}')
            if should_disable:
                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ⚠️  Plugin disabled due to repeated failures")
            return None
    
    def get_registered_commands(self, kiosk_mode: bool = False) -> Dict[str, str]:
        """
        Get list of registered commands available in the current mode.
        
        Args:
            kiosk_mode: Whether to filter for kiosk mode availability
        
        Returns:
            Dictionary mapping command names to descriptions
        """
        if not self.registered_commands:
            return {}
        
        result = {}
        for cmd_name, cmd_info in self.registered_commands.items():
            if not kiosk_mode or cmd_info.get('available_in_kiosk', True):
                result[cmd_name] = cmd_info.get('description', 'No description')
        
        return result
    
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
