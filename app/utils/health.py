"""
Health monitoring system for data collection sources.
Tracks source health, uptime, and provides dashboards metrics.
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List
from collections import defaultdict
import json

logger = logging.getLogger(__name__)


class SourceHealth:
    """Individual source health tracking."""
    
    def __init__(self, source_name: str, source_type: str = 'unknown'):
        self.source_name = source_name
        self.source_type = source_type
        self.last_fetch = None
        self.success_count = 0
        self.failure_count = 0
        self.last_error = None
        self.items_count = 0
        self.total_items_collected = 0
        self.total_items_failed = 0
        self.created_at = datetime.now()
    
    def record_success(self, items_count: int = 0):
        """Log successful fetch."""
        self.last_fetch = datetime.now()
        self.success_count += 1
        self.items_count = items_count
        self.total_items_collected += max(0, items_count)
        self.last_error = None
        logger.info(f"✓ {self.source_name}: Success ({items_count} items)")
    
    def record_failure(self, error: str):
        """Log failed fetch."""
        self.last_fetch = datetime.now()
        self.failure_count += 1
        self.last_error = error
        logger.error(f"✗ {self.source_name}: {error}")
    
    def is_healthy(self, timeout_hours: int = 2) -> bool:
        """Check if source is healthy (fetched recently and not too many failures)."""
        if self.last_fetch is None:
            return False
        
        time_since_last_fetch = datetime.now() - self.last_fetch
        is_fresh = time_since_last_fetch < timedelta(hours=timeout_hours)
        
        # If too many failures relative to successes, mark unhealthy
        if self.success_count > 0:
            failure_rate = self.failure_count / (self.success_count + self.failure_count)
            is_not_failing = failure_rate < 0.5
        else:
            is_not_failing = self.failure_count < 3
        
        return is_fresh and is_not_failing
    
    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive health statistics."""
        total_attempts = self.success_count + self.failure_count
        success_rate = (self.success_count / total_attempts * 100) if total_attempts > 0 else 0
        
        time_since_fetch = None
        if self.last_fetch:
            time_since_fetch = str(datetime.now() - self.last_fetch).split('.')[0]
        
        if total_attempts == 0:
            status = 'no_data'
        else:
            status = 'healthy' if self.is_healthy() else 'unhealthy'

        return {
            'source_name': self.source_name,
            'source_type': self.source_type,
            'status': status,
            'last_fetch': self.last_fetch.isoformat() if self.last_fetch else 'Never',
            'time_since_last_fetch': time_since_fetch,
            'success_count': self.success_count,
            'failure_count': self.failure_count,
            'total_attempts': total_attempts,
            'success_rate': f"{success_rate:.1f}%",
            'last_items_count': self.items_count,
            'total_items_collected': self.total_items_collected,
            'last_error': self.last_error or 'None',
            'uptime_days': (datetime.now() - self.created_at).days
        }


