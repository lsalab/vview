"""Tests for the Viewer class and main functionality."""

import os
import sqlite3
from unittest.mock import MagicMock, Mock, patch, mock_open
import pytest

from main import Viewer, THUMBNAIL_DB, THUMBNAIL_HEIGHT, THUMBNAIL_TIME


class TestViewerInit:
    """Tests for Viewer.__init__ method."""

    @patch('main.connect')
    @patch('main.listdir')
    @patch('main.abspath')
    @patch('main.basename')
    @patch('builtins.open', new_callable=mock_open, read_data=b'test content')
    @patch('main.SHA384')
    def test_init_creates_hashes_for_css_js(
        self, mock_sha384, mock_file, mock_basename, mock_abspath, 
        mock_listdir, mock_connect
    ):
        """Test that __init__ creates hashes for CSS and JS files."""
        # Setup mocks
        mock_listdir.side_effect = lambda x: ['bootstrap.min.css'] if 'css' in x else ['bootstrap.bundle.min.js']
        mock_abspath.side_effect = lambda x: x
        mock_basename.side_effect = lambda x: os.path.basename(x)
        
        mock_hash = MagicMock()
        mock_hash.digest.return_value = b'test_digest'
        mock_sha384.new.return_value = mock_hash
        
        mock_con = MagicMock()
        mock_cur = MagicMock()
        mock_cur.execute.return_value.fetchall.return_value = []
        mock_con.cursor.return_value = mock_cur
        mock_connect.return_value.__enter__.return_value = mock_con
        
        with patch.object(Viewer, '_update_thumbnails'):
            viewer = Viewer()
            assert 'css' in viewer.hashes
            assert 'js' in viewer.hashes

    @patch('main.connect')
    @patch('main.listdir')
    @patch('main.abspath')
    @patch('main.basename')
    @patch('builtins.open', new_callable=mock_open, read_data=b'test content')
    @patch('main.SHA384')
    def test_init_creates_database_table_if_not_exists(
        self, mock_sha384, mock_file, mock_basename, mock_abspath,
        mock_listdir, mock_connect
    ):
        """Test that __init__ creates the thumbnails table if it doesn't exist."""
        # Setup mocks
        mock_listdir.side_effect = lambda x: ['bootstrap.min.css'] if 'css' in x else ['bootstrap.bundle.min.js']
        mock_abspath.side_effect = lambda x: x
        mock_basename.side_effect = lambda x: os.path.basename(x)
        
        mock_hash = MagicMock()
        mock_hash.digest.return_value = b'test_digest'
        mock_sha384.new.return_value = mock_hash
        
        mock_con = MagicMock()
        mock_cur = MagicMock()
        # First call: check for table existence (returns empty)
        # Second call: create table
        mock_cur.execute.return_value.fetchall.return_value = []
        mock_con.cursor.return_value = mock_cur
        mock_connect.return_value.__enter__.return_value = mock_con
        
        with patch.object(Viewer, '_update_thumbnails'):
            viewer = Viewer()
            # Verify that execute was called (for table creation check)
            assert mock_cur.execute.called


