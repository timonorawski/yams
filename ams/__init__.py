"""
YAML Arcade Management System (YAMS)

Abstraction layer between detection hardware and games.
See docs/architecture/AMS_ARCHITECTURE.md for design details.
"""

import logging

# Create logger for AMS package
logger = logging.getLogger('ams')

# Don't add handlers here - let the application configure logging
# This allows users to control log level and output format

__all__ = ['logger']
