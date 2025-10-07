"""
Database integration for CloudClearingAPI

This module provides PostgreSQL/PostGIS integration for storing
change detection results, analysis history, and monitoring configurations.
"""

import asyncio
import asyncpg
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Float, Boolean, Text, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.dialects.postgresql import UUID
from geoalchemy2 import Geometry
from datetime import datetime
from typing import List, Dict, Optional, Any
import uuid
import logging
from .config import get_config

logger = logging.getLogger(__name__)

Base = declarative_base()

class AnalysisResult(Base):
    """Store change detection analysis results"""
    __tablename__ = 'analysis_results'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    analysis_id = Column(String(100), unique=True, nullable=False)
    region_name = Column(String(100), nullable=False)
    
    # Time period
    week_a_start = Column(DateTime, nullable=False)
    week_a_end = Column(DateTime, nullable=False) 
    week_b_start = Column(DateTime, nullable=False)
    week_b_end = Column(DateTime, nullable=False)
    
    # Analysis parameters
    ndvi_threshold = Column(Float, nullable=False)
    ndbi_threshold = Column(Float, nullable=False)
    min_area_m2 = Column(Float, nullable=False)
    
    # Results
    change_count = Column(Integer, default=0)
    total_area_m2 = Column(Float, default=0.0)
    change_types = Column(JSON)
    
    # Geometry
    bbox = Column(Geometry('POLYGON', srid=4326))
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    processing_time_seconds = Column(Float)
    status = Column(String(20), default='completed')
    error_message = Column(Text)

class ChangePolygon(Base):
    """Store individual change polygons"""
    __tablename__ = 'change_polygons'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    analysis_id = Column(String(100), nullable=False)  # FK to analysis_results
    
    # Change characteristics
    change_type = Column(String(50), nullable=False)  # vegetation_loss, development, etc.
    confidence_score = Column(Float, nullable=False)
    area_m2 = Column(Float, nullable=False)
    
    # Spectral changes
    ndvi_change = Column(Float)
    ndbi_change = Column(Float)
    
    # Geometry
    geometry = Column(Geometry('POLYGON', srid=4326))
    
    # Metadata
    detected_at = Column(DateTime, default=datetime.utcnow)

class MonitoringRegion(Base):
    """Store monitoring region configurations"""
    __tablename__ = 'monitoring_regions'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(Text)
    
    # Priority and tags
    priority = Column(Integer, default=2)  # 1=high, 2=medium, 3=low
    tags = Column(JSON)  # ['java', 'urban', 'coastal']
    
    # Geometry
    bbox = Column(Geometry('POLYGON', srid=4326))
    
    # Monitoring settings
    active = Column(Boolean, default=True)
    check_interval_hours = Column(Integer, default=168)  # weekly
    
    # Thresholds (can override global settings)
    ndvi_threshold = Column(Float)
    ndbi_threshold = Column(Float)
    min_area_m2 = Column(Float)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class AlertLog(Base):
    """Store alert history"""
    __tablename__ = 'alert_log'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    analysis_id = Column(String(100), nullable=False)
    
    # Alert details
    alert_type = Column(String(50), nullable=False)  # email, webhook, slack
    recipient = Column(String(200), nullable=False)
    subject = Column(String(200))
    message = Column(Text)
    
    # Status
    status = Column(String(20), default='pending')  # pending, sent, failed
    sent_at = Column(DateTime)
    error_message = Column(Text)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)

