"""Tests for utility functions in main.py."""

import sys
from io import StringIO
from unittest.mock import patch, MagicMock
import pytest

# Import the function to test
sys.path.insert(0, '/home/lsalab/.prn/vview')
from main import perr


class TestPerr:
    """Tests for the perr() utility function."""

    def test_perr_writes_to_stderr(self):
        """Test that perr writes messages to stderr."""
        test_message = "Test error message"
        mock_stderr = StringIO()
        with patch('main.stderr', mock_stderr):
            perr(test_message)
            assert test_message in mock_stderr.getvalue()

    def test_perr_strips_newlines(self):
        """Test that perr strips newlines from input."""
        test_message = "Test message\nwith\r\nnewlines"
        mock_stderr = StringIO()
        with patch('main.stderr', mock_stderr):
            perr(test_message)
            output = mock_stderr.getvalue()
            # Should not contain the original newlines, but should have one at the end
            assert '\r\n' in output
            assert test_message.strip('\r\n') in output

    def test_perr_adds_newline(self):
        """Test that perr adds a newline at the end."""
        test_message = "Test message"
        mock_stderr = StringIO()
        with patch('main.stderr', mock_stderr):
            perr(test_message)
            output = mock_stderr.getvalue()
            assert output.endswith('\r\n')

    def test_perr_flushes_stderr(self):
        """Test that perr flushes stderr."""
        mock_stderr = MagicMock()
        with patch('main.stderr', mock_stderr):
            perr("Test message")
            mock_stderr.flush.assert_called_once()

