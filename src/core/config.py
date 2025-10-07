"""
Configuration management for CloudClearingAPI

This module handles loading and validating configuration settings
from YAML files and environment variables.
"""

import os
import yaml
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

@dataclass
class AlertConfig:
    """Configuration for alerting system"""
    email_enabled: bool = True
    email_recipients: List[str] = field(default_factory=list)
    smtp_server: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    webhook_url: Optional[str] = None
    slack_token: Optional[str] = None

@dataclass
class DatabaseConfig:
    """Database configuration"""
    enabled: bool = False
    url: str = "sqlite:///cloudclearing.db"
    pool_size: int = 5
    max_overflow: int = 10

@dataclass
class ProcessingConfig:
    """Image processing configuration"""
    max_cloud_cover: float = 20.0
    composite_method: str = "median"  # median, mean, percentile
    scale: int = 10  # meters per pixel
    max_pixels: int = int(1e9)
    
    # Enhanced cloud masking
    use_s2cloudless: bool = True
    cloud_probability_threshold: int = 50
    cloud_buffer_distance: int = 50
    use_qa60: bool = True
    use_cirrus_mask: bool = False
    
@dataclass
class MonitoringConfig:
    """Area monitoring configuration"""
    # Yogyakarta default bounding box
    bbox_west: float = 110.25
    bbox_east: float = 110.55  
    bbox_south: float = -7.95
    bbox_north: float = -7.65
    
    # Update schedule
    check_interval_hours: int = 24 * 7  # Weekly
    lookback_days: int = 7
    
    # Change thresholds
    ndvi_loss_threshold: float = -0.20
    ndbi_gain_threshold: float = 0.15
    min_change_area_m2: float = 500.0
    
    # Advanced filtering
    max_changes_per_alert: int = 20
    change_confidence_threshold: float = 0.7
    exclude_water_bodies: bool = True
    exclude_agricultural: bool = True
    exclude_seasonal_vegetation: bool = False

@dataclass
class AppConfig:
    """Main application configuration"""
    # Sub-configurations
    monitoring: MonitoringConfig = field(default_factory=MonitoringConfig)
    processing: ProcessingConfig = field(default_factory=ProcessingConfig)
    alerts: AlertConfig = field(default_factory=AlertConfig)
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    
    # Application settings
    debug: bool = False
    log_level: str = "INFO"
    data_dir: str = "./data"
    output_dir: str = "./output"
    
    # Google Earth Engine
    gee_project: Optional[str] = None
    gee_service_account: Optional[str] = None

