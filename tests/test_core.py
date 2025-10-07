"""
Unit tests for CloudClearingAPI core functionality
"""

import unittest
from unittest.mock import patch, MagicMock
import sys
from pathlib import Path
import os

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core.config import ConfigManager, AppConfig, ChangeDetectionConfig
from core.change_detector import ChangeDetector

class TestConfig(unittest.TestCase):
    """Test configuration management"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.test_config_path = "test_config.yaml"
    
    def tearDown(self):
        """Clean up test fixtures"""
        if os.path.exists(self.test_config_path):
            os.remove(self.test_config_path)
    
    def test_default_config_creation(self):
        """Test creating default configuration"""
        config = AppConfig()
        
        self.assertIsInstance(config.monitoring.bbox_west, float)
        self.assertIsInstance(config.monitoring.ndvi_loss_threshold, float)
        self.assertEqual(config.debug, False)
    
    def test_change_detection_config(self):
        """Test change detection configuration"""
        config = ChangeDetectionConfig(
            ndvi_loss_threshold=-0.25,
            ndbi_gain_threshold=0.20,
            min_change_area=300.0
        )
        
        self.assertEqual(config.ndvi_loss_threshold, -0.25)
        self.assertEqual(config.ndbi_gain_threshold, 0.20)
        self.assertEqual(config.min_change_area, 300.0)

class TestChangeDetector(unittest.TestCase):
    """Test change detection functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.config = ChangeDetectionConfig()
    
    @patch('core.change_detector.ee')
    def test_detector_initialization(self, mock_ee):
        """Test detector initialization"""
        # Mock Earth Engine initialization
        mock_ee.Initialize.return_value = None
        
        detector = ChangeDetector(self.config)
        
        self.assertIsNotNone(detector.config)
        self.assertEqual(detector.config.ndvi_loss_threshold, -0.20)
    
    @patch('core.change_detector.ee')
    def test_weekly_change_detection(self, mock_ee):
        """Test weekly change detection workflow"""
        # Mock Earth Engine objects
        mock_ee.Initialize.return_value = None
        mock_ee.Geometry.Rectangle.return_value = MagicMock()
        
        # Mock image collections and processing
        mock_collection = MagicMock()
        mock_ee.ImageCollection.return_value = mock_collection
        mock_collection.filterDate.return_value = mock_collection
        mock_collection.filterBounds.return_value = mock_collection
        mock_collection.filter.return_value = mock_collection
        mock_collection.map.return_value = mock_collection
        mock_collection.median.return_value = MagicMock()
        
        detector = ChangeDetector(self.config)
        
        # This would normally require actual GEE authentication
        # For testing, we'd need to mock the entire GEE workflow
        self.assertIsNotNone(detector)

class TestAPI(unittest.TestCase):
    """Test API functionality"""
    
    def test_analysis_request_validation(self):
        """Test API request model validation"""
        from api.main import AnalysisRequest
        
        # Valid request
        request = AnalysisRequest(
            week_a_start="2025-09-01",
            week_b_start="2025-09-08"
        )
        
        self.assertEqual(request.week_a_start, "2025-09-01")
        self.assertEqual(request.week_b_start, "2025-09-08")
        self.assertEqual(request.bbox_west, 110.25)  # Default value

if __name__ == '__main__':
    # Run tests
    unittest.main(verbosity=2)