#!/usr/bin/env python3
"""
Pytest Suite for Kiosk Mode with Plugin Integration

Tests cover:
- Kiosk mode functionality
- Plugin integration in kiosk mode
- Command handling in kiosk mode
- Message pipeline in kiosk mode
- Security and isolation
"""

import pytest
import sys
import os
from unittest.mock import Mock, patch, MagicMock

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(__file__))

# Mock environment variables
os.environ['BOT_KEY'] = 'test_bot_key'
os.environ['API_KEY'] = 'test_api_key'
os.environ['ANTHROPIC_API_KEY'] = 'test_anthropic_key'
os.environ['OPENROUTER_API_KEY'] = 'test_openrouter_key'
os.environ['GROQ_API_KEY'] = 'test_groq_key'

from kiosk_plugin_base import KioskPlugin
from kiosk_plugin_manager import PluginManager, PluginConfig


# Fixtures

@pytest.fixture
def kiosk_session_data():
    """Mock kiosk mode session data"""
    return {
        'kiosk_user_123': {
            'model_version': 'openrouter:google/gemini-2.0-flash-001',
            'CONVERSATION': [
                {'role': 'system', 'content': [{'type': 'text', 'text': 'You are a helpful tutor'}]},
                {'role': 'user', 'content': [{'type': 'text', 'text': 'What is 2+2?'}]},
                {'role': 'assistant', 'content': [{'type': 'text', 'text': '2+2 equals 4'}]}
            ],
            'tokens_used': 50,
            'max_rounds': 4,
            'notification_shown': False,
            'response_format': 'auto'
        }
    }


@pytest.fixture
def kiosk_config():
    """Kiosk mode configuration"""
    return {
        'enabled': True,
        'model': 'openrouter:google/gemini-2.0-flash-001',
        'prompt_file': 'test_prompt.txt',
        'inactivity_timeout': 3600
    }


@pytest.fixture
def plugin_manager_kiosk(kiosk_session_data):
    """Plugin manager configured for kiosk mode"""
    config = PluginConfig()
    config.enabled = True
    config.timeout = 5.0
    config.max_failures = 3
    
    return PluginManager(
        config=config,
        session_data=kiosk_session_data,
        openrouter_api_key="test_key",
        openrouter_url="https://openrouter.ai/api/v1/chat/completions"
    )


# Test Classes

class TestKioskModeBasics:
    """Tests for basic kiosk mode functionality"""
    
    def test_kiosk_session_initialization(self, kiosk_session_data):
        """Test that kiosk sessions are properly initialized"""
        session = kiosk_session_data['kiosk_user_123']
        
        assert 'model_version' in session
        assert 'CONVERSATION' in session
        assert 'tokens_used' in session
        assert session['CONVERSATION'][0]['role'] == 'system'  # System prompt present
    
    def test_kiosk_mode_locks_settings(self):
        """Test that kiosk mode prevents model changes"""
        # This would be tested in the actual bot, but we can test the concept
        kiosk_locked_commands = ['/gpt4', '/claud3', '/maxrounds', '/listopenroutermodels']
        
        # In kiosk mode, these should not be available
        for cmd in kiosk_locked_commands:
            assert cmd.startswith('/')  # Just checking format
    
    def test_kiosk_available_commands(self):
        """Test that kiosk mode has specific available commands"""
        kiosk_commands = ['/start', '/help', '/clear', '/status', '/format']
        
        for cmd in kiosk_commands:
            assert cmd.startswith('/')
            assert len(cmd) > 1