class TestUpdateThumbnails:
    """Tests for Viewer._update_thumbnails method."""

    @patch('main.ffmpeg')
    @patch('main.Image')
    @patch('main.BytesIO')
    @patch('main.connect')
    @patch('main.listdir')
    @patch('main.abspath')
    @patch('main.basename')
    @patch('builtins.open', new_callable=mock_open, read_data=b'test content')
    @patch('main.SHA384')
    def test_update_thumbnails_removes_deleted_files(
        self, mock_sha384, mock_file, mock_basename, mock_abspath, mock_listdir, mock_connect,
        mock_bytesio, mock_image, mock_ffmpeg
    ):
        """Test that _update_thumbnails removes metadata for deleted files."""
        # Setup basic mocks for Viewer init
        def listdir_side_effect(path):
            if 'css' in path:
                return ['bootstrap.min.css']
            elif 'js' in path:
                return ['bootstrap.bundle.min.js']
            elif 'vid' in path or './vid' in path:
                return ['test1.mp4']  # Only one file exists
            return []
        
        mock_listdir.side_effect = listdir_side_effect
        mock_abspath.side_effect = lambda x: x
        mock_basename.side_effect = lambda x: os.path.basename(x)
        mock_hash = MagicMock()
        mock_hash.digest.return_value = b'test_digest'
        mock_sha384.new.return_value = mock_hash
        
        # Mock ffmpeg to avoid AttributeError
        mock_ffmpeg.probe.return_value = {
            'streams': [{
                'codec_type': 'video',
                'width': '1920',
                'height': '1080',
                'r_frame_rate': '30/1'
            }]
        }
        mock_ffmpeg.input.return_value.filter.return_value.output.return_value.run.return_value = (b'\x00' * (1920 * 1080 * 3), b'')
        
        # Mock BytesIO for image saving
        mock_io = MagicMock()
        mock_io.getbuffer.return_value = b'image_data'
        mock_bytesio.return_value.__enter__.return_value = mock_io
        
        # Mock PIL Image
        mock_img = MagicMock()
        mock_img.resize.return_value = mock_img
        mock_image.frombytes.return_value = mock_img
        
        # Mock for Viewer.__init__ database connection
        mock_con_init = MagicMock()
        mock_cur_init = MagicMock()
        mock_cur_init.execute.return_value.fetchall.return_value = []
        mock_con_init.cursor.return_value = mock_cur_init
        mock_connect.return_value.__enter__.return_value = mock_con_init
        
        viewer = Viewer()
        viewer.hashes = {'css': {}, 'js': {}}
        
        # Mock for _update_thumbnails database connection
        mock_con = MagicMock()
        mock_cur = MagicMock()
        # First call: SELECT file FROM thumbnails (returns deleted.mp4)
        # Second call: DELETE FROM thumbnails
        mock_cur.execute.return_value.fetchall.side_effect = [
            [('deleted.mp4',)],  # Existing metadata
            []  # After deletion
        ]
        mock_con.cursor.return_value = mock_cur
        mock_connect.return_value.__enter__.return_value = mock_con
        
        viewer._update_thumbnails()
        
        # Verify DELETE was called
        delete_calls = [call for call in mock_cur.execute.call_args_list 
                       if 'DELETE' in str(call)]
        assert len(delete_calls) > 0

    @patch('main.ffmpeg')
    @patch('main.Image')
    @patch('main.BytesIO')
    @patch('main.connect')
    @patch('main.listdir')
    @patch('main.abspath')
    @patch('main.basename')
    @patch('builtins.open', new_callable=mock_open, read_data=b'test content')
    @patch('main.SHA384')
    def test_update_thumbnails_creates_metadata_for_new_files(
        self, mock_sha384, mock_file, mock_basename, mock_abspath, mock_listdir, mock_connect,
        mock_bytesio, mock_image, mock_ffmpeg
    ):
        """Test that _update_thumbnails creates metadata for new MP4 files."""
        # Setup basic mocks for Viewer init
        def listdir_side_effect(path):
            if 'css' in path:
                return ['bootstrap.min.css']
            elif 'js' in path:
                return ['bootstrap.bundle.min.js']
            elif 'vid' in path or './vid' in path:
                return ['new_video.mp4']
            return []
        
        mock_listdir.side_effect = listdir_side_effect
        mock_abspath.side_effect = lambda x: x
        mock_basename.side_effect = lambda x: os.path.basename(x)
        mock_hash = MagicMock()
        mock_hash.digest.return_value = b'test_digest'
        mock_sha384.new.return_value = mock_hash
        
        # Mock for Viewer.__init__ database connection
        mock_con_init = MagicMock()
        mock_cur_init = MagicMock()
        mock_cur_init.execute.return_value.fetchall.return_value = []
        mock_con_init.cursor.return_value = mock_cur_init
        mock_connect.return_value.__enter__.return_value = mock_con_init
        
        # Mock ffmpeg probe (needed during Viewer.__init__)
        mock_ffmpeg.probe.return_value = {
            'streams': [{
                'codec_type': 'video',
                'width': '1920',
                'height': '1080',
                'r_frame_rate': '30/1'
            }]
        }
        
        # Mock ffmpeg input/output
        mock_output = MagicMock()
        mock_output.run.return_value = (b'\x00' * (1920 * 1080 * 3), b'')
        mock_ffmpeg.input.return_value.filter.return_value.output.return_value = mock_output
        
        # Mock PIL Image
        mock_img = MagicMock()
        mock_img.resize.return_value = mock_img
        mock_image.frombytes.return_value = mock_img
        
        # Mock BytesIO
        mock_io = MagicMock()
        mock_io.getbuffer.return_value = b'image_data'
        mock_bytesio.return_value.__enter__.return_value = mock_io
        
        viewer = Viewer()
        viewer.hashes = {'css': {}, 'js': {}}
        
        # Mock for _update_thumbnails database connection
        mock_con = MagicMock()
        mock_cur = MagicMock()
        # First call: SELECT file FROM thumbnails (returns empty - no existing metadata)
        mock_cur.execute.return_value.fetchall.return_value = []
        mock_con.cursor.return_value = mock_cur
        mock_connect.return_value.__enter__.return_value = mock_con
        
        viewer._update_thumbnails()
        
        # Verify INSERT was called
        insert_calls = [call for call in mock_cur.execute.call_args_list 
                       if 'INSERT' in str(call)]
        assert len(insert_calls) > 0

    @patch('main.connect')
    @patch('main.listdir')
    @patch('main.abspath')
    @patch('main.basename')
    @patch('builtins.open', new_callable=mock_open, read_data=b'test content')
    @patch('main.SHA384')
    def test_update_thumbnails_ignores_non_mp4_files(
        self, mock_sha384, mock_file, mock_basename, mock_abspath, mock_listdir, mock_connect
    ):
        """Test that _update_thumbnails ignores non-MP4 files."""
        # Setup basic mocks for Viewer init
        def listdir_side_effect(path):
            if 'css' in path:
                return ['bootstrap.min.css']
            elif 'js' in path:
                return ['bootstrap.bundle.min.js']
            elif 'vid' in path or './vid' in path:
                return ['video.txt', 'video.avi']
            return []
        
        mock_listdir.side_effect = listdir_side_effect
        mock_abspath.side_effect = lambda x: x
        mock_basename.side_effect = lambda x: os.path.basename(x)
        mock_hash = MagicMock()
        mock_hash.digest.return_value = b'test_digest'
        mock_sha384.new.return_value = mock_hash
        
        mock_con_init = MagicMock()
        mock_cur_init = MagicMock()
        mock_cur_init.execute.return_value.fetchall.return_value = []
        mock_con_init.cursor.return_value = mock_cur_init
        mock_connect.return_value.__enter__.return_value = mock_con_init
        
        viewer = Viewer()
        viewer.hashes = {'css': {}, 'js': {}}
        
        # Mock for _update_thumbnails database connection
        mock_con = MagicMock()
        mock_cur = MagicMock()
        mock_cur.execute.return_value.fetchall.return_value = []
        mock_con.cursor.return_value = mock_cur
        mock_connect.return_value.__enter__.return_value = mock_con
        
        viewer._update_thumbnails()
        
        # Should not call ffmpeg for non-MP4 files
        # (This is implicit - if it tried, it would fail without mocks)


