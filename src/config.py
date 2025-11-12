"""
GestureGlide - Configuration Management Module
Handles loading and validation of YAML configuration
"""

import yaml
from pathlib import Path
from typing import Dict, Any, Optional
import logging


class Config:
    """Configuration manager for GestureGlide"""
    
    def __init__(self, config_path: str = "config.yaml"):
        """
        Initialize configuration from YAML file
        
        Args:
            config_path: Path to configuration file
            
        Raises:
            FileNotFoundError: If config file doesn't exist
            yaml.YAMLError: If config file is invalid
        """
        self.logger = logging.getLogger(__name__)
        self.config_path = Path(config_path)
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Config file not found: {self.config_path}")
        
        try:
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)
            self.logger.info(f"Configuration loaded from {self.config_path}")
            return config
        except yaml.YAMLError as e:
            self.logger.error(f"Invalid YAML in config file: {e}")
            raise
    
    def reload(self) -> None:
        """Reload configuration from file"""
        self.config = self._load_config()
        self.logger.info("Configuration reloaded")
    
    def save(self, output_path: Optional[str] = None) -> None:
        """Save configuration to file"""
        path = Path(output_path) if output_path else self.config_path
        try:
            with open(path, 'w') as f:
                yaml.dump(self.config, f, default_flow_style=False)
            self.logger.info(f"Configuration saved to {path}")
        except Exception as e:
            self.logger.error(f"Failed to save configuration: {e}")
            raise
    
    def __getitem__(self, key: str) -> Any:
        """Dictionary-style access to config"""
        return self.config[key]
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value with default"""
        return self.config.get(key, default)
    
    def update(self, updates: Dict[str, Any]) -> None:
        """Update configuration values"""
        self.config.update(updates)
        self.logger.info(f"Configuration updated with {len(updates)} changes")
    
    # Property-based access for common sections
    @property
    def hand_tracking(self) -> Dict[str, Any]:
        return self.config.get('hand_tracking', {})
    
    @property
    def cursor_control(self) -> Dict[str, Any]:
        return self.config.get('cursor_control', {})
    
    @property
    def gesture_detection(self) -> Dict[str, Any]:
        return self.config.get('gesture_detection', {})
    
    @property
    def performance(self) -> Dict[str, Any]:
        return self.config.get('performance', {})
    
    @property
    def visualization(self) -> Dict[str, Any]:
        return self.config.get('visualization', {})
    
    @property
    def system(self) -> Dict[str, Any]:
        return self.config.get('system', {})
    
    @property
    def advanced(self) -> Dict[str, Any]:
        return self.config.get('advanced', {})
