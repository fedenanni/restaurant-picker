import sys
from pathlib import Path

# Ensure the api directory is in the Python path
api_dir = Path(__file__).resolve().parent
if str(api_dir) not in sys.path:
    sys.path.insert(0, str(api_dir))

from main import app

# Vercel serverless handler
handler = app
