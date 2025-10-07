"""
CloudClearingAPI Core Module

This package contains the core functionality for satellite imagery
change detection and analysis.
"""

from .change_detector import ChangeDetector, ChangeDetectionConfig
from .config import AppConfig, get_config, reload_config

__version__ = "0.1.0"
__author__ = "CloudClearingAPI Team"

__all__ = [
    "ChangeDetector",
    "ChangeDetectionConfig", 
    "AppConfig",
    "get_config",
    "reload_config"
]