"""Gunicorn configuration."""
import gunicorn.http.wsgi

gunicorn.http.wsgi.SERVER = "RedTeam-Platform"
