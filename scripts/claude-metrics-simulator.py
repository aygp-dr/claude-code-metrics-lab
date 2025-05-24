#!/usr/bin/env python3
"""
Claude Code Metrics Simulator

Generates realistic mock metrics using Brownian motion for educational
telemetry development and testing. Provides Prometheus-compatible endpoint
with time-series data that exhibits natural variation patterns.
"""

import time
import math
import random
import yaml
import json
import argparse
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import threading
import logging


@dataclass
class MetricConfig:
    """Configuration for a simulated metric"""
    name: str
    metric_type: str  # counter, gauge, histogram
    initial_value: float
    drift: float  # per second
    volatility: float  # standard deviation
    bounds: Tuple[float, float] = (0, float('inf'))
    labels: Dict[str, List[str]] = None
    description: str = ""
    unit: str = "1"


@dataclass
class ScenarioConfig:
    """Configuration for a simulation scenario"""
    name: str
    duration: float  # seconds
    description: str = ""
    patterns: Dict[str, Any] = None


class BrownianMotionGenerator:
    """Generates values using Brownian motion with drift and volatility"""
    
    def __init__(self, initial_value: float, drift: float, volatility: float, 
                 bounds: Tuple[float, float] = (0, float('inf'))):
        self.initial_value = initial_value
        self.current_value = initial_value
        self.drift = drift
        self.volatility = volatility
        self.bounds = bounds
        self.last_time = time.time()
        
    def next_value(self, dt: Optional[float] = None) -> float:
        """Generate next value using Brownian motion"""
        if dt is None:
            current_time = time.time()
            dt = current_time - self.last_time
            self.last_time = current_time
        
        # Brownian motion: dX = drift * dt + volatility * sqrt(dt) * random_normal
        drift_component = self.drift * dt
        random_shock = self.volatility * math.sqrt(dt) * random.gauss(0, 1)
        
        self.current_value += drift_component + random_shock
        
        # Apply bounds
        self.current_value = max(self.bounds[0], 
                               min(self.bounds[1], self.current_value))
        
        return self.current_value
    
    def reset(self, new_initial: Optional[float] = None):
        """Reset generator to initial state"""
        self.current_value = new_initial or self.initial_value
        self.last_time = time.time()


class HistogramGenerator:
    """Generates histogram data with realistic distributions"""
    
    def __init__(self, buckets: List[float], mean: float, std: float):
        self.buckets = sorted(buckets)
        self.mean = mean
        self.std = std
        self.samples = []
        self.total_count = 0
        self.total_sum = 0.0
        
    def add_sample(self, value: float):
        """Add a sample to the histogram"""
        self.samples.append(value)
        self.total_count += 1
        self.total_sum += value
        
        # Keep only recent samples (sliding window)
        if len(self.samples) > 1000:
            removed = self.samples.pop(0)
            self.total_sum -= removed
            self.total_count -= 1
    
    def generate_sample(self) -> float:
        """Generate a new sample and add to histogram"""
        # Use log-normal distribution for realistic positive values
        sample = random.lognormvariate(math.log(self.mean), self.std)
        self.add_sample(sample)
        return sample
    
    def get_bucket_counts(self) -> Dict[str, int]:
        """Get current bucket counts"""
        counts = {}
        
        for i, bucket in enumerate(self.buckets):
            count = sum(1 for s in self.samples if s <= bucket)
            counts[f"le=\"{bucket}\""] = count
        
        counts["le=\"+Inf\""] = len(self.samples)
        return counts


