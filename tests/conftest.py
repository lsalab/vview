"""Pytest configuration and shared fixtures for vview tests."""

import os
import shutil
import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch
import pytest


@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    temp_path = tempfile.mkdtemp()
    yield temp_path
    shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture
def mock_css_folder(temp_dir):
    """Create a mock CSS folder with test files."""
    css_dir = os.path.join(temp_dir, 'css')
    os.makedirs(css_dir, exist_ok=True)
    css_file = os.path.join(css_dir, 'bootstrap.min.css')
    with open(css_file, 'w') as f:
        f.write('/* mock css */')
    return css_dir


@pytest.fixture
def mock_js_folder(temp_dir):
    """Create a mock JS folder with test files."""
    js_dir = os.path.join(temp_dir, 'js')
    os.makedirs(js_dir, exist_ok=True)
    js_file = os.path.join(js_dir, 'bootstrap.bundle.min.js')
    with open(js_file, 'w') as f:
        f.write('// mock js')
    return js_dir


@pytest.fixture
def mock_vid_folder(temp_dir):
    """Create a mock video folder."""
    vid_dir = os.path.join(temp_dir, 'vid')
    os.makedirs(vid_dir, exist_ok=True)
    return vid_dir


@pytest.fixture
def mock_db_path(temp_dir):
    """Create a path for a temporary database."""
    return os.path.join(temp_dir, 'test_metadata.sqlite')


@pytest.fixture
def mock_av_container():
    """Mock PyAV container and video stream."""
    from unittest.mock import MagicMock
    
    # Mock video stream
    mock_stream = MagicMock()
    mock_stream.width = 1920
    mock_stream.height = 1080
    mock_stream.average_rate = 30.0
    mock_stream.time_base = MagicMock()
    mock_stream.duration = None
    
    # Mock frame
    mock_frame = MagicMock()
    mock_frame.time = 60.0
    mock_img = MagicMock()
    mock_frame.to_image.return_value = mock_img
    
    # Mock container
    mock_container = MagicMock()
    mock_container.streams.video = [mock_stream]
    mock_container.duration = None
    mock_container.seek = MagicMock()
    mock_container.decode.return_value = iter([mock_frame])
    mock_container.close = MagicMock()
    
    return mock_container


@pytest.fixture
def mock_av_open(mock_av_container):
    """Mock PyAV's av.open() function."""
    from unittest.mock import patch
    with patch('av.open', return_value=mock_av_container) as mock_open:
        yield mock_open


@pytest.fixture
def sample_video_files(mock_vid_folder):
    """Create sample video files in the mock video folder."""
    files = ['test1.mp4', 'test2.mp4', 'other.txt']
    for fname in files:
        filepath = os.path.join(mock_vid_folder, fname)
        with open(filepath, 'w') as f:
            f.write('mock video content')
    return files

