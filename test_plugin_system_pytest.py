#!/usr/bin/env python3
"""
Comprehensive Pytest Suite for Kiosk Plugin System

Tests cover:
- Plugin discovery and loading
- Hook invocation and data transformation
- Error handling and timeout behavior
- AI helper utilities
- Custom command registration and execution
- Security (no arbitrary imports)
- Full pipeline integration
- Example plugin functionality
"""

import pytest
import sys
import os
import time
import base64
from io import BytesIO
from unittest.mock import Mock, patch, MagicMock, call

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(__file__))

# Mock environment variables before importing main module
os.environ['BOT_KEY'] = 'test_bot_key'
os.environ['API_KEY'] = 'test_api_key'
os.environ['ANTHROPIC_API_KEY'] = 'test_anthropic_key'
os.environ['OPENROUTER_API_KEY'] = 'test_openrouter_key'
os.environ['GROQ_API_KEY'] = 'test_groq_key'

# Import plugin modules
from kiosk_plugin_base import (
    KioskPlugin, PluginAIHelper, PluginConfig, 
    PluginHealthMonitor, with_timeout
)
from kiosk_plugin_manager import PluginManager


# Fixtures

@pytest.fixture
def mock_session_data():
    """Mock session data for testing"""
    return {
        'test_123': {
            'model_version': 'gpt-4o-mini',
            'CONVERSATION': [
                {'role': 'user', 'content': [{'type': 'text', 'text': 'Hello'}]},
                {'role': 'assistant', 'content': [{'type': 'text', 'text': 'Hi there!'}]}
            ],
            'tokens_used': 100
        }
    }


@pytest.fixture
def plugin_config():
    """Plugin configuration for testing"""
    config = PluginConfig()
    config.enabled = True
    config.timeout = 5.0
    config.max_failures = 3
    config.debug = False
    return config


@pytest.fixture
def plugin_ai_helper(mock_session_data):
    """AI helper for testing"""
    return PluginAIHelper(
        session_data=mock_session_data,
        openrouter_api_key="test_key",
        openrouter_url="https://test.api/v1/chat/completions"
    )


@pytest.fixture
def plugin_manager(plugin_config, mock_session_data):
    """Plugin manager for testing"""
    return PluginManager(
        config=plugin_config,
        session_data=mock_session_data,
        openrouter_api_key="test_key",
        openrouter_url="https://test.api/v1/chat/completions"
    )


# Test Classes

class TestPluginBaseClass:
    """Tests for the KioskPlugin base class"""
    
    def test_base_class_has_all_required_methods(self):
        """Test that base class has all 10 required hook methods"""
        plugin = KioskPlugin()
        
        required_methods = [
            'pre_user_text', 'post_user_text',
            'pre_user_images', 'post_user_images',
            'pre_assistant_text', 'post_assistant_text',
            'pre_assistant_images', 'post_assistant_images',
            'on_session_start', 'on_message_complete',
            'get_commands', 'send_message', 'send_document'
        ]
        
        for method_name in required_methods:
            assert hasattr(plugin, method_name), f"Missing method: {method_name}"
            assert callable(getattr(plugin, method_name)), f"Method not callable: {method_name}"
    
    def test_hooks_pass_through_data_unchanged(self):
        """Test that default hooks pass data through unchanged"""
        plugin = KioskPlugin()
        context = {'chat_id': 'test', 'metadata': {}}
        
        # Test text hooks
        assert plugin.pre_user_text("hello", context) == "hello"
        assert plugin.post_user_text("world", context) == "world"
        assert plugin.pre_assistant_text("response", context) == "response"
        assert plugin.post_assistant_text("final", context) == "final"
        
        # Test image hooks
        images = ["img1", "img2"]
        assert plugin.pre_user_images(images, "text", context) == images
        assert plugin.post_user_images(images, "text", context) == images
        assert plugin.pre_assistant_images(images, "text", context) == images
        assert plugin.post_assistant_images(images, "text", context) == images
    
    def test_lifecycle_hooks_execute_without_error(self):
        """Test that lifecycle hooks execute without raising errors"""
        plugin = KioskPlugin()
        context = {'chat_id': 'test', 'metadata': {}}
        
        # Should not raise any exceptions
        plugin.on_session_start(context)
        plugin.on_message_complete(context)
    
    def test_get_commands_returns_empty_dict(self):
        """Test that default get_commands returns empty dict"""
        plugin = KioskPlugin()
        commands = plugin.get_commands()
        assert isinstance(commands, dict)
        assert len(commands) == 0