class PrometheusMetricsSimulator:
    """Main simulator class that generates Prometheus-compatible metrics"""
    
    def __init__(self, config_path: Optional[str] = None):
        self.config = self._load_config(config_path)
        self.metrics = {}
        self.histograms = {}
        self.start_time = time.time()
        self.running = False
        self.logger = self._setup_logging()
        
        self._initialize_metrics()
    
    def _load_config(self, config_path: Optional[str] = None) -> Dict[str, Any]:
        """Load configuration from file or use defaults"""
        if config_path and Path(config_path).exists():
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        else:
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration for Claude Code metrics simulation"""
        return {
            "server": {
                "host": "localhost",
                "port": 9090,
                "update_interval": 10
            },
            "metrics": {
                "otel_claude_code_token_usage_tokens_total": {
                    "name": "otel_claude_code_token_usage_tokens_total",
                    "metric_type": "counter",
                    "initial_value": 1000,
                    "drift": 0.1,  # 0.1 tokens/second growth
                    "volatility": 5.0,
                    "bounds": [0, 1000000],
                    "labels": {
                        "model": ["claude-3-sonnet", "claude-3-haiku", "claude-3-opus"],
                        "token_type": ["input", "output"],
                        "session_id": ["session-001", "session-002", "session-003"],
                        "project": ["web-development", "data-analysis", "infrastructure"]
                    },
                    "description": "Total number of tokens used in Claude Code sessions (simulated)",
                    "unit": "tokens"
                },
                "otel_claude_code_session_duration_seconds": {
                    "name": "otel_claude_code_session_duration_seconds", 
                    "metric_type": "histogram",
                    "initial_value": 300,  # 5 minutes average
                    "drift": 0.0,
                    "volatility": 30.0,
                    "bounds": [10, 7200],  # 10 seconds to 2 hours
                    "labels": {
                        "session_id": ["session-001", "session-002", "session-003"],
                        "status": ["completed", "active", "failed"],
                        "project": ["web-development", "data-analysis", "infrastructure"]
                    },
                    "description": "Duration of Claude Code sessions in seconds (simulated)",
                    "unit": "seconds"
                },
                "otel_claude_code_cost_usd": {
                    "name": "otel_claude_code_cost_usd",
                    "metric_type": "gauge",
                    "initial_value": 0.50,
                    "drift": 0.001,  # $0.001/second cost growth
                    "volatility": 0.05,
                    "bounds": [0, 1000],
                    "labels": {
                        "model": ["claude-3-sonnet", "claude-3-haiku", "claude-3-opus"],
                        "session_id": ["session-001", "session-002", "session-003"],
                        "project": ["web-development", "data-analysis", "infrastructure"]
                    },
                    "description": "Estimated cost in USD for Claude Code usage (simulated)",
                    "unit": "dollars"
                },
                "otel_claude_code_tool_usage_total": {
                    "name": "otel_claude_code_tool_usage_total",
                    "metric_type": "counter", 
                    "initial_value": 50,
                    "drift": 0.05,  # 0.05 tool uses/second
                    "volatility": 2.0,
                    "bounds": [0, 100000],
                    "labels": {
                        "tool_name": ["Read", "Write", "Edit", "Bash", "Glob", "Grep"],
                        "session_id": ["session-001", "session-002", "session-003"],
                        "project": ["web-development", "data-analysis", "infrastructure"],
                        "status": ["success", "error"]
                    },
                    "description": "Number of tool invocations in Claude Code sessions (simulated)",
                    "unit": "invocations"
                },
                "otel_claude_code_error_total": {
                    "name": "otel_claude_code_error_total",
                    "metric_type": "counter",
                    "initial_value": 2,
                    "drift": 0.01,  # 0.01 errors/second 
                    "volatility": 0.5,
                    "bounds": [0, 10000],
                    "labels": {
                        "error_type": ["timeout", "network", "auth", "validation"],
                        "session_id": ["session-001", "session-002", "session-003"],
                        "tool_name": ["Read", "Write", "Edit", "Bash"]
                    },
                    "description": "Number of errors encountered in Claude Code sessions (simulated)",
                    "unit": "errors"
                }
            },
            "scenarios": {
                "normal": {
                    "name": "normal_operations",
                    "duration": 3600,  # 1 hour
                    "description": "Normal Claude Code usage patterns"
                },
                "high_load": {
                    "name": "high_load_testing",
                    "duration": 1800,  # 30 minutes
                    "description": "High load testing scenario",
                    "patterns": {
                        "token_drift_multiplier": 5.0,
                        "error_rate_multiplier": 2.0
                    }
                },
                "degradation": {
                    "name": "system_degradation",
                    "duration": 2700,  # 45 minutes
                    "description": "System performance degradation",
                    "patterns": {
                        "token_drift_multiplier": 0.5,
                        "error_rate_multiplier": 10.0
                    }
                }
            }
        }
    
    def _setup_logging(self) -> logging.Logger:
        """Setup logging configuration"""
        logger = logging.getLogger('claude-metrics-simulator')
        logger.setLevel(logging.INFO)
        
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
        return logger
    
    def _initialize_metrics(self):
        """Initialize all metric generators"""
        for metric_name, metric_config in self.config["metrics"].items():
            config = MetricConfig(**metric_config)
            
            if config.metric_type == "histogram":
                # Initialize histogram with standard buckets
                buckets = [1, 5, 10, 30, 60, 300, 600, 1800, 3600]
                self.histograms[metric_name] = HistogramGenerator(
                    buckets=buckets,
                    mean=config.initial_value,
                    std=config.volatility / config.initial_value  # relative std
                )
            else:
                # Initialize Brownian motion generators for each label combination
                self.metrics[metric_name] = {}
                
                if config.labels:
                    # Generate combinations of labels
                    label_combinations = self._generate_label_combinations(config.labels)
                    for labels in label_combinations:
                        key = self._labels_to_key(labels)
                        self.metrics[metric_name][key] = {
                            'generator': BrownianMotionGenerator(
                                config.initial_value,
                                config.drift,
                                config.volatility,
                                config.bounds
                            ),
                            'labels': labels,
                            'config': config
                        }
                else:
                    # No labels, single generator
                    self.metrics[metric_name][''] = {
                        'generator': BrownianMotionGenerator(
                            config.initial_value,
                            config.drift,
                            config.volatility,
                            config.bounds
                        ),
                        'labels': {},
                        'config': config
                    }
    
    def _generate_label_combinations(self, label_config: Dict[str, List[str]]) -> List[Dict[str, str]]:
        """Generate all combinations of label values"""
        import itertools
        
        keys = list(label_config.keys())
        values = list(label_config.values())
        
        combinations = []
        for combination in itertools.product(*values):
            combinations.append(dict(zip(keys, combination)))
        
        # Limit combinations to prevent explosion
        if len(combinations) > 50:
            combinations = combinations[:50]
        
        return combinations
    
    def _labels_to_key(self, labels: Dict[str, str]) -> str:
        """Convert labels dict to string key"""
        return ','.join(f"{k}={v}" for k, v in sorted(labels.items()))
    
    def update_metrics(self):
        """Update all metrics with new values"""
        current_time = time.time()
        
        # Update regular metrics
        for metric_name, metric_data in self.metrics.items():
            for key, data in metric_data.items():
                new_value = data['generator'].next_value()
                data['current_value'] = new_value
                data['last_update'] = current_time
        
        # Update histograms
        for metric_name, histogram in self.histograms.items():
            # Generate new sample
            histogram.generate_sample()
    
    def get_prometheus_output(self) -> str:
        """Generate Prometheus exposition format output"""
        output_lines = []
        current_time = int(time.time() * 1000)  # milliseconds
        
        # Regular metrics
        for metric_name, metric_data in self.metrics.items():
            if not metric_data:
                continue
            
            # Get config from first entry
            config = next(iter(metric_data.values()))['config']
            
            # Add HELP and TYPE comments
            output_lines.append(f"# HELP {metric_name} {config.description}")
            output_lines.append(f"# TYPE {metric_name} {config.metric_type}")
            
            # Add metric lines
            for key, data in metric_data.items():
                labels_str = ""
                if data['labels']:
                    label_pairs = [f'{k}="{v}"' for k, v in data['labels'].items()]
                    labels_str = "{" + ",".join(label_pairs) + "}"
                
                value = data.get('current_value', data['generator'].current_value)
                
                # Format value appropriately
                if config.metric_type == "counter":
                    value = max(0, int(value))  # Counters should be non-negative integers
                else:
                    value = round(value, 4)  # Gauges can be float
                
                output_lines.append(f"{metric_name}{labels_str} {value} {current_time}")
        
        # Histogram metrics
        for metric_name, histogram in self.histograms.items():
            config = self.config["metrics"][metric_name]
            
            # Add HELP and TYPE comments
            output_lines.append(f"# HELP {metric_name} {config['description']}")
            output_lines.append(f"# TYPE {metric_name} histogram")
            
            # Generate labels (simplified for histogram)
            base_labels = {"session_id": "session-001", "project": "simulation"}
            label_pairs = [f'{k}="{v}"' for k, v in base_labels.items()]
            base_labels_str = "{" + ",".join(label_pairs) + "}"
            
            # Add bucket counts
            bucket_counts = histogram.get_bucket_counts()
            for bucket_label, count in bucket_counts.items():
                bucket_labels_str = base_labels_str[:-1] + f",{bucket_label}" + "}"
                output_lines.append(f"{metric_name}_bucket{bucket_labels_str} {count} {current_time}")
            
            # Add sum and count
            output_lines.append(f"{metric_name}_sum{base_labels_str} {histogram.total_sum:.4f} {current_time}")
            output_lines.append(f"{metric_name}_count{base_labels_str} {histogram.total_count} {current_time}")
        
        return "\n".join(output_lines) + "\n"
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get health status information"""
        uptime = time.time() - self.start_time
        return {
            "status": "healthy",
            "uptime_seconds": round(uptime, 2),
            "metrics_count": sum(len(m) for m in self.metrics.values()),
            "last_update": datetime.now().isoformat(),
            "config": {
                "update_interval": self.config["server"]["update_interval"],
                "scenarios": list(self.config["scenarios"].keys())
            }
        }
    
    def apply_scenario(self, scenario_name: str):
        """Apply a specific scenario configuration"""
        if scenario_name not in self.config["scenarios"]:
            self.logger.warning(f"Scenario '{scenario_name}' not found")
            return
        
        scenario = self.config["scenarios"][scenario_name]
        self.logger.info(f"Applying scenario: {scenario['name']}")
        
        if "patterns" in scenario:
            patterns = scenario["patterns"]
            
            # Apply pattern multipliers
            for metric_name, metric_data in self.metrics.items():
                for key, data in metric_data.items():
                    generator = data['generator']
                    
                    if "token_drift_multiplier" in patterns and "token" in metric_name:
                        generator.drift *= patterns["token_drift_multiplier"]
                    
                    if "error_rate_multiplier" in patterns and "error" in metric_name:
                        generator.drift *= patterns["error_rate_multiplier"]
    
    def start_simulation(self, scenario: Optional[str] = None):
        """Start the metrics simulation"""
        if scenario:
            self.apply_scenario(scenario)
        
        self.running = True
        self.logger.info("Starting Claude Code metrics simulation")
        self.logger.info(f"Prometheus endpoint: http://{self.config['server']['host']}:{self.config['server']['port']}/metrics")
        
        # Start metrics update thread
        def update_loop():
            while self.running:
                self.update_metrics()
                time.sleep(self.config["server"]["update_interval"])
        
        update_thread = threading.Thread(target=update_loop, daemon=True)
        update_thread.start()
        
        return update_thread
    
    def stop_simulation(self):
        """Stop the metrics simulation"""
        self.running = False
        self.logger.info("Stopping Claude Code metrics simulation")