class TestIndex:
    """Tests for Viewer.index method."""

    @patch('main.connect')
    @patch('main.listdir')
    @patch('main.abspath')
    @patch('main.basename')
    @patch('builtins.open', new_callable=mock_open, read_data=b'test content')
    @patch('main.SHA384')
    def test_index_returns_html(
        self, mock_sha384, mock_file, mock_basename, mock_abspath, mock_listdir, mock_connect
    ):
        """Test that index() returns valid HTML."""
        # Setup basic mocks for Viewer init
        mock_listdir.side_effect = lambda x: ['bootstrap.min.css'] if 'css' in x else ['bootstrap.bundle.min.js']
        mock_abspath.side_effect = lambda x: x
        mock_basename.side_effect = lambda x: os.path.basename(x)
        mock_hash = MagicMock()
        mock_hash.digest.return_value = b'test_digest'
        mock_sha384.new.return_value = mock_hash
        
        mock_con_init = MagicMock()
        mock_cur_init = MagicMock()
        mock_cur_init.execute.return_value.fetchall.return_value = []
        mock_con_init.cursor.return_value = mock_cur_init
        mock_connect.return_value.__enter__.return_value = mock_con_init
        
        with patch.object(Viewer, '_update_thumbnails'):
            viewer = Viewer()
        
        viewer.hashes = {
            'css': {'bootstrap.min.css': 'test_hash'},
            'js': {'bootstrap.bundle.min.js': 'test_hash'}
        }
        
        mock_basename.side_effect = lambda x: os.path.basename(x)
        mock_abspath.side_effect = lambda x: x
        mock_listdir.return_value = []
        
        mock_con = MagicMock()
        mock_cur = MagicMock()
        mock_cur.execute.return_value.fetchone.return_value = None
        mock_con.cursor.return_value = mock_cur
        mock_connect.return_value.__enter__.return_value = mock_con
        
        result = viewer.index()
        
        assert isinstance(result, str)
        assert '<!DOCTYPE html>' in result
        assert '<html>' in result
        assert '<title>Video viewer</title>' in result

    @patch('main.connect')
    @patch('main.listdir')
    @patch('main.abspath')
    @patch('main.basename')
    @patch('builtins.open', new_callable=mock_open, read_data=b'test content')
    @patch('main.SHA384')
    def test_index_displays_videos(
        self, mock_sha384, mock_file, mock_basename, mock_abspath, mock_listdir, mock_connect
    ):
        """Test that index() displays video thumbnails."""
        # Setup basic mocks for Viewer init
        def listdir_side_effect(path):
            if 'css' in path:
                return ['bootstrap.min.css']
            elif 'js' in path:
                return ['bootstrap.bundle.min.js']
            elif 'vid' in path or './vid' in path:
                return ['test1.mp4', 'test2.mp4']
            return []
        
        mock_listdir.side_effect = listdir_side_effect
        mock_abspath.side_effect = lambda x: x
        mock_basename.side_effect = lambda x: os.path.basename(x)
        mock_hash = MagicMock()
        mock_hash.digest.return_value = b'test_digest'
        mock_sha384.new.return_value = mock_hash
        
        mock_con_init = MagicMock()
        mock_cur_init = MagicMock()
        mock_cur_init.execute.return_value.fetchall.return_value = []
        mock_con_init.cursor.return_value = mock_cur_init
        mock_connect.return_value.__enter__.return_value = mock_con_init
        
        with patch.object(Viewer, '_update_thumbnails'):
            viewer = Viewer()
        
        viewer.hashes = {
            'css': {'bootstrap.min.css': 'test_hash'},
            'js': {'bootstrap.bundle.min.js': 'test_hash'}
        }
        
        # Mock for index() database connection
        mock_con = MagicMock()
        mock_cur = MagicMock()
        mock_cur.execute.return_value.fetchone.return_value = ('base64_image_data',)
        mock_con.cursor.return_value = mock_cur
        mock_connect.return_value.__enter__.return_value = mock_con
        
        result = viewer.index()
        
        assert 'test1.mp4' in result or 'test2.mp4' in result
        assert 'data:image/png;base64' in result


