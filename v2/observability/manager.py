"""
Yamazaki v2 - Observability Manager

Manages logging, tracing, and metrics.
"""

from typing import Optional
import logging

from .logger import setup_logging, get_logger


class ObservabilityManager:
    """
    Manages observability for the application.

    Handles logging, tracing, and metrics setup and coordination.
    """

    def __init__(self, config):
        """
        Initialize observability manager.

        Args:
            config: ObservabilityConfig
        """
        self.config = config
        self.logger: Optional[logging.Logger] = None
        self._initialized = False

    def initialize(self):
        """Initialize logging, tracing, and metrics"""
        if self._initialized:
            return

        # Setup structured logging
        self.logger = setup_logging(self.config)
        self.logger.info("🚀 Yamazaki v2 starting up")

        # Setup OpenTelemetry (if enabled)
        if self.config.enable_telemetry:
            self._setup_telemetry()

        # Setup metrics (if enabled)
        if self.config.enable_metrics:
            self._setup_metrics()

        self._initialized = True

    def _setup_telemetry(self):
        """Setup OpenTelemetry tracing"""
        try:
            from opentelemetry import trace
            from opentelemetry.sdk.trace import TracerProvider
            from opentelemetry.sdk.resources import Resource

            # Create resource
            resource = Resource.create({
                "service.name": self.config.service_name,
                "service.version": "2.0.0",
            })

            # Create tracer provider
            provider = TracerProvider(resource=resource)
            trace.set_tracer_provider(provider)

            self.logger.info("✓ OpenTelemetry tracing enabled")

        except ImportError:
            self.logger.warning(
                "OpenTelemetry not installed. Install with: pip install opentelemetry-api opentelemetry-sdk"
            )

    def _setup_metrics(self):
        """Setup Prometheus metrics"""
        try:
            from opentelemetry import metrics
            from opentelemetry.sdk.metrics import MeterProvider

            # Create meter provider
            provider = MeterProvider()
            metrics.set_meter_provider(provider)

            self.logger.info(f"✓ Metrics enabled (port {self.config.metrics_port})")

        except ImportError:
            self.logger.warning(
                "OpenTelemetry metrics not available. Install with: pip install opentelemetry-api opentelemetry-sdk"
            )

    def get_logger(self, name: str = "yamazaki") -> logging.Logger:
        """
        Get logger instance.

        Args:
            name: Logger name

        Returns:
            Logger instance
        """
        if not self._initialized:
            self.initialize()

        return get_logger(name)

    async def shutdown(self):
        """Shutdown observability (flush logs, close exporters)"""
        if self.logger:
            self.logger.info("👋 Yamazaki v2 shutting down")

        # Flush and cleanup
        logging.shutdown()

    def __repr__(self) -> str:
        return f"ObservabilityManager(service={self.config.service_name})"
