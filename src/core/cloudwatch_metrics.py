"""
CloudWatch Metrics Client for CloudClearingAPI

This module provides a wrapper around AWS CloudWatch metrics to emit custom
monitoring data from the pipeline. All metrics are sent to the 'CCAPI/Monitoring'
namespace with appropriate dimensions for filtering and aggregation.

Usage:
    from src.core.cloudwatch_metrics import CloudWatchMetrics
    
    metrics = CloudWatchMetrics(enabled=True)
    
    # Emit single metric
    metrics.emit_region_processing_time(
        region_name='jakarta_north_sprawl',
        duration_seconds=45.2
    )
    
    # Emit batch metrics
    metrics.flush()  # Send any buffered metrics

Architecture:
    - Namespace: CCAPI/Monitoring
    - Dimensions: RegionName, Pipeline Stage, DataSource, etc.
    - Buffering: Metrics are buffered and sent in batches to reduce API calls
    - Error Handling: Never raises exceptions (degrades gracefully)
"""

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum

try:
    import boto3
    from botocore.exceptions import ClientError, BotoCoreError
    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False
    logging.warning("boto3 not installed. CloudWatch metrics will be disabled.")


logger = logging.getLogger(__name__)


class PipelineStage(Enum):
    """Pipeline stages for dimensional filtering"""
    SCORING = "Scoring"
    FINANCIAL = "Financial"
    PDF_GENERATION = "PDFGeneration"
    DBT_ANALYTICS = "dbtAnalytics"
    COMPLETE_PIPELINE = "CompletePipeline"


class DataSource(Enum):
    """Data sources for availability tracking"""
    GEE_SATELLITE = "GoogleEarthEngine"
    OSM_INFRASTRUCTURE = "OpenStreetMap"
    LAMUDI = "Lamudi"
    RUMAH = "Rumah.com"
    NINETY_NINE = "99.co"
    STATIC_BENCHMARK = "StaticBenchmark"
    CACHE = "Cache"


@dataclass
class MetricData:
    """Represents a single CloudWatch metric data point"""
    metric_name: str
    value: float
    unit: str
    dimensions: Dict[str, str] = field(default_factory=dict)
    timestamp: Optional[datetime] = None