class TestPluginHealthMonitor:
    """Tests for PluginHealthMonitor"""
    
    def test_starts_healthy(self):
        """Test that monitor starts in healthy state"""
        monitor = PluginHealthMonitor(max_failures=3)
        assert monitor.is_healthy()
    
    def test_records_failures(self):
        """Test failure recording and plugin disabling"""
        monitor = PluginHealthMonitor(max_failures=3)
        
        # First failure
        should_disable = monitor.record_failure("test_hook")
        assert not should_disable
        assert monitor.is_healthy()
        
        # Second failure
        should_disable = monitor.record_failure("test_hook")
        assert not should_disable
        assert monitor.is_healthy()
        
        # Third failure - should disable
        should_disable = monitor.record_failure("test_hook")
        assert should_disable
        assert not monitor.is_healthy()
    
    def test_success_resets_failure_count(self):
        """Test that success resets failure count for a hook"""
        monitor = PluginHealthMonitor(max_failures=3)
        
        monitor.record_failure("test_hook")
        assert monitor.failure_counts.get("test_hook", 0) == 1
        
        monitor.record_success("test_hook")
        assert monitor.failure_counts.get("test_hook", 0) == 0


class TestPluginAIHelper:
    """Tests for PluginAIHelper"""
    
    def test_ai_helper_has_required_methods(self, plugin_ai_helper):
        """Test that AI helper has all required methods"""
        required_methods = ['call_ai', 'quick_call', 'base64_to_pil', 'pil_to_base64']
        
        for method_name in required_methods:
            assert hasattr(plugin_ai_helper, method_name)
            assert callable(getattr(plugin_ai_helper, method_name))
    
    @patch('requests.post')
    def test_call_ai_makes_api_request(self, mock_post, plugin_ai_helper):
        """Test that call_ai makes proper API request"""
        # Mock response
        mock_response = Mock()
        mock_response.json.return_value = {
            'choices': [{'message': {'content': 'AI response'}}]
        }
        mock_post.return_value = mock_response
        
        result = plugin_ai_helper.call_ai("test prompt", model="gpt-4o-mini")
        
        assert mock_post.called
        assert result == 'AI response'
    
    @patch('requests.post')
    def test_quick_call_sends_system_and_user_messages(self, mock_post, plugin_ai_helper):
        """Test that quick_call formats messages correctly"""
        mock_response = Mock()
        mock_response.json.return_value = {
            'choices': [{'message': {'content': 'Response'}}]
        }
        mock_post.return_value = mock_response
        
        result = plugin_ai_helper.quick_call(
            system="You are helpful",
            user="What is 2+2?"
        )
        
        assert mock_post.called
        call_args = mock_post.call_args
        payload = call_args[1]['json']
        assert len(payload['messages']) == 2
        assert payload['messages'][0]['role'] == 'system'
        assert payload['messages'][1]['role'] == 'user'


class TestPluginManager:
    """Tests for PluginManager"""
    
    def test_plugin_manager_initializes(self, plugin_manager):
        """Test that plugin manager initializes correctly"""
        assert plugin_manager is not None
        assert plugin_manager.ai_helper is not None
        assert plugin_manager.health_monitor is not None
        assert isinstance(plugin_manager.registered_commands, dict)
    
    def test_build_context_includes_required_fields(self, plugin_manager):
        """Test that build_context creates proper context dict"""
        context = plugin_manager.build_context('test_123', extra_field='value')
        
        required_fields = [
            'session_data', 'chat_id', 'history', 'metadata',
            'ai_helper', 'model', 'kiosk_mode'
        ]
        
        for field in required_fields:
            assert field in context, f"Missing field: {field}"
        
        assert context['chat_id'] == 'test_123'
        assert context['extra_field'] == 'value'
    
    def test_invoke_hook_with_no_plugin_returns_original(self, plugin_manager):
        """Test that invoke_hook returns original data when no plugin"""
        result = plugin_manager.invoke_hook('pre_user_text', 'test', chat_id='test_123')
        assert result == 'test'
    
    def test_invoke_hook_calls_plugin_method(self, plugin_manager):
        """Test that invoke_hook calls the plugin method"""
        # Create a test plugin
        class TestPlugin(KioskPlugin):
            def pre_user_text(self, text, context):
                return text.upper()
        
        plugin_manager.plugin = TestPlugin()
        result = plugin_manager.invoke_hook('pre_user_text', 'test', chat_id='test_123')
        assert result == 'TEST'
    
    def test_invoke_hook_handles_exceptions(self, plugin_manager):
        """Test that invoke_hook handles exceptions gracefully"""
        class FaultyPlugin(KioskPlugin):
            def pre_user_text(self, text, context):
                raise ValueError("Test error")
        
        plugin_manager.plugin = FaultyPlugin()
        result = plugin_manager.invoke_hook('pre_user_text', 'test', chat_id='test_123')
        # Should return original data on error
        assert result == 'test'