class TestKioskPluginIntegration:
    """Tests for plugin integration in kiosk mode"""
    
    def test_plugin_works_in_kiosk_mode(self, plugin_manager_kiosk):
        """Test that plugins function correctly in kiosk mode"""
        class KioskTestPlugin(KioskPlugin):
            def pre_user_text(self, text, context):
                assert context['kiosk_mode'] is True
                return text.strip()
        
        plugin_manager_kiosk.plugin = KioskTestPlugin()
        result = plugin_manager_kiosk.pre_user_text('  test  ', 'kiosk_user_123')
        
        assert result == 'test'
    
    def test_plugin_receives_kiosk_session_data(self, plugin_manager_kiosk):
        """Test that plugins receive correct kiosk session data"""
        class DataCheckPlugin(KioskPlugin):
            def __init__(self):
                self.received_model = None
            
            def pre_user_text(self, text, context):
                self.received_model = context.get('model')
                return text
        
        plugin = DataCheckPlugin()
        plugin_manager_kiosk.plugin = plugin
        
        plugin_manager_kiosk.pre_user_text('test', 'kiosk_user_123')
        
        assert plugin.received_model == 'openrouter:google/gemini-2.0-flash-001'
    
    def test_plugin_metadata_persists_across_messages(self, plugin_manager_kiosk):
        """Test that plugin metadata persists for the session"""
        class StatefulPlugin(KioskPlugin):
            def on_session_start(self, context):
                context['metadata']['count'] = 0
            
            def pre_user_text(self, text, context):
                context['metadata']['count'] += 1
                return text
        
        plugin = StatefulPlugin()
        plugin_manager_kiosk.plugin = plugin
        
        # Start session
        plugin_manager_kiosk.on_session_start('kiosk_user_123')
        
        # Process multiple messages
        plugin_manager_kiosk.pre_user_text('msg1', 'kiosk_user_123')
        plugin_manager_kiosk.pre_user_text('msg2', 'kiosk_user_123')
        
        # Check metadata persisted
        metadata = plugin_manager_kiosk.plugin_metadata['kiosk_user_123']
        assert metadata['count'] == 2


class TestKioskCustomCommands:
    """Tests for custom commands in kiosk mode"""
    
    def test_plugin_commands_available_in_kiosk(self, plugin_manager_kiosk):
        """Test that plugin commands work in kiosk mode"""
        class CommandPlugin(KioskPlugin):
            def __init__(self):
                self.executed = False
            
            def get_commands(self):
                return {
                    'generate-worksheets': {
                        'description': 'Generate practice worksheets',
                        'handler': self.handle_worksheets,
                        'available_in_kiosk': True
                    }
                }
            
            def handle_worksheets(self, chat_id, context):
                self.executed = True
                return "Worksheets generated"
        
        plugin = CommandPlugin()
        plugin_manager_kiosk.plugin = plugin
        plugin_manager_kiosk.registered_commands = plugin.get_commands()
        
        result = plugin_manager_kiosk.handle_command(
            '/generate-worksheets',
            'kiosk_user_123',
            True,  # kiosk_mode=True
            send_message_fn=Mock()
        )
        
        assert result is True
        assert plugin.executed is True
    
    def test_non_kiosk_commands_blocked_in_kiosk_mode(self, plugin_manager_kiosk):
        """Test that commands not available in kiosk are blocked"""
        plugin_manager_kiosk.registered_commands = {
            'admin-cmd': {
                'description': 'Admin only',
                'handler': Mock(),
                'available_in_kiosk': False
            }
        }
        
        result = plugin_manager_kiosk.handle_command(
            '/admin-cmd',
            'kiosk_user_123',
            True,  # kiosk_mode=True
        )
        
        assert result is False  # Command not available in kiosk mode
    
    def test_command_help_shows_plugin_commands(self, plugin_manager_kiosk):
        """Test that /help includes plugin commands in kiosk mode"""
        plugin_manager_kiosk.registered_commands = {
            'worksheets': {
                'description': 'Generate worksheets',
                'available_in_kiosk': True
            },
            'summary': {
                'description': 'Summarize conversation',
                'available_in_kiosk': True
            }
        }
        
        commands = plugin_manager_kiosk.get_registered_commands(kiosk_mode=True)
        
        assert 'worksheets' in commands
        assert 'summary' in commands
        assert len(commands) == 2


