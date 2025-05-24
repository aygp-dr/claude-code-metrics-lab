#!/usr/bin/env python3
"""
Configurable Logging Proxy for Claude Code Metrics

Simulates a pass-through to Prometheus logger with payload verification
and detailed logging for debugging and monitoring purposes.
"""

import json
import logging
import time
from datetime import datetime
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, asdict
from pathlib import Path
import yaml


@dataclass
class MetricConfig:
    """Configuration for metric collection and validation"""
    name: str
    metric_type: str  # counter, gauge, histogram, summary
    labels: List[str]
    validation_rules: Dict[str, Any]
    prometheus_format: str
    description: str = ""


@dataclass
class ProxyConfig:
    """Main configuration for the logging proxy"""
    enabled: bool = True
    log_level: str = "INFO"
    output_format: str = "json"  # json, prometheus, both
    verify_payloads: bool = True
    simulate_prometheus: bool = True
    metrics: Dict[str, MetricConfig] = None
    thresholds: Dict[str, float] = None
    export_path: str = "exports/proxy_logs"


class PrometheusSimulator:
    """Simulates Prometheus metrics collection and formatting"""
    
    def __init__(self, config: ProxyConfig):
        self.config = config
        self.metrics_store = {}
        self.logger = logging.getLogger(f"{__name__}.simulator")
    
    def format_metric(self, metric_name: str, value: Union[int, float], 
                     labels: Dict[str, str] = None, timestamp: float = None) -> str:
        """Format metric in Prometheus exposition format"""
        labels_str = ""
        if labels:
            label_pairs = [f'{k}="{v}"' for k, v in labels.items()]
            labels_str = "{" + ",".join(label_pairs) + "}"
        
        timestamp_str = ""
        if timestamp:
            timestamp_str = f" {int(timestamp * 1000)}"
        
        return f"{metric_name}{labels_str} {value}{timestamp_str}"
    
    def validate_metric(self, metric_name: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Validate metric payload against configuration rules"""
        validation_result = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "metric_name": metric_name
        }
        
        if not self.config.metrics or metric_name not in self.config.metrics:
            validation_result["warnings"].append(f"No validation rules for metric: {metric_name}")
            return validation_result
        
        metric_config = self.config.metrics[metric_name]
        rules = metric_config.validation_rules
        
        # Validate required fields
        if "required_fields" in rules:
            for field in rules["required_fields"]:
                if field not in payload:
                    validation_result["valid"] = False
                    validation_result["errors"].append(f"Missing required field: {field}")
        
        # Validate value ranges
        if "value_range" in rules and "value" in payload:
            min_val, max_val = rules["value_range"]
            if not (min_val <= payload["value"] <= max_val):
                validation_result["valid"] = False
                validation_result["errors"].append(
                    f"Value {payload['value']} outside range [{min_val}, {max_val}]"
                )
        
        # Validate label requirements
        if "required_labels" in rules:
            labels = payload.get("labels", {})
            for label in rules["required_labels"]:
                if label not in labels:
                    validation_result["valid"] = False
                    validation_result["errors"].append(f"Missing required label: {label}")
        
        return validation_result
    
    def store_metric(self, metric_name: str, value: Union[int, float], 
                    labels: Dict[str, str] = None, timestamp: float = None):
        """Store metric in internal metrics store"""
        if timestamp is None:
            timestamp = time.time()
        
        key = f"{metric_name}_{hash(str(labels))}"
        self.metrics_store[key] = {
            "name": metric_name,
            "value": value,
            "labels": labels or {},
            "timestamp": timestamp,
            "formatted": self.format_metric(metric_name, value, labels, timestamp)
        }


class LoggingProxy:
    """Main logging proxy class for Claude Code metrics"""
    
    def __init__(self, config_path: Optional[str] = None):
        self.config = self._load_config(config_path)
        self.simulator = PrometheusSimulator(self.config)
        self.logger = self._setup_logging()
        self.session_data = []
        
        # Ensure export directory exists
        Path(self.config.export_path).mkdir(parents=True, exist_ok=True)
    
    def _load_config(self, config_path: Optional[str] = None) -> ProxyConfig:
        """Load configuration from file or use defaults"""
        if config_path and Path(config_path).exists():
            with open(config_path, 'r') as f:
                config_data = yaml.safe_load(f)
            
            # Convert metrics dict to MetricConfig objects
            metrics = {}
            if "metrics" in config_data:
                for name, metric_data in config_data["metrics"].items():
                    metrics[name] = MetricConfig(**metric_data)
            
            config_data["metrics"] = metrics
            return ProxyConfig(**config_data)
        else:
            return self._get_default_config()
    
    def _get_default_config(self) -> ProxyConfig:
        """Get default configuration for Claude Code metrics"""
        return ProxyConfig(
            enabled=True,
            log_level="INFO",
            output_format="both",
            verify_payloads=True,
            simulate_prometheus=True,
            metrics={
                "otel_claude_code_token_usage_tokens_total": MetricConfig(
                    name="otel_claude_code_token_usage_tokens_total",
                    metric_type="counter",
                    labels=["model", "token_type", "session_id"],
                    validation_rules={
                        "required_fields": ["value", "labels"],
                        "required_labels": ["model", "token_type"],
                        "value_range": [0, 1000000]
                    },
                    prometheus_format="# HELP otel_claude_code_token_usage_tokens_total Total tokens used\n# TYPE otel_claude_code_token_usage_tokens_total counter"
                ),
                "otel_claude_code_session_duration_seconds": MetricConfig(
                    name="otel_claude_code_session_duration_seconds",
                    metric_type="histogram",
                    labels=["session_id", "status"],
                    validation_rules={
                        "required_fields": ["value"],
                        "value_range": [0, 86400]  # Max 24 hours
                    },
                    prometheus_format="# HELP otel_claude_code_session_duration_seconds Session duration\n# TYPE otel_claude_code_session_duration_seconds histogram"
                ),
                "otel_claude_code_cost_usd": MetricConfig(
                    name="otel_claude_code_cost_usd",
                    metric_type="gauge",
                    labels=["model", "session_id"],
                    validation_rules={
                        "required_fields": ["value"],
                        "value_range": [0, 1000]  # Max $1000
                    },
                    prometheus_format="# HELP otel_claude_code_cost_usd Estimated cost in USD\n# TYPE otel_claude_code_cost_usd gauge"
                )
            },
            thresholds={
                "max_tokens_per_minute": 10000,
                "max_cost_per_hour": 10.0,
                "max_session_duration": 3600
            }
        )
    
    def _setup_logging(self) -> logging.Logger:
        """Setup logging configuration"""
        logger = logging.getLogger(f"{__name__}.proxy")
        logger.setLevel(getattr(logging, self.config.log_level))
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(getattr(logging, self.config.log_level))
        
        # File handler (ensure directory exists)
        log_file = Path(self.config.export_path) / "proxy.log"
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        
        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(formatter)
        file_handler.setFormatter(formatter)
        
        logger.addHandler(console_handler)
        logger.addHandler(file_handler)
        
        return logger
    
    def log_metric(self, metric_name: str, value: Union[int, float], 
                  labels: Dict[str, str] = None, metadata: Dict[str, Any] = None):
        """Log a metric with validation and formatting"""
        if not self.config.enabled:
            return
        
        timestamp = time.time()
        labels = labels or {}
        metadata = metadata or {}
        
        # Create payload
        payload = {
            "metric_name": metric_name,
            "value": value,
            "labels": labels,
            "metadata": metadata,
            "timestamp": timestamp,
            "iso_timestamp": datetime.fromtimestamp(timestamp).isoformat()
        }
        
        # Validate payload if enabled
        validation_result = None
        if self.config.verify_payloads:
            validation_result = self.simulator.validate_metric(metric_name, payload)
            payload["validation"] = validation_result
        
        # Store in simulator if enabled
        if self.config.simulate_prometheus:
            self.simulator.store_metric(metric_name, value, labels, timestamp)
            payload["prometheus_format"] = self.simulator.format_metric(
                metric_name, value, labels, timestamp
            )
        
        # Log based on output format
        if self.config.output_format in ["json", "both"]:
            self.logger.info(f"METRIC_JSON: {json.dumps(payload, indent=2)}")
        
        if self.config.output_format in ["prometheus", "both"]:
            prometheus_line = self.simulator.format_metric(metric_name, value, labels, timestamp)
            self.logger.info(f"METRIC_PROMETHEUS: {prometheus_line}")
        
        # Store for session analysis
        self.session_data.append(payload)
        
        # Check thresholds
        self._check_thresholds(payload)
        
        return payload
    
    def _check_thresholds(self, payload: Dict[str, Any]):
        """Check if metric values exceed configured thresholds"""
        if not self.config.thresholds:
            return
        
        metric_name = payload["metric_name"]
        value = payload["value"]
        
        # Token rate threshold
        if "tokens" in metric_name and "max_tokens_per_minute" in self.config.thresholds:
            threshold = self.config.thresholds["max_tokens_per_minute"]
            if value > threshold:
                self.logger.warning(f"Token rate threshold exceeded: {value} > {threshold}")
        
        # Cost threshold
        if "cost" in metric_name and "max_cost_per_hour" in self.config.thresholds:
            threshold = self.config.thresholds["max_cost_per_hour"]
            if value > threshold:
                self.logger.warning(f"Cost threshold exceeded: ${value} > ${threshold}")
        
        # Session duration threshold
        if "duration" in metric_name and "max_session_duration" in self.config.thresholds:
            threshold = self.config.thresholds["max_session_duration"]
            if value > threshold:
                self.logger.warning(f"Session duration threshold exceeded: {value}s > {threshold}s")
    
    def export_session_data(self, filename: Optional[str] = None) -> str:
        """Export collected session data to file"""
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"session_data_{timestamp}.json"
        
        output_path = Path(self.config.export_path) / filename
        
        export_data = {
            "config": asdict(self.config),
            "session_summary": {
                "total_metrics": len(self.session_data),
                "metric_types": list(set(m["metric_name"] for m in self.session_data)),
                "start_time": min(m["timestamp"] for m in self.session_data) if self.session_data else None,
                "end_time": max(m["timestamp"] for m in self.session_data) if self.session_data else None
            },
            "metrics": self.session_data,
            "prometheus_store": self.simulator.metrics_store
        }
        
        with open(output_path, 'w') as f:
            json.dump(export_data, f, indent=2, default=str)
        
        self.logger.info(f"Session data exported to {output_path}")
        return str(output_path)
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get summary of collected metrics"""
        if not self.session_data:
            return {"message": "No metrics collected"}
        
        summary = {
            "total_metrics": len(self.session_data),
            "unique_metric_names": list(set(m["metric_name"] for m in self.session_data)),
            "validation_summary": {
                "valid": sum(1 for m in self.session_data 
                           if m.get("validation", {}).get("valid", True)),
                "invalid": sum(1 for m in self.session_data 
                             if not m.get("validation", {}).get("valid", True))
            },
            "time_range": {
                "start": min(m["timestamp"] for m in self.session_data),
                "end": max(m["timestamp"] for m in self.session_data)
            }
        }
        
        return summary


def create_sample_config(output_path: str = "config/logging_proxy.yaml"):
    """Create a sample configuration file"""
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    
    sample_config = {
        "enabled": True,
        "log_level": "INFO",
        "output_format": "both",
        "verify_payloads": True,
        "simulate_prometheus": True,
        "export_path": "exports/proxy_logs",
        "thresholds": {
            "max_tokens_per_minute": 10000,
            "max_cost_per_hour": 10.0,
            "max_session_duration": 3600
        },
        "metrics": {
            "otel_claude_code_token_usage_tokens_total": {
                "name": "otel_claude_code_token_usage_tokens_total",
                "metric_type": "counter",
                "labels": ["model", "token_type", "session_id"],
                "validation_rules": {
                    "required_fields": ["value", "labels"],
                    "required_labels": ["model", "token_type"],
                    "value_range": [0, 1000000]
                },
                "prometheus_format": "# HELP otel_claude_code_token_usage_tokens_total Total tokens used\n# TYPE otel_claude_code_token_usage_tokens_total counter",
                "description": "Total number of tokens used in Claude Code sessions"
            }
        }
    }
    
    with open(output_path, 'w') as f:
        yaml.dump(sample_config, f, default_flow_style=False, indent=2)
    
    print(f"Sample configuration created at {output_path}")
    return output_path


if __name__ == "__main__":
    # Demo usage
    proxy = LoggingProxy()
    
    # Log some sample metrics
    proxy.log_metric(
        "otel_claude_code_token_usage_tokens_total",
        1500,
        labels={"model": "claude-3-sonnet", "token_type": "input", "session_id": "test-001"}
    )
    
    proxy.log_metric(
        "otel_claude_code_cost_usd",
        0.75,
        labels={"model": "claude-3-sonnet", "session_id": "test-001"}
    )
    
    proxy.log_metric(
        "otel_claude_code_session_duration_seconds",
        300,
        labels={"session_id": "test-001", "status": "completed"}
    )
    
    # Print summary
    print("\nSession Summary:")
    print(json.dumps(proxy.get_metrics_summary(), indent=2))
    
    # Export data
    export_file = proxy.export_session_data()
    print(f"\nData exported to: {export_file}")