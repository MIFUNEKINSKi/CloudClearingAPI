"""
CloudWatch Logs Integration for CloudClearingAPI

This module configures Python logging to stream to AWS CloudWatch Logs,
enabling centralized log aggregation, searching, and metric extraction.

Usage:
    from src.core.cloudwatch_logs import setup_cloudwatch_logging
    
    # Initialize CloudWatch Logs handler
    setup_cloudwatch_logging(
        log_group='/aws/ccapi/monitoring',
        stream_name='weekly-monitoring',
        enabled=True
    )
    
    # Use logger as normal
    import logging
    logger = logging.getLogger(__name__)
    logger.info("Processing region...")
    logger.error("Region failed", extra={'region': 'jakarta_north'})

Features:
    - Automatic log group creation
    - Batch log sending (reduces API calls)
    - JSON-structured logging for easy parsing
    - Retention policies (7-30 days)
    - Metric filters for ERROR/WARNING patterns
    - Graceful degradation if CloudWatch unavailable
"""

import logging
import os
import json
from datetime import datetime
from typing import Optional, Dict, Any

try:
    import watchtower
    from watchtower import CloudWatchLogHandler
    import boto3
    from botocore.exceptions import ClientError
    WATCHTOWER_AVAILABLE = True
except ImportError:
    WATCHTOWER_AVAILABLE = False


logger = logging.getLogger(__name__)


class CloudWatchLogsConfig:
    """Configuration for CloudWatch Logs integration"""
    
    # Log groups by component
    LOG_GROUPS = {
        'monitoring': '/aws/ccapi/monitoring',
        'scoring': '/aws/ccapi/scoring',
        'financial': '/aws/ccapi/financial',
        'pdf': '/aws/ccapi/pdf-generation',
        'dbt': '/aws/ccapi/dbt-analytics',
        'errors': '/aws/ccapi/errors',
        'cache': '/aws/ccapi/cache'
    }
    
    # Retention periods (days)
    RETENTION_POLICIES = {
        'monitoring': 7,
        'scoring': 7,
        'financial': 7,
        'pdf': 3,
        'dbt': 7,
        'errors': 30,
        'cache': 3
    }
    
    # Batch settings
    SEND_INTERVAL = 60  # seconds (batch logs every 60s)
    MAX_BATCH_SIZE = 10000  # bytes
    MAX_BATCH_COUNT = 10000  # log events
    
    # Stream name format
    STREAM_NAME_FORMAT = '{strftime:%Y-%m-%d}/{hostname}/{logger_name}'