class CloudWatchMetrics:
    """
    CloudWatch metrics client with buffering and error handling.
    
    All methods are safe to call even if CloudWatch is unavailable - they will
    log warnings but never crash the pipeline.
    """
    
    NAMESPACE = "CCAPI/Monitoring"
    MAX_BATCH_SIZE = 20  # CloudWatch API limit per PutMetricData call
    
    def __init__(
        self,
        enabled: bool = True,
        region_name: str = "us-east-1",
        buffer_size: int = 10,
        auto_flush: bool = True
    ):
        """
        Initialize CloudWatch metrics client.
        
        Args:
            enabled: If False, all metric operations are no-ops
            region_name: AWS region for CloudWatch API
            buffer_size: Number of metrics to buffer before auto-flush
            auto_flush: Automatically flush when buffer reaches buffer_size
        """
        self.enabled = enabled and BOTO3_AVAILABLE
        self.region_name = region_name
        self.buffer_size = buffer_size
        self.auto_flush = auto_flush
        self._buffer: List[MetricData] = []
        
        if self.enabled:
            try:
                self.client = boto3.client('cloudwatch', region_name=region_name)
                logger.info(f"✅ CloudWatch metrics enabled (namespace: {self.NAMESPACE})")
            except Exception as e:
                logger.warning(f"Failed to initialize CloudWatch client: {e}")
                self.enabled = False
        else:
            self.client = None
            if not BOTO3_AVAILABLE:
                logger.warning("⚠️ CloudWatch metrics disabled (boto3 not installed)")
            else:
                logger.info("⚠️ CloudWatch metrics disabled by configuration")
    
    def _add_to_buffer(self, metric: MetricData) -> None:
        """Add metric to buffer and auto-flush if needed"""
        if not self.enabled:
            return
        
        self._buffer.append(metric)
        
        if self.auto_flush and len(self._buffer) >= self.buffer_size:
            self.flush()
    
    def flush(self) -> bool:
        """
        Send all buffered metrics to CloudWatch.
        
        Returns:
            True if successful, False otherwise
        """
        if not self.enabled or not self._buffer:
            return True
        
        try:
            # Split into batches of MAX_BATCH_SIZE
            for i in range(0, len(self._buffer), self.MAX_BATCH_SIZE):
                batch = self._buffer[i:i + self.MAX_BATCH_SIZE]
                
                metric_data = [
                    {
                        'MetricName': m.metric_name,
                        'Value': m.value,
                        'Unit': m.unit,
                        'Timestamp': m.timestamp or datetime.utcnow(),
                        'Dimensions': [
                            {'Name': k, 'Value': v}
                            for k, v in m.dimensions.items()
                        ]
                    }
                    for m in batch
                ]
                
                self.client.put_metric_data(
                    Namespace=self.NAMESPACE,
                    MetricData=metric_data
                )
            
            logger.debug(f"📊 Flushed {len(self._buffer)} metrics to CloudWatch")
            self._buffer.clear()
            return True
            
        except (ClientError, BotoCoreError) as e:
            logger.warning(f"Failed to send metrics to CloudWatch: {e}")
            self._buffer.clear()  # Discard to prevent memory buildup
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending metrics: {e}")
            self._buffer.clear()
            return False
    
    # =============================================================================
    # PIPELINE PERFORMANCE METRICS
    # =============================================================================
    
    def emit_region_processing_time(
        self,
        region_name: str,
        duration_seconds: float,
        stage: Optional[PipelineStage] = None
    ) -> None:
        """
        Track how long it takes to process a region.
        
        Args:
            region_name: Region identifier
            duration_seconds: Processing time in seconds
            stage: Pipeline stage (None = complete pipeline)
        """
        dimensions = {'RegionName': region_name}
        if stage:
            dimensions['Stage'] = stage.value
        
        metric = MetricData(
            metric_name='RegionProcessingTime',
            value=duration_seconds,
            unit='Seconds',
            dimensions=dimensions
        )
        self._add_to_buffer(metric)
    
    def emit_batch_processing_time(
        self,
        region_count: int,
        duration_seconds: float
    ) -> None:
        """
        Track total processing time for a batch of regions.
        
        Args:
            region_count: Number of regions processed
            duration_seconds: Total processing time
        """
        metric = MetricData(
            metric_name='BatchProcessingTime',
            value=duration_seconds,
            unit='Seconds',
            dimensions={'RegionCount': str(region_count)}
        )
        self._add_to_buffer(metric)
    
    def emit_regions_processed(self, count: int, success: bool = True) -> None:
        """
        Track number of regions processed successfully or failed.
        
        Args:
            count: Number of regions
            success: True for successful, False for failed
        """
        metric = MetricData(
            metric_name='RegionsProcessed',
            value=count,
            unit='Count',
            dimensions={'Status': 'Success' if success else 'Failed'}
        )
        self._add_to_buffer(metric)
    
    # =============================================================================
    # CACHE PERFORMANCE METRICS
    # =============================================================================
    
    def emit_cache_hit_rate(
        self,
        data_source: DataSource,
        hit_count: int,
        total_count: int
    ) -> None:
        """
        Track cache hit rate for different data sources.
        
        Args:
            data_source: Which cache (GEE, OSM, etc.)
            hit_count: Number of cache hits
            total_count: Total number of requests
        """
        if total_count == 0:
            return
        
        hit_rate = (hit_count / total_count) * 100
        
        metric = MetricData(
            metric_name='CacheHitRate',
            value=hit_rate,
            unit='Percent',
            dimensions={'DataSource': data_source.value}
        )
        self._add_to_buffer(metric)
    
    def emit_cache_size(self, data_source: DataSource, size_mb: float) -> None:
        """
        Track cache storage size.
        
        Args:
            data_source: Which cache
            size_mb: Size in megabytes
        """
        metric = MetricData(
            metric_name='CacheSize',
            value=size_mb,
            unit='Megabytes',
            dimensions={'DataSource': data_source.value}
        )
        self._add_to_buffer(metric)
    
    # =============================================================================
    # DATA AVAILABILITY METRICS
    # =============================================================================
    
    def emit_data_availability(
        self,
        data_source: DataSource,
        available: bool,
        region_name: Optional[str] = None
    ) -> None:
        """
        Track whether data sources are available.
        
        Args:
            data_source: Which data source
            available: True if data retrieved successfully
            region_name: Optional region filter
        """
        dimensions = {
            'DataSource': data_source.value,
            'Status': 'Available' if available else 'Unavailable'
        }
        if region_name:
            dimensions['RegionName'] = region_name
        
        metric = MetricData(
            metric_name='DataAvailability',
            value=1.0 if available else 0.0,
            unit='None',
            dimensions=dimensions
        )
        self._add_to_buffer(metric)
    
    def emit_scraping_success_rate(
        self,
        data_source: DataSource,
        success_count: int,
        total_count: int
    ) -> None:
        """
        Track web scraping success rate.
        
        Args:
            data_source: Which scraper (Lamudi, Rumah, 99.co)
            success_count: Number of successful scrapes
            total_count: Total scrape attempts
        """
        if total_count == 0:
            return
        
        success_rate = (success_count / total_count) * 100
        
        metric = MetricData(
            metric_name='ScrapingSuccessRate',
            value=success_rate,
            unit='Percent',
            dimensions={'DataSource': data_source.value}
        )
        self._add_to_buffer(metric)
    
    # =============================================================================
    # INVESTMENT SIGNAL QUALITY METRICS
    # =============================================================================
    
    def emit_investment_score(
        self,
        region_name: str,
        score: float,
        confidence: float,
        recommendation: str
    ) -> None:
        """
        Track investment scores and confidence levels.
        
        Args:
            region_name: Region identifier
            score: Final investment score (0-100)
            confidence: Confidence level (0-1)
            recommendation: BUY/WATCH/PASS
        """
        # Score metric
        score_metric = MetricData(
            metric_name='InvestmentScore',
            value=score,
            unit='None',
            dimensions={
                'RegionName': region_name,
                'Recommendation': recommendation
            }
        )
        self._add_to_buffer(score_metric)
        
        # Confidence metric
        confidence_metric = MetricData(
            metric_name='ScoreConfidence',
            value=confidence * 100,
            unit='Percent',
            dimensions={'RegionName': region_name}
        )
        self._add_to_buffer(confidence_metric)
    
    def emit_recommendation_count(
        self,
        recommendation: str,
        count: int
    ) -> None:
        """
        Track number of BUY/WATCH/PASS recommendations.
        
        Args:
            recommendation: BUY/WATCH/PASS
            count: Number of regions with this recommendation
        """
        metric = MetricData(
            metric_name='RecommendationCount',
            value=count,
            unit='Count',
            dimensions={'Recommendation': recommendation}
        )
        self._add_to_buffer(metric)
    
    def emit_satellite_changes(
        self,
        region_name: str,
        total_changes: int,
        area_hectares: float
    ) -> None:
        """
        Track satellite-detected changes.
        
        Args:
            region_name: Region identifier
            total_changes: Total pixel changes detected
            area_hectares: Area affected in hectares
        """
        changes_metric = MetricData(
            metric_name='SatelliteChanges',
            value=total_changes,
            unit='Count',
            dimensions={'RegionName': region_name}
        )
        self._add_to_buffer(changes_metric)
        
        area_metric = MetricData(
            metric_name='AreaChanged',
            value=area_hectares,
            unit='None',
            dimensions={'RegionName': region_name}
        )
        self._add_to_buffer(area_metric)
    
    # =============================================================================
    # FINANCIAL METRICS
    # =============================================================================
    
    def emit_financial_projection_success(
        self,
        region_name: str,
        success: bool,
        data_source: Optional[str] = None
    ) -> None:
        """
        Track financial projection calculation success/failure.
        
        Args:
            region_name: Region identifier
            success: True if projection calculated
            data_source: Source of land price data
        """
        dimensions = {
            'RegionName': region_name,
            'Status': 'Success' if success else 'Failed'
        }
        if data_source:
            dimensions['DataSource'] = data_source
        
        metric = MetricData(
            metric_name='FinancialProjectionSuccess',
            value=1.0 if success else 0.0,
            unit='None',
            dimensions=dimensions
        )
        self._add_to_buffer(metric)
    
    def emit_roi_projection(
        self,
        region_name: str,
        roi_3yr: float,
        rvi: Optional[float] = None
    ) -> None:
        """
        Track ROI projections for investment opportunities.
        
        Args:
            region_name: Region identifier
            roi_3yr: 3-year ROI projection (%)
            rvi: Relative Value Index (optional)
        """
        roi_metric = MetricData(
            metric_name='ROIProjection',
            value=roi_3yr,
            unit='Percent',
            dimensions={'RegionName': region_name}
        )
        self._add_to_buffer(roi_metric)
        
        if rvi is not None:
            rvi_metric = MetricData(
                metric_name='RelativeValueIndex',
                value=rvi,
                unit='None',
                dimensions={'RegionName': region_name}
            )
            self._add_to_buffer(rvi_metric)
    
    # =============================================================================
    # ERROR AND ALERT METRICS
    # =============================================================================
    
    def emit_error_count(
        self,
        error_type: str,
        stage: PipelineStage,
        region_name: Optional[str] = None
    ) -> None:
        """
        Track errors by type and stage.
        
        Args:
            error_type: Type of error (GEETimeout, ScrapingFailed, etc.)
            stage: Pipeline stage where error occurred
            region_name: Optional region identifier
        """
        dimensions = {
            'ErrorType': error_type,
            'Stage': stage.value
        }
        if region_name:
            dimensions['RegionName'] = region_name
        
        metric = MetricData(
            metric_name='ErrorCount',
            value=1.0,
            unit='Count',
            dimensions=dimensions
        )
        self._add_to_buffer(metric)
    
    def emit_pdf_generation_time(self, duration_seconds: float) -> None:
        """
        Track PDF report generation time.
        
        Args:
            duration_seconds: Time to generate PDF
        """
        metric = MetricData(
            metric_name='PDFGenerationTime',
            value=duration_seconds,
            unit='Seconds',
            dimensions={'Stage': 'PDFGeneration'}
        )
        self._add_to_buffer(metric)
    
    def emit_dbt_run_time(
        self,
        duration_seconds: float,
        models_run: int,
        success: bool
    ) -> None:
        """
        Track dbt transformation execution.
        
        Args:
            duration_seconds: Time for dbt run
            models_run: Number of models executed
            success: True if dbt run succeeded
        """
        time_metric = MetricData(
            metric_name='DbtRunTime',
            value=duration_seconds,
            unit='Seconds',
            dimensions={
                'Stage': 'dbtAnalytics',
                'Status': 'Success' if success else 'Failed'
            }
        )
        self._add_to_buffer(time_metric)
        
        models_metric = MetricData(
            metric_name='DbtModelsRun',
            value=models_run,
            unit='Count',
            dimensions={'Status': 'Success' if success else 'Failed'}
        )
        self._add_to_buffer(models_metric)
    
    # =============================================================================
    # UTILITY METHODS
    # =============================================================================
    
    def __enter__(self):
        """Context manager support"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Flush on context exit"""
        self.flush()
        return False  # Don't suppress exceptions


# Singleton instance for global access
_global_metrics_client: Optional[CloudWatchMetrics] = None


def get_metrics_client() -> CloudWatchMetrics:
    """
    Get or create the global metrics client.
    
    Returns:
        CloudWatchMetrics instance
    """
    global _global_metrics_client
    if _global_metrics_client is None:
        # Check if CloudWatch should be enabled from environment
        import os
        enabled = os.getenv('CLOUDWATCH_METRICS_ENABLED', 'true').lower() == 'true'
        region = os.getenv('AWS_REGION', 'us-east-1')
        
        _global_metrics_client = CloudWatchMetrics(
            enabled=enabled,
            region_name=region,
            buffer_size=10,
            auto_flush=True
        )
    
    return _global_metrics_client