class TestRefresh:
    """Tests for Viewer.refresh method."""

    @patch('main.cherrypy.HTTPRedirect')
    @patch('main.connect')
    @patch('main.listdir')
    @patch('main.abspath')
    @patch('main.basename')
    @patch('builtins.open', new_callable=mock_open, read_data=b'test content')
    @patch('main.SHA384')
    def test_refresh_calls_update_thumbnails(
        self, mock_sha384, mock_file, mock_basename, mock_abspath, 
        mock_listdir, mock_connect, mock_redirect
    ):
        """Test that refresh() calls _update_thumbnails."""
        # Setup basic mocks for Viewer init
        def listdir_side_effect(path):
            if 'css' in path:
                return ['bootstrap.min.css']
            elif 'js' in path:
                return ['bootstrap.bundle.min.js']
            return []
        
        mock_listdir.side_effect = listdir_side_effect
        mock_abspath.side_effect = lambda x: x
        mock_basename.side_effect = lambda x: os.path.basename(x)
        mock_hash = MagicMock()
        mock_hash.digest.return_value = b'test_digest'
        mock_sha384.new.return_value = mock_hash
        
        mock_con_init = MagicMock()
        mock_cur_init = MagicMock()
        mock_cur_init.execute.return_value.fetchall.return_value = []
        mock_con_init.cursor.return_value = mock_cur_init
        mock_connect.return_value.__enter__.return_value = mock_con_init
        
        # Mock ffmpeg to avoid AttributeError during init
        mock_ffmpeg_module = MagicMock()
        mock_ffmpeg_module.probe.return_value = {
            'streams': [{
                'codec_type': 'video',
                'width': '1920',
                'height': '1080',
                'r_frame_rate': '30/1'
            }]
        }
        mock_ffmpeg_module.input.return_value.filter.return_value.output.return_value.run.return_value = (b'\x00' * (1920 * 1080 * 3), b'')
        
        with patch('main.ffmpeg', mock_ffmpeg_module), \
             patch('main.Image') as mock_image, \
             patch('main.BytesIO') as mock_bytesio:
            # Mock BytesIO and Image
            mock_io = MagicMock()
            mock_io.getbuffer.return_value = b'image_data'
            mock_bytesio.return_value.__enter__.return_value = mock_io
            mock_img = MagicMock()
            mock_img.resize.return_value = mock_img
            mock_image.frombytes.return_value = mock_img
            
            with patch.object(Viewer, '_update_thumbnails') as mock_update:
                viewer = Viewer()
                viewer.hashes = {'css': {}, 'js': {}}
                
                mock_redirect_instance = MagicMock()
                mock_redirect.return_value = mock_redirect_instance
                
                try:
                    viewer.refresh()
                except:
                    pass  # HTTPRedirect raises an exception
                
                # _update_thumbnails is called once during __init__ and once in refresh()
                assert mock_update.call_count == 2