class JSONFormatter(logging.Formatter):
    """
    Format log records as JSON for structured logging in CloudWatch.
    
    This enables CloudWatch Logs Insights queries like:
        fields @timestamp, level, message, region_name
        | filter level = "ERROR"
        | sort @timestamp desc
    """
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON string"""
        log_data = {
            'timestamp': datetime.utcfromtimestamp(record.created).isoformat() + 'Z',
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        
        # Add extra fields from logger.info(..., extra={'key': 'value'})
        if hasattr(record, '__dict__'):
            for key, value in record.__dict__.items():
                if key not in ['name', 'msg', 'args', 'created', 'filename', 'funcName',
                               'levelname', 'levelno', 'lineno', 'module', 'msecs',
                               'message', 'pathname', 'process', 'processName', 'relativeCreated',
                               'thread', 'threadName', 'exc_info', 'exc_text', 'stack_info']:
                    log_data[key] = value
        
        return json.dumps(log_data)


def setup_cloudwatch_logging(
    log_group: Optional[str] = None,
    stream_name: Optional[str] = None,
    enabled: Optional[bool] = None,
    log_level: int = logging.INFO,
    use_json: bool = True,
    region_name: str = 'us-east-1'
) -> bool:
    """
    Configure Python logging to stream to CloudWatch Logs.
    
    Args:
        log_group: CloudWatch log group name (e.g., '/aws/ccapi/monitoring')
                   If None, uses LOG_GROUPS['monitoring']
        stream_name: Log stream name pattern (supports strftime/hostname/logger_name)
                     If None, uses STREAM_NAME_FORMAT
        enabled: Enable CloudWatch logging (if None, reads from env var)
        log_level: Minimum log level to send (default: INFO)
        use_json: Use JSON formatting for structured logs
        region_name: AWS region for CloudWatch
    
    Returns:
        True if CloudWatch handler configured successfully, False otherwise
    
    Example:
        # Basic usage
        setup_cloudwatch_logging()
        
        # Custom configuration
        setup_cloudwatch_logging(
            log_group='/aws/ccapi/custom',
            stream_name='my-stream',
            log_level=logging.DEBUG
        )
    """
    # Check if enabled
    if enabled is None:
        enabled = os.getenv('CLOUDWATCH_LOGS_ENABLED', 'false').lower() == 'true'
    
    if not enabled:
        logger.info("ℹ️  CloudWatch Logs disabled by configuration")
        return False
    
    if not WATCHTOWER_AVAILABLE:
        logger.warning("⚠️ CloudWatch Logs unavailable (watchtower not installed)")
        logger.info("Install with: pip install watchtower")
        return False
    
    # Use defaults if not specified
    if log_group is None:
        log_group = CloudWatchLogsConfig.LOG_GROUPS['monitoring']
    
    if stream_name is None:
        stream_name = CloudWatchLogsConfig.STREAM_NAME_FORMAT
    
    try:
        # Create CloudWatch Logs client
        logs_client = boto3.client('logs', region_name=region_name)
        
        # Try to create log group (idempotent)
        try:
            logs_client.create_log_group(logGroupName=log_group)
            logger.info(f"✅ Created CloudWatch log group: {log_group}")
        except ClientError as e:
            if e.response['Error']['Code'] != 'ResourceAlreadyExistsException':
                raise
        
        # Set retention policy
        component = _get_component_from_log_group(log_group)
        retention_days = CloudWatchLogsConfig.RETENTION_POLICIES.get(component, 7)
        try:
            logs_client.put_retention_policy(
                logGroupName=log_group,
                retentionInDays=retention_days
            )
        except ClientError:
            pass  # Ignore if already set
        
        # Create CloudWatch handler
        handler = CloudWatchLogHandler(
            log_group=log_group,
            stream_name=stream_name,
            send_interval=CloudWatchLogsConfig.SEND_INTERVAL,
            max_batch_size=CloudWatchLogsConfig.MAX_BATCH_SIZE,
            max_batch_count=CloudWatchLogsConfig.MAX_BATCH_COUNT,
            create_log_group=True,
            boto3_client=logs_client
        )
        
        # Set formatter
        if use_json:
            handler.setFormatter(JSONFormatter())
        else:
            handler.setFormatter(logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            ))
        
        handler.setLevel(log_level)
        
        # Add handler to root logger
        root_logger = logging.getLogger()
        root_logger.addHandler(handler)
        
        logger.info(f"✅ CloudWatch Logs enabled: {log_group}")
        logger.info(f"   Stream: {stream_name}")
        logger.info(f"   Retention: {retention_days} days")
        logger.info(f"   Format: {'JSON' if use_json else 'Text'}")
        
        return True
        
    except Exception as e:
        logger.warning(f"⚠️ Failed to setup CloudWatch Logs: {e}")
        return False


def setup_error_log_group(region_name: str = 'us-east-1') -> bool:
    """
    Configure separate log group for ERROR-level logs only.
    This enables quick filtering of critical issues.
    
    Args:
        region_name: AWS region
    
    Returns:
        True if configured successfully
    """
    error_log_group = CloudWatchLogsConfig.LOG_GROUPS['errors']
    
    return setup_cloudwatch_logging(
        log_group=error_log_group,
        stream_name='{strftime:%Y-%m-%d}/errors/{logger_name}',
        log_level=logging.ERROR,
        use_json=True,
        region_name=region_name
    )


def create_metric_filters(region_name: str = 'us-east-1') -> Dict[str, bool]:
    """
    Create CloudWatch metric filters to extract metrics from logs.
    
    Metric filters automatically create metrics from log patterns:
        - ErrorCount: Count ERROR-level logs
        - WarningCount: Count WARNING-level logs
        - SlowRegionCount: Count regions with >180s processing time
        - GEETimeoutCount: Count GEE timeout errors
        - ScrapingFailureCount: Count scraping failures
    
    Args:
        region_name: AWS region
    
    Returns:
        Dict mapping filter name to success status
    """
    if not WATCHTOWER_AVAILABLE:
        logger.warning("CloudWatch Logs unavailable, cannot create metric filters")
        return {}
    
    try:
        logs_client = boto3.client('logs', region_name=region_name)
        results = {}
        
        # Filter 1: Count ERROR logs
        try:
            logs_client.put_metric_filter(
                logGroupName=CloudWatchLogsConfig.LOG_GROUPS['monitoring'],
                filterName='ErrorCount',
                filterPattern='[timestamp, level=ERROR*, ...]',
                metricTransformations=[{
                    'metricName': 'ErrorCount',
                    'metricNamespace': 'CCAPI/Monitoring',
                    'metricValue': '1',
                    'defaultValue': 0.0
                }]
            )
            results['ErrorCount'] = True
        except Exception as e:
            logger.warning(f"Failed to create ErrorCount metric filter: {e}")
            results['ErrorCount'] = False
        
        # Filter 2: Count WARNING logs
        try:
            logs_client.put_metric_filter(
                logGroupName=CloudWatchLogsConfig.LOG_GROUPS['monitoring'],
                filterName='WarningCount',
                filterPattern='[timestamp, level=WARNING*, ...]',
                metricTransformations=[{
                    'metricName': 'WarningCount',
                    'metricNamespace': 'CCAPI/Monitoring',
                    'metricValue': '1',
                    'defaultValue': 0.0
                }]
            )
            results['WarningCount'] = True
        except Exception as e:
            logger.warning(f"Failed to create WarningCount metric filter: {e}")
            results['WarningCount'] = False
        
        # Filter 3: Count slow regions (>180 seconds)
        try:
            logs_client.put_metric_filter(
                logGroupName=CloudWatchLogsConfig.LOG_GROUPS['monitoring'],
                filterName='SlowRegionCount',
                filterPattern='[timestamp, level, logger, message="*processing time*", duration>180]',
                metricTransformations=[{
                    'metricName': 'SlowRegionCount',
                    'metricNamespace': 'CCAPI/Monitoring',
                    'metricValue': '1',
                    'defaultValue': 0.0
                }]
            )
            results['SlowRegionCount'] = True
        except Exception as e:
            logger.warning(f"Failed to create SlowRegionCount metric filter: {e}")
            results['SlowRegionCount'] = False
        
        # Filter 4: Count GEE timeouts
        try:
            logs_client.put_metric_filter(
                logGroupName=CloudWatchLogsConfig.LOG_GROUPS['errors'],
                filterName='GEETimeoutCount',
                filterPattern='[timestamp, level=ERROR, ..., message="*GEE*timeout*" || message="*Earth Engine*timeout*"]',
                metricTransformations=[{
                    'metricName': 'GEETimeoutCount',
                    'metricNamespace': 'CCAPI/Monitoring',
                    'metricValue': '1',
                    'defaultValue': 0.0,
                    'dimensions': {
                        'ErrorType': 'GEETimeout'
                    }
                }]
            )
            results['GEETimeoutCount'] = True
        except Exception as e:
            logger.warning(f"Failed to create GEETimeoutCount metric filter: {e}")
            results['GEETimeoutCount'] = False
        
        # Filter 5: Count scraping failures
        try:
            logs_client.put_metric_filter(
                logGroupName=CloudWatchLogsConfig.LOG_GROUPS['errors'],
                filterName='ScrapingFailureCount',
                filterPattern='[timestamp, level=ERROR, ..., message="*scraping*failed*" || message="*ScrapingFailed*"]',
                metricTransformations=[{
                    'metricName': 'ScrapingFailureCount',
                    'metricNamespace': 'CCAPI/Monitoring',
                    'metricValue': '1',
                    'defaultValue': 0.0,
                    'dimensions': {
                        'ErrorType': 'ScrapingFailed'
                    }
                }]
            )
            results['ScrapingFailureCount'] = True
        except Exception as e:
            logger.warning(f"Failed to create ScrapingFailureCount metric filter: {e}")
            results['ScrapingFailureCount'] = False
        
        logger.info(f"✅ Created {sum(results.values())}/{len(results)} metric filters")
        return results
        
    except Exception as e:
        logger.error(f"Failed to create metric filters: {e}")
        return {}


def _get_component_from_log_group(log_group: str) -> str:
    """Extract component name from log group path"""
    for component, group_path in CloudWatchLogsConfig.LOG_GROUPS.items():
        if log_group == group_path:
            return component
    return 'monitoring'  # default


# Convenience function for quick setup
def enable_cloudwatch_logs() -> bool:
    """
    Quick setup function for CloudWatch Logs.
    Reads configuration from environment variables.
    
    Environment Variables:
        CLOUDWATCH_LOGS_ENABLED: 'true' to enable
        CLOUDWATCH_LOG_GROUP: Override default log group
        CLOUDWATCH_LOG_LEVEL: DEBUG, INFO, WARNING, ERROR
        AWS_REGION: AWS region (default: us-east-1)
    
    Returns:
        True if configured successfully
    """
    log_group = os.getenv('CLOUDWATCH_LOG_GROUP')
    log_level_str = os.getenv('CLOUDWATCH_LOG_LEVEL', 'INFO')
    log_level = getattr(logging, log_level_str.upper(), logging.INFO)
    region = os.getenv('AWS_REGION', 'us-east-1')
    
    success = setup_cloudwatch_logging(
        log_group=log_group,
        log_level=log_level,
        region_name=region
    )
    
    if success:
        # Also setup error log group
        setup_error_log_group(region_name=region)
        
        # Create metric filters
        create_metric_filters(region_name=region)
    
    return success