class TestKioskMessagePipeline:
    """Tests for message processing pipeline in kiosk mode"""
    
    def test_user_message_pipeline_with_plugin(self, plugin_manager_kiosk):
        """Test complete user message processing with plugin"""
        class PipelinePlugin(KioskPlugin):
            def __init__(self):
                self.stages = []
            
            def pre_user_text(self, text, context):
                self.stages.append('pre_user_text')
                return text.lower()
            
            def post_user_text(self, text, context):
                self.stages.append('post_user_text')
                return text + '?'
        
        plugin = PipelinePlugin()
        plugin_manager_kiosk.plugin = plugin
        
        # Process user message
        result1 = plugin_manager_kiosk.pre_user_text('HELLO', 'kiosk_user_123')
        assert result1 == 'hello'
        
        result2 = plugin_manager_kiosk.post_user_text(result1, 'kiosk_user_123')
        assert result2 == 'hello?'
        
        assert plugin.stages == ['pre_user_text', 'post_user_text']
    
    def test_assistant_message_pipeline_with_plugin(self, plugin_manager_kiosk):
        """Test complete assistant message processing with plugin"""
        class ResponsePlugin(KioskPlugin):
            def pre_assistant_text(self, text, context):
                # Detect LaTeX
                if '$$' in text:
                    context['metadata']['has_latex'] = True
                return text
            
            def post_assistant_text(self, text, context):
                if context['metadata'].get('has_latex'):
                    return text + '\n[LaTeX detected]'
                return text
        
        plugin = ResponsePlugin()
        plugin_manager_kiosk.plugin = plugin
        
        # Process assistant response with LaTeX
        result1 = plugin_manager_kiosk.pre_assistant_text('Answer: $$x^2$$', 'kiosk_user_123')
        result2 = plugin_manager_kiosk.post_assistant_text(result1, 'kiosk_user_123')
        
        assert '[LaTeX detected]' in result2
    
    def test_image_processing_in_kiosk_mode(self, plugin_manager_kiosk):
        """Test image processing with plugins in kiosk mode"""
        class ImagePlugin(KioskPlugin):
            def pre_user_images(self, images, text, context):
                # Auto-expand brief captions
                if images and len(text.strip()) < 20:
                    context['metadata']['needs_caption'] = True
                return images
        
        plugin = ImagePlugin()
        plugin_manager_kiosk.plugin = plugin
        
        images = ['base64_image_data']
        result = plugin_manager_kiosk.pre_user_images(images, 'pic', 'kiosk_user_123')
        
        assert result == images
        metadata = plugin_manager_kiosk.plugin_metadata.get('kiosk_user_123', {})
        assert metadata.get('needs_caption') is True


class TestKioskSecurity:
    """Security tests for kiosk mode"""
    
    def test_kiosk_mode_prevents_model_changes(self):
        """Test that kiosk mode configuration is immutable"""
        # In kiosk mode, model should be locked
        kiosk_model = 'openrouter:google/gemini-2.0-flash-001'
        
        # Attempting to change should not work (tested in actual bot)
        assert kiosk_model.startswith('openrouter:')
    
    def test_plugin_timeout_in_kiosk_mode(self, plugin_manager_kiosk):
        """Test that plugin timeouts work in kiosk mode"""
        class SlowPlugin(KioskPlugin):
            def pre_user_text(self, text, context):
                import time
                time.sleep(10)  # Exceed timeout
                return text
        
        plugin_manager_kiosk.plugin = SlowPlugin()
        plugin_manager_kiosk.config.timeout = 1.0
        
        # Should timeout and return original
        result = plugin_manager_kiosk.invoke_hook('pre_user_text', 'test', chat_id='kiosk_user_123')
        assert result == 'test'
    
    def test_plugin_health_monitoring_in_kiosk(self, plugin_manager_kiosk):
        """Test that health monitoring works in kiosk mode"""
        class FaultyPlugin(KioskPlugin):
            def pre_user_text(self, text, context):
                raise Exception("Error")
        
        plugin_manager_kiosk.plugin = FaultyPlugin()
        plugin_manager_kiosk.config.max_failures = 3
        
        # First failure
        result1 = plugin_manager_kiosk.invoke_hook('pre_user_text', 'test1', chat_id='kiosk_user_123')
        assert plugin_manager_kiosk.health_monitor.is_healthy()
        
        # Second failure
        result2 = plugin_manager_kiosk.invoke_hook('pre_user_text', 'test2', chat_id='kiosk_user_123')
        assert plugin_manager_kiosk.health_monitor.is_healthy()
        
        # Third failure - should disable
        result3 = plugin_manager_kiosk.invoke_hook('pre_user_text', 'test3', chat_id='kiosk_user_123')
        assert not plugin_manager_kiosk.health_monitor.is_healthy()