class HealthMonitor:
    """Central health monitoring system for all data sources."""
    
    def __init__(self):
        self.sources: Dict[str, SourceHealth] = {}
        self.collection_logs: List[Dict[str, Any]] = []
        self.max_logs = 1000  # Keep last 1000 logs
    
    def register_source(self, source_name: str, source_type: str = 'unknown') -> SourceHealth:
        """Register a new data source for monitoring."""
        if source_name not in self.sources:
            self.sources[source_name] = SourceHealth(source_name, source_type)
            logger.info(f"📊 Registered source for monitoring: {source_name}")
        return self.sources[source_name]
    
    def record_fetch(self, source_name: str, success: bool, items_count: int = 0, error: str = None):
        """Record a fetch attempt."""
        if source_name not in self.sources:
            self.register_source(source_name)
        
        source = self.sources[source_name]
        
        if success:
            source.record_success(items_count)
        else:
            source.record_failure(error or 'Unknown error')
        
        # Add to collection logs
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'source': source_name,
            'success': success,
            'items': items_count,
            'error': error
        }
        self.collection_logs.append(log_entry)
        
        # Keep only recent logs
        if len(self.collection_logs) > self.max_logs:
            self.collection_logs = self.collection_logs[-self.max_logs:]
    
    def get_source_health(self, source_name: str = None) -> Dict[str, Any]:
        """Get health stats for specific source or all sources."""
        if source_name:
            if source_name in self.sources:
                return self.sources[source_name].get_stats()
            return None
        else:
            return {name: health.get_stats() for name, health in self.sources.items()}
    
    def get_overall_health(self) -> Dict[str, Any]:
        """Get overall system health status."""
        if not self.sources:
            return {
                'overall_status': 'no_data',
                'message': 'No sources registered yet',
                'timestamp': datetime.now().isoformat(),
                'healthy_sources': 0,
                'active_sources': 0,
                'total_sources': 0,
                'health_percentage': '0.0%',
                'overall_success_rate': '0.0%',
                'total_attempts': 0,
                'best_performing': 'N/A',
                'worst_performing': 'N/A',
                'uptime': {
                    'successful_collections': 0,
                    'failed_collections': 0
                }
            }

        active_sources_list = [
            s for s in self.sources.values() if (s.success_count + s.failure_count) > 0
        ]
        active_sources = len(active_sources_list)
        healthy_sources = sum(1 for s in active_sources_list if s.is_healthy())
        total_sources = len(self.sources)
        
        overall_success_count = sum(s.success_count for s in self.sources.values())
        overall_failure_count = sum(s.failure_count for s in self.sources.values())
        total_attempts = overall_success_count + overall_failure_count
        overall_success_rate = (overall_success_count / total_attempts * 100) if total_attempts > 0 else 0
        
        if active_sources_list:
            worst_source = min(
                active_sources_list,
                key=lambda s: s.success_count - s.failure_count,
                default=None
            )
            best_source = max(
                active_sources_list,
                key=lambda s: s.success_count - s.failure_count,
                default=None
            )
            overall_status = 'healthy' if healthy_sources / active_sources >= 0.7 else 'degraded'
            health_percentage = f"{(healthy_sources / active_sources * 100):.1f}%"
        else:
            worst_source = None
            best_source = None
            overall_status = 'no_data'
            health_percentage = '0.0%'
        
        return {
            'timestamp': datetime.now().isoformat(),
            'overall_status': overall_status,
            'healthy_sources': healthy_sources,
            'active_sources': active_sources,
            'total_sources': total_sources,
            'health_percentage': health_percentage,
            'overall_success_rate': f"{overall_success_rate:.1f}%",
            'total_attempts': total_attempts,
            'best_performing': best_source.source_name if best_source else 'N/A',
            'worst_performing': worst_source.source_name if worst_source else 'N/A',
            'uptime': {
                'successful_collections': overall_success_count,
                'failed_collections': overall_failure_count
            }
        }
    
    def get_recent_logs(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent collection logs."""
        return self.collection_logs[-limit:]
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get all data needed for the health dashboard."""
        return {
            'overall_health': self.get_overall_health(),
            'sources_health': self.get_source_health(),
            'recent_logs': self.get_recent_logs(50),
            'timestamp': datetime.now().isoformat()
        }
    
    def export_health_report(self, filepath: str = None) -> str:
        """Export health report as JSON."""
        report = {
            'generated_at': datetime.now().isoformat(),
            'overall_health': self.get_overall_health(),
            'detailed_sources': self.get_source_health(),
            'recent_logs': self.get_recent_logs(100)
        }
        
        report_json = json.dumps(report, indent=2)
        
        if filepath:
            try:
                with open(filepath, 'w') as f:
                    f.write(report_json)
                logger.info(f"Health report exported to {filepath}")
            except Exception as e:
                logger.error(f"Failed to export health report: {e}")
        
        return report_json


# Global health monitor instance
health_monitor = HealthMonitor()

# Pre-register known sources
health_monitor.register_source('RSS - Ada Derana', 'RSS')
health_monitor.register_source('RSS - Daily Mirror', 'RSS')
health_monitor.register_source('RSS - Lanka Business Online', 'RSS')
health_monitor.register_source('RSS - News First', 'RSS')
health_monitor.register_source('NewsAPI', 'API')
health_monitor.register_source('GDELT', 'API')
health_monitor.register_source('WorldBank', 'API')
health_monitor.register_source('Reddit - srilanka', 'Social')
health_monitor.register_source('Reddit - Colombo', 'Social')
