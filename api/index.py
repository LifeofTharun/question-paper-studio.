import os
import sys

# Ensure root folder is on sys.path for Vercel serverless imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app

# Export app instance for Vercel WSGI
app = app