class PrometheusHTTPHandler(BaseHTTPRequestHandler):
    """HTTP handler for Prometheus metrics endpoint"""
    
    def __init__(self, simulator: PrometheusMetricsSimulator, *args, **kwargs):
        self.simulator = simulator
        super().__init__(*args, **kwargs)
    
    def do_GET(self):
        """Handle GET requests"""
        parsed_path = urlparse(self.path)
        
        if parsed_path.path == "/metrics":
            self._handle_metrics()
        elif parsed_path.path == "/health":
            self._handle_health()
        elif parsed_path.path == "/config":
            self._handle_config()
        else:
            self._handle_404()
    
    def _handle_metrics(self):
        """Handle metrics endpoint"""
        try:
            metrics_output = self.simulator.get_prometheus_output()
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain; version=0.0.4; charset=utf-8')
            self.end_headers()
            self.wfile.write(metrics_output.encode())
        except Exception as e:
            self.simulator.logger.error(f"Error generating metrics: {e}")
            self.send_error(500, f"Internal server error: {e}")
    
    def _handle_health(self):
        """Handle health check endpoint"""
        try:
            health_status = self.simulator.get_health_status()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(health_status, indent=2).encode())
        except Exception as e:
            self.send_error(500, f"Internal server error: {e}")
    
    def _handle_config(self):
        """Handle configuration endpoint"""
        try:
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(self.simulator.config, indent=2).encode())
        except Exception as e:
            self.send_error(500, f"Internal server error: {e}")
    
    def _handle_404(self):
        """Handle 404 responses"""
        self.send_error(404, "Not found")
    
    def log_message(self, format, *args):
        """Override to use our logger"""
        self.simulator.logger.info(f"{self.address_string()} - {format % args}")