class TestVvid:
    """Tests for Viewer.vvid method."""

    @patch('main.listdir')
    @patch('main.abspath')
    @patch('main.basename')
    @patch('main.connect')
    @patch('builtins.open', new_callable=mock_open, read_data=b'test content')
    @patch('main.SHA384')
    def test_vvid_returns_html_for_valid_video(
        self, mock_sha384, mock_file, mock_connect, mock_basename, mock_abspath, mock_listdir
    ):
        """Test that vvid() returns HTML for a valid video."""
        # Setup basic mocks for Viewer init
        def listdir_side_effect(path):
            if 'css' in path:
                return ['bootstrap.min.css']
            elif 'js' in path:
                return ['bootstrap.bundle.min.js']
            elif 'vid' in path or './vid' in path:
                return ['test_video.mp4']
            return []
        
        mock_listdir.side_effect = listdir_side_effect
        mock_abspath.side_effect = lambda x: x
        mock_basename.side_effect = lambda x: os.path.basename(x)
        mock_hash = MagicMock()
        mock_hash.digest.return_value = b'test_digest'
        mock_sha384.new.return_value = mock_hash
        
        mock_con_init = MagicMock()
        mock_cur_init = MagicMock()
        mock_cur_init.execute.return_value.fetchall.return_value = []
        mock_con_init.cursor.return_value = mock_cur_init
        mock_connect.return_value.__enter__.return_value = mock_con_init
        
        with patch.object(Viewer, '_update_thumbnails'):
            viewer = Viewer()
        
        viewer.hashes = {
            'css': {
                'bootstrap.min.css': 'test_hash',
                'video-js.css': 'test_hash'
            },
            'js': {
                'bootstrap.bundle.min.js': 'test_hash',
                'video.min.js': 'test_hash',
                'videojs.hotkeys.min.js': 'test_hash'
            }
        }
        
        result = viewer.vvid('test_video.mp4')
        
        assert isinstance(result, str)
        assert '<!DOCTYPE html>' in result
        assert '<video' in result
        assert 'test_video.mp4' in result

    @patch('main.listdir')
    @patch('main.abspath')
    @patch('main.basename')
    @patch('main.connect')
    @patch('builtins.open', new_callable=mock_open, read_data=b'test content')
    @patch('main.SHA384')
    def test_vvid_returns_not_found_for_invalid_video(
        self, mock_sha384, mock_file, mock_connect, mock_basename, mock_abspath, mock_listdir
    ):
        """Test that vvid() returns 'Not found' for invalid video."""
        # Setup basic mocks for Viewer init
        def listdir_side_effect(path):
            if 'css' in path:
                return ['bootstrap.min.css']
            elif 'js' in path:
                return ['bootstrap.bundle.min.js']
            elif 'vid' in path or './vid' in path:
                return []
            return []
        
        mock_listdir.side_effect = listdir_side_effect
        mock_abspath.side_effect = lambda x: x
        mock_basename.side_effect = lambda x: os.path.basename(x)
        mock_hash = MagicMock()
        mock_hash.digest.return_value = b'test_digest'
        mock_sha384.new.return_value = mock_hash
        
        mock_con_init = MagicMock()
        mock_cur_init = MagicMock()
        mock_cur_init.execute.return_value.fetchall.return_value = []
        mock_con_init.cursor.return_value = mock_cur_init
        mock_connect.return_value.__enter__.return_value = mock_con_init
        
        with patch.object(Viewer, '_update_thumbnails'):
            viewer = Viewer()
        
        viewer.hashes = {
            'css': {
                'bootstrap.min.css': 'test_hash',
                'video-js.css': 'test_hash'
            },
            'js': {'bootstrap.bundle.min.js': 'test_hash'}
        }
        
        result = viewer.vvid('nonexistent.mp4')
        
        assert 'Not found' in result

    @patch('main.listdir')
    @patch('main.abspath')
    @patch('main.basename')
    @patch('main.connect')
    @patch('builtins.open', new_callable=mock_open, read_data=b'test content')
    @patch('main.SHA384')
    def test_vvid_handles_default_parameter(
        self, mock_sha384, mock_file, mock_connect, mock_basename, mock_abspath, mock_listdir
    ):
        """Test that vvid() handles default 'None' parameter."""
        # Setup basic mocks for Viewer init
        def listdir_side_effect(path):
            if 'css' in path:
                return ['bootstrap.min.css']
            elif 'js' in path:
                return ['bootstrap.bundle.min.js']
            elif 'vid' in path or './vid' in path:
                return []
            return []
        
        mock_listdir.side_effect = listdir_side_effect
        mock_abspath.side_effect = lambda x: x
        mock_basename.side_effect = lambda x: os.path.basename(x)
        mock_hash = MagicMock()
        mock_hash.digest.return_value = b'test_digest'
        mock_sha384.new.return_value = mock_hash
        
        mock_con_init = MagicMock()
        mock_cur_init = MagicMock()
        mock_cur_init.execute.return_value.fetchall.return_value = []
        mock_con_init.cursor.return_value = mock_cur_init
        mock_connect.return_value.__enter__.return_value = mock_con_init
        
        with patch.object(Viewer, '_update_thumbnails'):
            viewer = Viewer()
        
        viewer.hashes = {
            'css': {
                'bootstrap.min.css': 'test_hash',
                'video-js.css': 'test_hash'
            },
            'js': {'bootstrap.bundle.min.js': 'test_hash'}
        }
        
        result = viewer.vvid()
        
        assert 'Not found' in result