class DatabaseManager:
    """Manages database connections and operations"""
    
    def __init__(self):
        self.config = get_config()
        self.engine = None
        self.SessionLocal = None
        
        if self.config.database.enabled:
            self._initialize_database()
    
    def _initialize_database(self):
        """Initialize database connection and create tables"""
        try:
            self.engine = create_engine(
                self.config.database.url,
                pool_size=self.config.database.pool_size,
                max_overflow=self.config.database.max_overflow,
                echo=self.config.debug
            )
            
            self.SessionLocal = sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=self.engine
            )
            
            # Create tables
            Base.metadata.create_all(bind=self.engine)
            
            logger.info("Database initialized successfully")
            
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            raise
    
    def get_session(self):
        """Get database session"""
        if not self.SessionLocal:
            raise RuntimeError("Database not initialized")
        return self.SessionLocal()
    
    def store_analysis_result(self, 
                            analysis_id: str,
                            region_name: str,
                            results: Dict[str, Any],
                            bbox_wkt: str) -> str:
        """
        Store analysis results in database
        
        Args:
            analysis_id: Unique analysis identifier
            region_name: Name of the analyzed region  
            results: Analysis results dictionary
            bbox_wkt: Bounding box as WKT string
            
        Returns:
            Database record ID
        """
        if not self.config.database.enabled:
            logger.warning("Database storage disabled")
            return None
        
        try:
            session = self.get_session()
            
            analysis_record = AnalysisResult(
                analysis_id=analysis_id,
                region_name=region_name,
                week_a_start=datetime.fromisoformat(results['week_a']),
                week_a_end=datetime.fromisoformat(results['week_a']) + timedelta(days=7),
                week_b_start=datetime.fromisoformat(results['week_b']),
                week_b_end=datetime.fromisoformat(results['week_b']) + timedelta(days=7),
                ndvi_threshold=results.get('ndvi_threshold', -0.2),
                ndbi_threshold=results.get('ndbi_threshold', 0.15),
                min_area_m2=results.get('min_area_m2', 500),
                change_count=results['change_count'],
                total_area_m2=results['total_area'],
                change_types=results['change_types'],
                bbox=f"SRID=4326;{bbox_wkt}",
                processing_time_seconds=results.get('processing_time', 0),
                status='completed'
            )
            
            session.add(analysis_record)
            session.commit()
            
            logger.info(f"Stored analysis result: {analysis_id}")
            return str(analysis_record.id)
            
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to store analysis result: {e}")
            raise
        finally:
            session.close()
    
    def get_analysis_history(self, 
                           region_name: Optional[str] = None,
                           limit: int = 50) -> List[Dict]:
        """
        Get analysis history from database
        
        Args:
            region_name: Filter by region name (optional)
            limit: Maximum number of records to return
            
        Returns:
            List of analysis records
        """
        if not self.config.database.enabled:
            return []
        
        try:
            session = self.get_session()
            
            query = session.query(AnalysisResult)
            
            if region_name:
                query = query.filter(AnalysisResult.region_name == region_name)
            
            records = query.order_by(AnalysisResult.created_at.desc()).limit(limit).all()
            
            results = []
            for record in records:
                results.append({
                    'analysis_id': record.analysis_id,
                    'region_name': record.region_name,
                    'week_a': record.week_a_start.isoformat(),
                    'week_b': record.week_b_start.isoformat(),
                    'change_count': record.change_count,
                    'total_area_m2': record.total_area_m2,
                    'change_types': record.change_types,
                    'created_at': record.created_at.isoformat(),
                    'status': record.status
                })
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to get analysis history: {e}")
            return []
        finally:
            session.close()
    
    def store_monitoring_region(self, region_data: Dict[str, Any]) -> str:
        """Store monitoring region configuration"""
        if not self.config.database.enabled:
            return None
        
        try:
            session = self.get_session()
            
            region = MonitoringRegion(
                name=region_data['name'],
                description=region_data.get('description'),
                priority=region_data.get('priority', 2),
                tags=region_data.get('tags', []),
                bbox=f"SRID=4326;{region_data['bbox_wkt']}",
                active=region_data.get('active', True),
                check_interval_hours=region_data.get('check_interval_hours', 168),
                ndvi_threshold=region_data.get('ndvi_threshold'),
                ndbi_threshold=region_data.get('ndbi_threshold'),
                min_area_m2=region_data.get('min_area_m2')
            )
            
            session.add(region)
            session.commit()
            
            logger.info(f"Stored monitoring region: {region_data['name']}")
            return str(region.id)
            
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to store monitoring region: {e}")
            raise
        finally:
            session.close()
    
    def log_alert(self, 
                  analysis_id: str,
                  alert_type: str,
                  recipient: str,
                  subject: str,
                  message: str,
                  status: str = 'pending') -> str:
        """Log alert to database"""
        if not self.config.database.enabled:
            return None
        
        try:
            session = self.get_session()
            
            alert = AlertLog(
                analysis_id=analysis_id,
                alert_type=alert_type,
                recipient=recipient,
                subject=subject,
                message=message,
                status=status,
                sent_at=datetime.utcnow() if status == 'sent' else None
            )
            
            session.add(alert)
            session.commit()
            
            return str(alert.id)
            
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to log alert: {e}")
            raise
        finally:
            session.close()

# Global database manager instance
_db_manager = None

def get_db_manager() -> DatabaseManager:
    """Get global database manager instance"""
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
    return _db_manager

def create_database_schema():
    """
    Create database schema - run this once during setup
    """
    db = get_db_manager()
    if db.engine:
        Base.metadata.create_all(bind=db.engine)
        logger.info("Database schema created successfully")
    else:
        logger.warning("Database not configured - schema creation skipped")

if __name__ == "__main__":
    create_database_schema()