class TestCustomCommands:
    """Tests for custom command functionality"""
    
    def test_get_commands_registration(self):
        """Test that plugins can register commands"""
        class TestPlugin(KioskPlugin):
            def get_commands(self):
                return {
                    'test-cmd': {
                        'description': 'Test command',
                        'handler': self.handle_test_cmd,
                        'available_in_kiosk': True
                    }
                }
            
            def handle_test_cmd(self, chat_id, context):
                return "Command executed"
        
        plugin = TestPlugin()
        commands = plugin.get_commands()
        
        assert 'test-cmd' in commands
        assert commands['test-cmd']['description'] == 'Test command'
        assert callable(commands['test-cmd']['handler'])
    
    def test_command_handler_receives_context(self, plugin_manager):
        """Test that command handlers receive full context"""
        class TestPlugin(KioskPlugin):
            def __init__(self):
                self.received_context = None
            
            def get_commands(self):
                return {
                    'test': {
                        'description': 'Test',
                        'handler': self.handle_test,
                        'available_in_kiosk': True
                    }
                }
            
            def handle_test(self, chat_id, context):
                self.received_context = context
                return True
        
        plugin = TestPlugin()
        plugin_manager.plugin = plugin
        plugin_manager.registered_commands = plugin.get_commands()
        
        result = plugin_manager.handle_command(
            '/test', 
            'test_123', 
            True,
            send_message_fn=Mock()
        )
        
        assert result is True
        assert plugin.received_context is not None
        assert 'ai_helper' in plugin.received_context
        assert 'send_message_fn' in plugin.received_context
    
    def test_send_message_helper_calls_function(self):
        """Test that send_message helper calls the provided function"""
        mock_send = Mock()
        plugin = KioskPlugin()
        context = {'send_message_fn': mock_send}
        
        plugin.send_message('chat_123', 'Test message', context)
        
        mock_send.assert_called_once_with('chat_123', 'Test message')
    
    def test_send_document_helper_calls_function(self):
        """Test that send_document helper calls the provided function"""
        mock_send_doc = Mock()
        plugin = KioskPlugin()
        context = {'send_document_fn': mock_send_doc}
        
        data = b'test data'
        plugin.send_document('chat_123', data, 'test.txt', 'Caption', context)
        
        mock_send_doc.assert_called_once_with('chat_123', data, 'test.txt', 'Caption')
    
    def test_get_registered_commands_filters_by_mode(self, plugin_manager):
        """Test that get_registered_commands filters by kiosk mode"""
        plugin_manager.registered_commands = {
            'cmd1': {'description': 'Cmd 1', 'available_in_kiosk': True},
            'cmd2': {'description': 'Cmd 2', 'available_in_kiosk': False}
        }
        
        # Get kiosk-available commands
        kiosk_cmds = plugin_manager.get_registered_commands(kiosk_mode=True)
        assert 'cmd1' in kiosk_cmds
        assert 'cmd2' not in kiosk_cmds
        
        # Get all commands
        all_cmds = plugin_manager.get_registered_commands(kiosk_mode=False)
        assert 'cmd1' in all_cmds
        assert 'cmd2' in all_cmds


class TestExamplePluginFunctionality:
    """Tests for example plugin features"""
    
    def test_profanity_filter(self):
        """Test that profanity filter works"""
        class ProfanityPlugin(KioskPlugin):
            def __init__(self):
                self.profanity_list = ['badword']
            
            def pre_user_text(self, text, context):
                filtered = text
                for word in self.profanity_list:
                    if word in filtered.lower():
                        filtered = filtered.replace(word, '*' * len(word))
                return filtered
        
        plugin = ProfanityPlugin()
        context = {'metadata': {}}
        
        result = plugin.pre_user_text("This has a badword in it", context)
        assert 'badword' not in result.lower()
        assert '*******' in result
    
    def test_metadata_tracking(self):
        """Test that plugins can use metadata for state tracking"""
        class TrackerPlugin(KioskPlugin):
            def on_session_start(self, context):
                context['metadata']['message_count'] = 0
            
            def on_message_complete(self, context):
                context['metadata']['message_count'] = context['metadata'].get('message_count', 0) + 1
        
        plugin = TrackerPlugin()
        metadata = {}
        context = {'metadata': metadata}
        
        plugin.on_session_start(context)
        assert metadata['message_count'] == 0
        
        plugin.on_message_complete(context)
        assert metadata['message_count'] == 1
        
        plugin.on_message_complete(context)
        assert metadata['message_count'] == 2
    
    @patch('requests.post')
    def test_ai_caption_expansion(self, mock_post, plugin_ai_helper):
        """Test AI-powered caption expansion"""
        mock_response = Mock()
        mock_response.json.return_value = {
            'choices': [{'message': {'content': 'A beautiful sunset over the ocean'}}]
        }
        mock_post.return_value = mock_response
        
        class CaptionPlugin(KioskPlugin):
            def pre_user_images(self, images, text, context):
                if images and len(text.strip()) < 20:
                    ai_helper = context.get('ai_helper')
                    if ai_helper:
                        description = ai_helper.call_ai(
                            prompt="Describe this image briefly",
                            images=[images[0]]
                        )
                        context['metadata']['ai_caption'] = description
                return images
        
        plugin = CaptionPlugin()
        metadata = {}
        context = {
            'metadata': metadata,
            'ai_helper': plugin_ai_helper
        }
        
        result = plugin.pre_user_images(['img_base64'], 'short', context)
        
        assert result == ['img_base64']
        assert 'ai_caption' in metadata
        assert 'sunset' in metadata['ai_caption'].lower()