def create_handler(simulator):
    """Create HTTP handler with simulator reference"""
    def handler(*args, **kwargs):
        PrometheusHTTPHandler(simulator, *args, **kwargs)
    return handler


def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Claude Code Metrics Simulator")
    parser.add_argument("--config", help="Configuration file path")
    parser.add_argument("--scenario", help="Scenario to run", default="normal")
    parser.add_argument("--port", type=int, help="HTTP server port")
    parser.add_argument("--host", help="HTTP server host")
    parser.add_argument("--duration", type=int, help="Simulation duration in seconds")
    parser.add_argument("--dev", action="store_true", help="Development mode")
    
    args = parser.parse_args()
    
    # Initialize simulator
    simulator = PrometheusMetricsSimulator(args.config)
    
    # Override config with command line args
    if args.port:
        simulator.config["server"]["port"] = args.port
    if args.host:
        simulator.config["server"]["host"] = args.host
    
    # Start simulation
    update_thread = simulator.start_simulation(args.scenario)
    
    # Start HTTP server
    server_address = (simulator.config["server"]["host"], simulator.config["server"]["port"])
    
    class SimulatorHTTPRequestHandler(BaseHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            self.simulator = simulator
            super().__init__(*args, **kwargs)
        
        def do_GET(self):
            handler = PrometheusHTTPHandler(simulator)
            handler.path = self.path
            handler.send_response = self.send_response
            handler.send_header = self.send_header
            handler.end_headers = self.end_headers
            handler.wfile = self.wfile
            handler.do_GET()
    
    httpd = HTTPServer(server_address, SimulatorHTTPRequestHandler)
    
    try:
        simulator.logger.info(f"Starting HTTP server on {server_address[0]}:{server_address[1]}")
        if args.duration:
            simulator.logger.info(f"Will run for {args.duration} seconds")
            
            # Run for specified duration
            def stop_after_duration():
                time.sleep(args.duration)
                simulator.stop_simulation()
                httpd.shutdown()
            
            timer_thread = threading.Thread(target=stop_after_duration, daemon=True)
            timer_thread.start()
        
        httpd.serve_forever()
        
    except KeyboardInterrupt:
        simulator.logger.info("Received interrupt signal")
    finally:
        simulator.stop_simulation()
        httpd.shutdown()
        simulator.logger.info("Simulator stopped")


if __name__ == "__main__":
    main()