class ConfigManager:
    """Manages application configuration loading and validation"""
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or self._find_config_file()
        self.config = self._load_config()
        
    def _find_config_file(self) -> str:
        """Find configuration file in standard locations"""
        possible_paths = [
            "./config/config.yaml",
            "./config.yaml", 
            os.path.expanduser("~/.cloudclearing/config.yaml"),
            "/etc/cloudclearing/config.yaml"
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                return path
                
        # Return default path if none found
        return "./config/config.yaml"
    
    def _load_config(self) -> AppConfig:
        """Load configuration from file and environment variables"""
        
        # Start with defaults
        config_dict = {}
        
        # Load from YAML file if it exists
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    config_dict = yaml.safe_load(f) or {}
                logger.info(f"Loaded configuration from {self.config_path}")
            except Exception as e:
                logger.warning(f"Failed to load config file {self.config_path}: {e}")
        
        # Override with environment variables
        config_dict = self._apply_env_overrides(config_dict)
        
        # Convert to configuration objects
        return self._dict_to_config(config_dict)
    
    def _apply_env_overrides(self, config_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Apply environment variable overrides"""
        
        env_mappings = {
            # Database
            'DATABASE_URL': ('database', 'url'),
            'DATABASE_ENABLED': ('database', 'enabled'),
            
            # Alerts
            'SMTP_SERVER': ('alerts', 'smtp_server'),
            'SMTP_USERNAME': ('alerts', 'smtp_username'),
            'SMTP_PASSWORD': ('alerts', 'smtp_password'),
            'ALERT_RECIPIENTS': ('alerts', 'email_recipients'),
            'WEBHOOK_URL': ('alerts', 'webhook_url'),
            
            # Google Earth Engine
            'GOOGLE_APPLICATION_CREDENTIALS': ('gee_service_account',),
            'GEE_PROJECT': ('gee_project',),
            
            # Application
            'DEBUG': ('debug',),
            'LOG_LEVEL': ('log_level',),
        }
        
        for env_var, config_path in env_mappings.items():
            value = os.getenv(env_var)
            if value is not None:
                # Handle type conversion
                if env_var in ['DATABASE_ENABLED', 'DEBUG']:
                    value = value.lower() in ('true', '1', 'yes', 'on')
                elif env_var == 'ALERT_RECIPIENTS':
                    value = [email.strip() for email in value.split(',')]
                
                # Set nested configuration
                current = config_dict
                for key in config_path[:-1]:
                    current = current.setdefault(key, {})
                current[config_path[-1]] = value
        
        return config_dict
    
    def _dict_to_config(self, config_dict: Dict[str, Any]) -> AppConfig:
        """Convert dictionary to configuration objects"""
        
        # Extract sub-configurations
        monitoring_dict = config_dict.get('monitoring', {})
        processing_dict = config_dict.get('processing', {})
        alerts_dict = config_dict.get('alerts', {})
        database_dict = config_dict.get('database', {})
        
        # Create configuration objects
        monitoring = MonitoringConfig(**monitoring_dict)
        processing = ProcessingConfig(**processing_dict)
        alerts = AlertConfig(**alerts_dict)
        database = DatabaseConfig(**database_dict)
        
        # Main configuration (filter out sections handled separately)
        excluded_sections = ['monitoring', 'processing', 'alerts', 'database', 'logging', 'monitoring_regions']
        main_dict = {k: v for k, v in config_dict.items() 
                    if k not in excluded_sections}
        
        return AppConfig(
            monitoring=monitoring,
            processing=processing,
            alerts=alerts,
            database=database,
            **main_dict
        )
    
    def save_config(self, config_path: Optional[str] = None) -> None:
        """Save current configuration to file"""
        
        path = config_path or self.config_path
        
        # Convert config to dictionary
        config_dict = {
            'monitoring': {
                'bbox_west': self.config.monitoring.bbox_west,
                'bbox_east': self.config.monitoring.bbox_east,
                'bbox_south': self.config.monitoring.bbox_south,
                'bbox_north': self.config.monitoring.bbox_north,
                'check_interval_hours': self.config.monitoring.check_interval_hours,
                'lookback_days': self.config.monitoring.lookback_days,
                'ndvi_loss_threshold': self.config.monitoring.ndvi_loss_threshold,
                'ndbi_gain_threshold': self.config.monitoring.ndbi_gain_threshold,
                'min_change_area_m2': self.config.monitoring.min_change_area_m2,
            },
            'processing': {
                'max_cloud_cover': self.config.processing.max_cloud_cover,
                'composite_method': self.config.processing.composite_method,
                'scale': self.config.processing.scale,
                'max_pixels': self.config.processing.max_pixels,
            },
            'alerts': {
                'email_enabled': self.config.alerts.email_enabled,
                'email_recipients': self.config.alerts.email_recipients,
                'smtp_server': self.config.alerts.smtp_server,
                'smtp_port': self.config.alerts.smtp_port,
                'smtp_username': self.config.alerts.smtp_username,
                'webhook_url': self.config.alerts.webhook_url,
            },
            'database': {
                'enabled': self.config.database.enabled,
                'url': self.config.database.url,
            },
            'debug': self.config.debug,
            'log_level': self.config.log_level,
            'data_dir': self.config.data_dir,
            'output_dir': self.config.output_dir,
        }
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(path), exist_ok=True)
        
        # Save to file
        with open(path, 'w') as f:
            yaml.dump(config_dict, f, default_flow_style=False, indent=2)
        
        logger.info(f"Configuration saved to {path}")

# Global configuration instance
_config_manager = None

def get_config() -> AppConfig:
    """Get the global configuration instance"""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager.config

def reload_config(config_path: Optional[str] = None) -> AppConfig:
    """Reload configuration from file"""
    global _config_manager
    _config_manager = ConfigManager(config_path)
    return _config_manager.config