class TestStop:
    """Tests for Viewer.stop method."""

    @patch('main.cherrypy.log')
    @patch('main.connect')
    @patch('main.listdir')
    @patch('main.abspath')
    @patch('main.basename')
    @patch('builtins.open', new_callable=mock_open, read_data=b'test content')
    @patch('main.SHA384')
    def test_stop_logs_message(
        self, mock_sha384, mock_file, mock_basename, mock_abspath, 
        mock_listdir, mock_connect, mock_log
    ):
        """Test that stop() logs a message."""
        # Setup basic mocks for Viewer init
        mock_listdir.side_effect = lambda x: ['bootstrap.min.css'] if 'css' in x else ['bootstrap.bundle.min.js']
        mock_abspath.side_effect = lambda x: x
        mock_basename.side_effect = lambda x: os.path.basename(x)
        mock_hash = MagicMock()
        mock_hash.digest.return_value = b'test_digest'
        mock_sha384.new.return_value = mock_hash
        
        mock_con_init = MagicMock()
        mock_cur_init = MagicMock()
        mock_cur_init.execute.return_value.fetchall.return_value = []
        mock_con_init.cursor.return_value = mock_cur_init
        mock_connect.return_value.__enter__.return_value = mock_con_init
        
        with patch.object(Viewer, '_update_thumbnails'):
            viewer = Viewer()
        
        viewer.hashes = {'css': {}, 'js': {}}
        
        viewer.stop()
        
        mock_log.error.assert_called_once()
        call_args = mock_log.error.call_args
        assert 'Viewer Stopped!' in str(call_args)

