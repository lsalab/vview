# Test Suite for vview

This directory contains unit tests for the vview video viewer application.

## Running Tests

### Prerequisites

Install test dependencies:

```bash
pip install -r requirements-test.txt
```

Or install pytest directly:

```bash
pip install pytest pytest-cov
```

### Running All Tests

```bash
pytest
```

### Running with Verbose Output

```bash
pytest -v
```

### Running Specific Test Files

```bash
pytest tests/test_main.py
pytest tests/test_helpers.py
```

### Running Specific Test Classes

```bash
pytest tests/test_main.py::TestViewerInit
pytest tests/test_main.py::TestIndex
```

### Running Specific Tests

```bash
pytest tests/test_main.py::TestViewerInit::test_init_creates_hashes_for_css_js
pytest tests/test_helpers.py::TestPerr::test_perr_writes_to_stderr
```

### Running with Coverage

```bash
pytest --cov=main --cov-report=html
```

This will generate an HTML coverage report in the `htmlcov/` directory.

## Test Structure

### `test_main.py`
Tests for the `Viewer` class and its methods:
- `TestViewerInit` - Tests for Viewer initialization
- `TestUpdateThumbnails` - Tests for thumbnail update functionality
- `TestIndex` - Tests for the index page generation
- `TestRefresh` - Tests for the refresh endpoint
- `TestVvid` - Tests for the video viewing page
- `TestStop` - Tests for the stop handler

### `test_helpers.py`
Tests for utility functions:
- `TestPerr` - Tests for the `perr()` error logging function

### `conftest.py`
Shared pytest fixtures for test setup:
- `temp_dir` - Temporary directory for test files
- `mock_css_folder` - Mock CSS folder with test files
- `mock_js_folder` - Mock JS folder with test files
- `mock_vid_folder` - Mock video folder
- `mock_db_path` - Temporary database path
- `mock_ffmpeg_probe` - Mock ffmpeg.probe response
- `mock_ffmpeg_output` - Mock ffmpeg output data
- `sample_video_files` - Sample video files for testing

## Test Coverage

The test suite covers:
- Viewer class initialization and hash generation
- Thumbnail database operations (create, update, delete)
- HTML page generation (index, video player)
- Error handling and edge cases
- Utility functions

## Notes

- Tests use mocking extensively to avoid dependencies on:
  - File system operations
  - Database connections
  - FFmpeg operations
  - CherryPy server
- All external dependencies are mocked to ensure tests run quickly and reliably

