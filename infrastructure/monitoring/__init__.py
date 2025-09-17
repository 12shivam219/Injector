"""
Monitoring package for Resume Customizer application.
Provides metrics collection, analytics, progress tracking, and caching functionality.
"""

from .metrics import (
    Metric,
    MetricType,
    MetricValue,
    MetricsManager,
    get_metrics_manager
)

from .analytics import (
    AnalyticsManager,
    UserActivity,
    SystemMetrics,
    get_analytics_manager
)

from .circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerError,
    get_circuit_breaker
)

from .email_templates import (
    EmailTemplate,
    TemplateManager,
    get_template_manager
)

from .progress import (
    ProgressTracker,
    TaskStatus,
    TaskProgress,
    get_progress_tracker
)

from .advanced_cache import (
    CacheLevel,
    CacheStats,
    AdvancedCacheManager,
    get_advanced_cache_manager,
    cached
)

__all__ = [
    'Metric',
    'MetricType',
    'MetricValue',
    'MetricsManager',
    'get_metrics_manager',
    'AnalyticsManager',
    'UserActivity',
    'SystemMetrics',
    'get_analytics_manager',
    'ProgressTracker',
    'TaskStatus',
    'TaskProgress',
    'get_progress_tracker',
    'CacheLevel',
    'CacheStats',
    'AdvancedCacheManager',
    'get_advanced_cache_manager',
    'cached'
]