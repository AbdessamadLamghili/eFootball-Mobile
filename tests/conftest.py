"""Pytest configuration for the test suite."""
import django
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
