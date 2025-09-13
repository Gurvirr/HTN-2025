# Installation Guide for Smart Glasses Agent Socket

This guide will help you set up the Smart Glasses Agent Socket backend system.

## Prerequisites

- Python 3.8 or higher
- pip (Python package installer)

## Quick Installation

### 1. Navigate to Backend Directory
```bash
cd HTN-2025/backend
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Run the Server
```bash
python app.py
```

The server will start on `http://localhost:5000`

### 4. Test the Connection
In a new terminal:
```bash
# Interactive testing
python test_client.py

# Or automated test sequence
python test_client.py --auto
```

## Detailed Installation

### Option 1: Using Virtual Environment (Recommended)

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the server
python app.py
```

### Option 2: Global Installation

```bash
# Install dependencies globally
pip install -r requirements.txt

# Run the server
python app.py
```

## Core Dependencies

The following packages will be installed:

- **aiohttp** (3.9.1) - Web framework for HTTP server
- **python-socketio[client]** (5.10.0) - Socket.IO server and client
- **python-dateutil** (2.8.2) - Date/time utilities
- **coloredlogs** (15.0.1) - Enhanced logging

## Development Dependencies

For development and testing:

- **pytest** (7.4.3) - Testing framework
- **pytest-asyncio** (0.21.1) - Async testing support
- **black** (23.11.0) - Code formatting
- **flake8** (6.1.0) - Code linting

## Optional Dependencies

### AI/ML Integration
Uncomment in `requirements.txt` if needed:
```
openai==1.3.7
anthropic==0.7.8
```

### Speech Processing
```
speech-recognition==3.10.0
pydub==0.25.1
```

### Image/Video Processing
```
Pillow==10.1.0
opencv-python==4.8.1.78
```

## Verification

### Check Server Status
```bash
curl http://localhost:5000/health
```

Expected response:
```json
{
  "status": "healthy",
  "mode": "conversational",
  "active_session": false,
  "uptime": 0.0
}
```

### Check Available Endpoints
- `GET /health` - Health check
- `GET /state` - Current app state
- `GET /history?limit=10` - Command history
- `POST /mode` - Change app mode

## Troubleshooting

### Common Issues

#### 1. Import Errors
```
ImportError: No module named 'socketio'
```
**Solution**: Install dependencies with `pip install -r requirements.txt`

#### 2. Port Already in Use
```
OSError: [Errno 48] Address already in use
```
**Solution**: Kill process using port 5000 or change port in `app.py`
```bash
# Find process using port 5000
lsof -i :5000
# Kill process
kill -9 <PID>
```

#### 3. Permission Issues on macOS/Linux
```
Permission denied
```
**Solution**: Use `sudo` or virtual environment
```bash
sudo pip install -r requirements.txt
```

#### 4. Python Version Issues
**Solution**: Ensure Python 3.8+ is installed
```bash
python --version
```

### Development Setup

For development with auto-reload:
```bash
# Install development dependencies
pip install -r requirements.txt

# Format code
black app.py data_types.py test_client.py

# Run linting
flake8 app.py data_types.py test_client.py

# Run tests
pytest
```

## Next Steps

1. **Integrate LLM**: Edit `_process_with_llm()` method in `app.py`
2. **Configure Settings**: Modify host/port in `app.py` if needed
3. **Add Authentication**: Implement socket authentication as needed
4. **Deploy**: Set up production deployment with proper WSGI server

## Support

- Check logs for detailed error messages
- Use test client to verify socket connections
- Review `README.md` for architecture details
- Ensure all dependencies are properly installed

## Files Overview

- `app.py` - Main socket server
- `data_types.py` - Type definitions and data structures
- `test_client.py` - Testing client for verification
- `requirements.txt` - Python dependencies
- `README.md` - Architecture and usage documentation