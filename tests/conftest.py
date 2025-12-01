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
def mock_ffmpeg_probe():
    """Mock ffmpeg.probe response."""
    return {
        'streams': [
            {
                'codec_type': 'video',
                'width': '1920',
                'height': '1080',
                'r_frame_rate': '30/1'
            }
        ]
    }


@pytest.fixture
def mock_ffmpeg_output():
    """Mock ffmpeg output (raw frame data)."""
    # Create a mock RGB24 frame (1920x1080x3 bytes)
    width, height = 1920, 1080
    frame_size = width * height * 3
    return (b'\x00' * frame_size, b'')


@pytest.fixture
def sample_video_files(mock_vid_folder):
    """Create sample video files in the mock video folder."""
    files = ['test1.mp4', 'test2.mp4', 'other.txt']
    for fname in files:
        filepath = os.path.join(mock_vid_folder, fname)
        with open(filepath, 'w') as f:
            f.write('mock video content')
    return files

