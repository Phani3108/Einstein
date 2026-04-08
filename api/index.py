"""Vercel serverless function entry point.

Imports the FastAPI app so Vercel's Python runtime can serve it.
All routes under /api/v1/* are handled by the FastAPI application.
"""

from src.api.app import app