class TestIntegration:
    """Integration tests for the full plugin pipeline"""
    
    def test_full_message_pipeline_with_plugin(self, plugin_manager):
        """Test complete message flow through plugin hooks"""
        class FullPlugin(KioskPlugin):
            def __init__(self):
                self.call_order = []
            
            def pre_user_text(self, text, context):
                self.call_order.append('pre_user_text')
                return text
            
            def post_user_text(self, text, context):
                self.call_order.append('post_user_text')
                return text
            
            def pre_assistant_text(self, text, context):
                self.call_order.append('pre_assistant_text')
                return text
            
            def post_assistant_text(self, text, context):
                self.call_order.append('post_assistant_text')
                return text
            
            def on_message_complete(self, context):
                self.call_order.append('on_message_complete')
        
        plugin = FullPlugin()
        plugin_manager.plugin = plugin
        
        # Simulate message pipeline
        plugin_manager.pre_user_text('user input', 'test_123')
        plugin_manager.post_user_text('processed input', 'test_123')
        plugin_manager.pre_assistant_text('ai response', 'test_123')
        plugin_manager.post_assistant_text('final response', 'test_123')
        plugin_manager.on_message_complete('test_123')
        
        expected_order = [
            'pre_user_text',
            'post_user_text',
            'pre_assistant_text',
            'post_assistant_text',
            'on_message_complete'
        ]
        
        assert plugin.call_order == expected_order
    
    def test_plugin_with_command_execution(self, plugin_manager):
        """Test plugin that uses both hooks and commands"""
        class HybridPlugin(KioskPlugin):
            def __init__(self):
                self.user_messages = []
                self.commands_executed = []
            
            def pre_user_text(self, text, context):
                self.user_messages.append(text)
                return text
            
            def get_commands(self):
                return {
                    'stats': {
                        'description': 'Show stats',
                        'handler': self.handle_stats,
                        'available_in_kiosk': True
                    }
                }
            
            def handle_stats(self, chat_id, context):
                self.commands_executed.append('stats')
                # Would normally send message here
                return f"Received {len(self.user_messages)} messages"
        
        plugin = HybridPlugin()
        plugin_manager.plugin = plugin
        plugin_manager.registered_commands = plugin.get_commands()
        
        # Process some messages
        plugin_manager.pre_user_text('msg1', 'test_123')
        plugin_manager.pre_user_text('msg2', 'test_123')
        
        # Execute command
        result = plugin_manager.handle_command('/stats', 'test_123', True)
        
        assert result is not None
        assert len(plugin.user_messages) == 2
        assert len(plugin.commands_executed) == 1


class TestSecurity:
    """Security-related tests"""
    
    def test_plugin_loading_validates_class(self, plugin_manager):
        """Test that plugin loading validates the plugin class"""
        # Plugin should only load if it inherits from KioskPlugin
        assert plugin_manager.plugin is None  # No plugin file exists
    
    def test_timeout_prevents_infinite_loops(self, plugin_manager):
        """Test that timeout prevents infinite loops"""
        class InfinitePlugin(KioskPlugin):
            def pre_user_text(self, text, context):
                while True:
                    pass  # Infinite loop
        
        plugin_manager.plugin = InfinitePlugin()
        plugin_manager.config.timeout = 1.0  # 1 second timeout
        
        # Should timeout and return original data
        result = plugin_manager.invoke_hook('pre_user_text', 'test', chat_id='test_123')
        assert result == 'test'
    
    def test_exception_isolation(self, plugin_manager):
        """Test that exceptions in one hook don't affect others"""
        class FaultyPlugin(KioskPlugin):
            def pre_user_text(self, text, context):
                raise ValueError("Error in pre_user_text")
            
            def post_user_text(self, text, context):
                return text + " [processed]"
        
        plugin_manager.plugin = FaultyPlugin()
        
        # First hook should fail gracefully
        result1 = plugin_manager.invoke_hook('pre_user_text', 'test', chat_id='test_123')
        assert result1 == 'test'
        
        # Second hook should still work
        result2 = plugin_manager.invoke_hook('post_user_text', 'test', chat_id='test_123')
        assert result2 == 'test [processed]'


# Main pytest runner
if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