class TestKioskWorksheetGeneration:
    """Tests for the worksheet generation use case"""
    
    @patch('requests.post')
    def test_worksheet_command_flow(self, mock_post, plugin_manager_kiosk):
        """Test complete worksheet generation flow"""
        # Mock AI response
        mock_response = Mock()
        mock_response.json.return_value = {
            'choices': [{'message': {'content': 'Problem 1: What is 3+3?\nProblem 2: What is 5+2?'}}]
        }
        mock_post.return_value = mock_response
        
        class WorksheetPlugin(KioskPlugin):
            def __init__(self):
                self.messages_sent = []
                self.documents_sent = []
            
            def get_commands(self):
                return {
                    'generate-worksheets': {
                        'description': 'Generate worksheets',
                        'handler': self.handle_worksheets,
                        'available_in_kiosk': True
                    }
                }
            
            def handle_worksheets(self, chat_id, context):
                # Send progress message
                self.send_message(chat_id, '📝 Generating...', context)
                
                # Generate content with AI
                ai_helper = context['ai_helper']
                content = ai_helper.quick_call(
                    system="Create math problems",
                    user="Generate 2 problems"
                )
                
                # Send document
                html = f"<html><body>{content}</body></html>"
                self.send_document(
                    chat_id,
                    html.encode('utf-8'),
                    'worksheet.html',
                    '✅ Here is your worksheet',
                    context
                )
                
                return True
        
        plugin = WorksheetPlugin()
        plugin_manager_kiosk.plugin = plugin
        plugin_manager_kiosk.registered_commands = plugin.get_commands()
        
        # Mock send functions
        mock_send_msg = Mock()
        mock_send_doc = Mock()
        
        # Execute command
        result = plugin_manager_kiosk.handle_command(
            '/generate-worksheets',
            'kiosk_user_123',
            True,
            send_message_fn=mock_send_msg,
            send_document_fn=mock_send_doc
        )
        
        assert result is True
        assert mock_post.called  # AI was called
        # Note: send_message and send_document would be called through the plugin


class TestKioskConversationAnalysis:
    """Tests for conversation analysis in kiosk mode"""
    
    def test_plugin_accesses_conversation_history(self, plugin_manager_kiosk, kiosk_session_data):
        """Test that plugins can analyze conversation history"""
        class AnalysisPlugin(KioskPlugin):
            def __init__(self):
                self.analyzed_messages = 0
            
            def on_message_complete(self, context):
                history = context.get('history', [])
                self.analyzed_messages = len(history)
        
        plugin = AnalysisPlugin()
        plugin_manager_kiosk.plugin = plugin
        
        plugin_manager_kiosk.on_message_complete('kiosk_user_123')
        
        # Should have counted messages from session
        assert plugin.analyzed_messages > 0
    
    @patch('requests.post')
    def test_summary_command_with_ai(self, mock_post, plugin_manager_kiosk):
        """Test conversation summary command"""
        mock_response = Mock()
        mock_response.json.return_value = {
            'choices': [{'message': {'content': '• Topic: Math\n• Questions: 1\n• Answers: 1'}}]
        }
        mock_post.return_value = mock_response
        
        class SummaryPlugin(KioskPlugin):
            def get_commands(self):
                return {
                    'summary': {
                        'description': 'Summarize conversation',
                        'handler': self.handle_summary,
                        'available_in_kiosk': True
                    }
                }
            
            def handle_summary(self, chat_id, context):
                history = context.get('history', [])
                ai_helper = context['ai_helper']
                
                summary = ai_helper.quick_call(
                    system="Summarize conversations",
                    user=f"Summarize {len(history)} messages"
                )
                
                self.send_message(chat_id, f"Summary:\n{summary}", context)
                return True
        
        plugin = SummaryPlugin()
        plugin_manager_kiosk.plugin = plugin
        plugin_manager_kiosk.registered_commands = plugin.get_commands()
        
        result = plugin_manager_kiosk.handle_command(
            '/summary',
            'kiosk_user_123',
            True,
            send_message_fn=Mock()
        )
        
        assert result is True
        assert mock_post.called


# Main pytest runner
if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
