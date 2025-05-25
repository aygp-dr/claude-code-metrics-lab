#!/usr/bin/env python3
"""
Enhanced Claude Code Metrics Simulator Framework

Implementation of the RFC: Metrics Dashboard Simulator and Development Instance
This provides a comprehensive simulator with configurable user populations,
activity models, fault injection, and scenario management.
"""

import time
import math
import random
import yaml
import json
import logging
import threading
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, asdict
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from prometheus_client import Counter, Histogram, Gauge, start_http_server, CollectorRegistry, CONTENT_TYPE_LATEST
import prometheus_client


@dataclass
class User:
    """Represents a simulated user with activity patterns"""
    id: str
    activity_level: float
    base_activity: float
    volatility: float
    user_type: str  # "power", "regular", "idle"
    last_session: Optional[datetime] = None
    total_sessions: int = 0
    total_tokens: int = 0
    total_cost: float = 0.0


@dataclass
class SimulationEvent:
    """Represents a scenario event"""
    time: float  # seconds from start
    event_type: str
    parameters: Dict[str, Any]


class ActivityModel:
    """Advanced activity model with Brownian motion and mean reversion"""
    
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.ActivityModel")
    
    def update_user_activity(self, user: User, dt: float = 0.1, 
                           seasonal_factor: float = 1.0,
                           burst_factor: float = 1.0) -> float:
        """Update user activity using Brownian motion with mean reversion"""
        # Mean reversion strength (users tend to return to their base activity)
        theta = 0.1
        
        # Random shock proportional to volatility
        shock = np.random.normal(0, user.volatility * np.sqrt(dt))
        
        # Drift towards base activity with seasonal and burst adjustments
        adjusted_base = user.base_activity * seasonal_factor * burst_factor
        drift = theta * (adjusted_base - user.activity_level) * dt
        
        # Update activity level
        user.activity_level += drift + shock
        
        # Apply bounds (activity cannot be negative or extremely high)
        user.activity_level = max(0.1, min(5.0, user.activity_level))
        
        return user.activity_level
    
    def get_seasonal_factor(self, current_time: datetime) -> float:
        """Calculate seasonal activity factor based on time of day and day of week"""
        hour = current_time.hour
        weekday = current_time.weekday()  # 0 = Monday, 6 = Sunday
        
        # Business hours factor (9 AM - 5 PM)
        if 9 <= hour <= 17:
            business_hours_factor = 2.0
        elif 6 <= hour <= 22:
            business_hours_factor = 1.5
        else:
            business_hours_factor = 0.3
        
        # Weekend factor
        weekend_factor = 0.3 if weekday >= 5 else 1.0
        
        return business_hours_factor * weekend_factor
    
    def generate_burst_pattern(self, elapsed_time: float, 
                             burst_config: Dict[str, Any]) -> float:
        """Generate burst activity patterns"""
        if not burst_config.get('enabled', False):
            return 1.0
        
        burst_interval = burst_config.get('interval', 3600)  # 1 hour default
        burst_duration = burst_config.get('duration', 300)   # 5 minutes default
        burst_intensity = burst_config.get('intensity', 3.0)
        
        # Check if we're in a burst period
        cycle_position = elapsed_time % burst_interval
        if cycle_position < burst_duration:
            return burst_intensity
        
        return 1.0


class MetricsGenerator:
    """Enhanced metrics generator with realistic distributions and user behavior"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.registry = CollectorRegistry()
        self._setup_metrics()
        self.logger = logging.getLogger(f"{__name__}.MetricsGenerator")
        
    def _setup_metrics(self):
        """Setup Prometheus metrics with custom registry"""
        # Session metrics
        self.session_counter = Counter(
            'otel_claude_code_session_count_total',
            'Total Claude Code sessions started',
            ['user_id', 'user_type'],
            registry=self.registry
        )
        
        # Token usage metrics
        self.token_counter = Counter(
            'otel_claude_code_token_usage_tokens_total',
            'Total tokens used in Claude Code sessions',
            ['user_id', 'model', 'type', 'user_type'],
            registry=self.registry
        )
        
        # Cost metrics
        self.cost_counter = Counter(
            'otel_claude_code_cost_usage_USD_total',
            'Total cost in USD for Claude Code usage',
            ['user_id', 'model', 'user_type'],
            registry=self.registry
        )
        
        # Tool usage metrics
        self.tool_counter = Counter(
            'otel_claude_code_tool_usage_total',
            'Total tool invocations in Claude Code sessions',
            ['user_id', 'tool_name', 'status', 'user_type'],
            registry=self.registry
        )
        
        # Error metrics
        self.error_counter = Counter(
            'otel_claude_code_error_total',
            'Total errors in Claude Code sessions',
            ['user_id', 'error_type', 'tool_name', 'user_type'],
            registry=self.registry
        )
        
        # Commit metrics
        self.commit_counter = Counter(
            'otel_claude_code_commit_count_total',
            'Total commits made in Claude Code sessions',
            ['user_id', 'user_type'],
            registry=self.registry
        )
        
        # Session duration histogram
        self.session_duration = Histogram(
            'otel_claude_code_session_duration_seconds',
            'Duration of Claude Code sessions in seconds',
            ['user_id', 'user_type', 'status'],
            registry=self.registry,
            buckets=[10, 30, 60, 300, 600, 1800, 3600, 7200]
        )
        
        # Active sessions gauge
        self.active_sessions = Gauge(
            'otel_claude_code_active_sessions',
            'Number of currently active Claude Code sessions',
            ['user_type'],
            registry=self.registry
        )
    
    def generate_session_metrics(self, user: User, activity_multiplier: float = 1.0,
                               failure_rate: float = 0.01) -> Dict[str, Any]:
        """Generate comprehensive metrics for a user session"""
        # Decide if this user should have a session based on activity level
        session_probability = (user.activity_level * activity_multiplier) / 5.0
        if random.random() > session_probability:
            return {}
        
        # Start session
        self.session_counter.labels(
            user_id=user.id,
            user_type=user.user_type
        ).inc()
        
        user.total_sessions += 1
        user.last_session = datetime.now()
        
        # Choose model based on user type and configuration
        model_weights = self.config['model_distribution'][user.user_type]
        model = random.choices(
            list(model_weights.keys()),
            weights=list(model_weights.values())
        )[0]
        
        # Generate session duration based on user type
        if user.user_type == 'power':
            duration = random.lognormvariate(math.log(1800), 0.8)  # ~30 min avg
        elif user.user_type == 'regular':
            duration = random.lognormvariate(math.log(600), 0.6)   # ~10 min avg
        else:  # idle
            duration = random.lognormvariate(math.log(300), 0.4)   # ~5 min avg
        
        duration = max(10, min(7200, duration))  # Clamp between 10s and 2h
        
        # Session status (success vs failure)
        session_status = 'failed' if random.random() < failure_rate else 'completed'
        
        # Record session duration
        self.session_duration.labels(
            user_id=user.id,
            user_type=user.user_type,
            status=session_status
        ).observe(duration)
        
        # Generate tokens based on session duration and user activity
        base_tokens = int(duration * user.activity_level * random.uniform(0.5, 2.0))
        
        # Input tokens (typically more than output)
        input_tokens = int(base_tokens * random.uniform(0.6, 1.0))
        self.token_counter.labels(
            user_id=user.id,
            model=model,
            type='input',
            user_type=user.user_type
        ).inc(input_tokens)
        
        # Output tokens
        output_tokens = int(base_tokens * random.uniform(0.3, 0.7))
        self.token_counter.labels(
            user_id=user.id,
            model=model,
            type='output',
            user_type=user.user_type
        ).inc(output_tokens)
        
        # Cache tokens (occasional)
        if random.random() < 0.2:
            cache_tokens = int(base_tokens * random.uniform(0.1, 0.3))
            self.token_counter.labels(
                user_id=user.id,
                model=model,
                type='cache',
                user_type=user.user_type
            ).inc(cache_tokens)
        
        user.total_tokens += input_tokens + output_tokens
        
        # Calculate and record cost
        costs = self.config['costs_per_1k_tokens'][model]
        total_cost = (input_tokens / 1000) * costs['input'] + \
                    (output_tokens / 1000) * costs['output']
        
        self.cost_counter.labels(
            user_id=user.id,
            model=model,
            user_type=user.user_type
        ).inc(total_cost)
        
        user.total_cost += total_cost
        
        # Generate tool usage
        tools_used = self._generate_tool_usage(user, duration, session_status)
        
        # Generate errors
        self._generate_errors(user, session_status, failure_rate * 10)
        
        # Generate commits (power users more likely)
        commit_probability = {
            'power': 0.4,
            'regular': 0.2,
            'idle': 0.05
        }[user.user_type]
        
        if random.random() < commit_probability:
            commits = random.randint(1, 5)
            self.commit_counter.labels(
                user_id=user.id,
                user_type=user.user_type
            ).inc(commits)
        
        return {
            'session_duration': duration,
            'tokens': input_tokens + output_tokens,
            'cost': total_cost,
            'tools_used': tools_used,
            'model': model,
            'status': session_status
        }
    
    def _generate_tool_usage(self, user: User, duration: float, status: str) -> Dict[str, int]:
        """Generate realistic tool usage patterns"""
        tools = ['Read', 'Write', 'Edit', 'Bash', 'Glob', 'Grep', 'MultiEdit', 'Task']
        tool_weights = {
            'Read': 0.25,
            'Write': 0.15,
            'Edit': 0.20,
            'Bash': 0.15,
            'Glob': 0.10,
            'Grep': 0.10,
            'MultiEdit': 0.03,
            'Task': 0.02
        }
        
        # Number of tools used based on session duration and user type
        base_tools = int(duration / 60)  # ~1 tool per minute
        if user.user_type == 'power':
            base_tools = int(base_tools * 1.5)
        elif user.user_type == 'idle':
            base_tools = int(base_tools * 0.5)
        
        tools_used = {}
        for _ in range(max(1, base_tools)):
            tool = random.choices(tools, weights=list(tool_weights.values()))[0]
            tool_status = 'error' if (status == 'failed' and random.random() < 0.3) else 'success'
            
            self.tool_counter.labels(
                user_id=user.id,
                tool_name=tool,
                status=tool_status,
                user_type=user.user_type
            ).inc()
            
            tools_used[tool] = tools_used.get(tool, 0) + 1
        
        return tools_used
    
    def _generate_errors(self, user: User, session_status: str, base_error_rate: float):
        """Generate realistic error patterns"""
        error_types = ['timeout', 'network', 'auth', 'validation', 'rate_limit']
        tools = ['Read', 'Write', 'Edit', 'Bash']
        
        error_probability = base_error_rate
        if session_status == 'failed':
            error_probability *= 5  # More errors in failed sessions
        
        if random.random() < error_probability:
            error_type = random.choice(error_types)
            tool_name = random.choice(tools)
            
            self.error_counter.labels(
                user_id=user.id,
                error_type=error_type,
                tool_name=tool_name,
                user_type=user.user_type
            ).inc()
    
    def update_active_sessions(self, active_counts: Dict[str, int]):
        """Update active session gauges"""
        for user_type, count in active_counts.items():
            self.active_sessions.labels(user_type=user_type).set(count)
    
    def get_metrics_output(self) -> str:
        """Get Prometheus metrics output"""
        return prometheus_client.generate_latest(self.registry).decode('utf-8')


class Simulator:
    """Main simulator orchestrating user activities and scenarios"""
    
    def __init__(self, config_file: str):
        with open(config_file, 'r') as f:
            self.config = yaml.safe_load(f)
        
        self.users: List[User] = []
        self.activity_model = ActivityModel()
        self.metrics_generator = MetricsGenerator(self.config)
        self.running = False
        self.start_time = time.time()
        self.current_scenario = None
        self.scenario_events: List[SimulationEvent] = []
        
        self.logger = self._setup_logging()
        self._create_users()
    
    def _setup_logging(self) -> logging.Logger:
        """Setup logging configuration"""
        logger = logging.getLogger(f"{__name__}.Simulator")
        logger.setLevel(logging.INFO)
        
        # Create handler if it doesn't exist
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    def _create_users(self):
        """Create user population based on configuration"""
        user_config = self.config['users']
        total_users = user_config['total']
        
        for i in range(total_users):
            # Determine user type and characteristics
            rand = random.random()
            cumulative = 0
            user_type = 'regular'  # default
            
            for utype, config in user_config['distribution'].items():
                cumulative += config['percentage']
                if rand <= cumulative:
                    user_type = utype
                    break
            
            # Set activity characteristics based on user type
            type_config = user_config['distribution'][user_type]
            base_activity = random.uniform(
                type_config['activity_range'][0],
                type_config['activity_range'][1]
            )
            
            user = User(
                id=f"user_{i:03d}",
                activity_level=base_activity,
                base_activity=base_activity,
                volatility=type_config['volatility'],
                user_type=user_type
            )
            self.users.append(user)
        
        self.logger.info(f"Created {len(self.users)} users: "
                        f"{sum(1 for u in self.users if u.user_type == 'power')} power, "
                        f"{sum(1 for u in self.users if u.user_type == 'regular')} regular, "
                        f"{sum(1 for u in self.users if u.user_type == 'idle')} idle")
    
    def load_scenario(self, scenario_name: str):
        """Load and parse a scenario configuration"""
        if scenario_name not in self.config['scenarios']:
            raise ValueError(f"Scenario '{scenario_name}' not found")
        
        scenario = self.config['scenarios'][scenario_name]
        self.current_scenario = scenario
        self.scenario_events = []
        
        # Parse timeline events
        for event_data in scenario.get('timeline', []):
            event_time = self._parse_time(event_data['time'])
            event = SimulationEvent(
                time=event_time,
                event_type=event_data['event'],
                parameters=event_data
            )
            self.scenario_events.append(event)
        
        # Sort events by time
        self.scenario_events.sort(key=lambda x: x.time)
        
        self.logger.info(f"Loaded scenario '{scenario_name}' with {len(self.scenario_events)} events")
    
    def _parse_time(self, time_str: str) -> float:
        """Parse time string like '10m' or '2h' to seconds"""
        if isinstance(time_str, (int, float)):
            return float(time_str)
        
        time_str = str(time_str).lower()
        if time_str.endswith('m'):
            return float(time_str[:-1]) * 60
        elif time_str.endswith('h'):
            return float(time_str[:-1]) * 3600
        elif time_str.endswith('s'):
            return float(time_str[:-1])
        else:
            return float(time_str)
    
    def _handle_scenario_event(self, event: SimulationEvent):
        """Handle a scenario event"""
        self.logger.info(f"Executing event: {event.event_type} at {event.time}s")
        
        if event.event_type == 'increase_load':
            multiplier = event.parameters.get('multiplier', 2.0)
            for user in self.users:
                user.activity_level *= multiplier
                
        elif event.event_type == 'inject_failure':
            failure_type = event.parameters.get('type', 'random')
            if failure_type == 'model_outage':
                # Simulate model outage by reducing activity for affected users
                affected_percentage = event.parameters.get('affected_percentage', 30) / 100
                affected_count = int(len(self.users) * affected_percentage)
                affected_users = random.sample(self.users, affected_count)
                for user in affected_users:
                    user.activity_level *= 0.1  # Dramatically reduce activity
                    
        elif event.event_type == 'recovery':
            # Reset all users to their base activity levels
            for user in self.users:
                user.activity_level = user.base_activity
                
        elif event.event_type == 'burst_load':
            # Temporary burst in activity
            multiplier = event.parameters.get('multiplier', 5.0)
            duration = event.parameters.get('duration', 300)  # 5 minutes
            
            # This would typically be handled by the burst pattern generator
            # For now, just log it
            self.logger.info(f"Burst load: {multiplier}x for {duration}s")
    
    def run_scenario(self, scenario_name: str, duration: Optional[float] = None):
        """Run a specific scenario"""
        self.load_scenario(scenario_name)
        
        scenario_duration = duration or self.current_scenario.get('duration', 3600)
        self.logger.info(f"Starting scenario '{scenario_name}' for {scenario_duration}s")
        
        self.running = True
        self.start_time = time.time()
        
        next_event_index = 0
        tick = 0
        
        try:
            while self.running and (time.time() - self.start_time) < scenario_duration:
                current_time = time.time() - self.start_time
                
                # Check for scenario events
                while (next_event_index < len(self.scenario_events) and 
                       self.scenario_events[next_event_index].time <= current_time):
                    self._handle_scenario_event(self.scenario_events[next_event_index])
                    next_event_index += 1
                
                # Update user activities
                if tick % 10 == 0:  # Update activities every 10 ticks
                    current_datetime = datetime.now()
                    seasonal_factor = self.activity_model.get_seasonal_factor(current_datetime)
                    
                    for user in self.users:
                        self.activity_model.update_user_activity(
                            user, 
                            dt=1.0,  # 1 second update
                            seasonal_factor=seasonal_factor
                        )
                
                # Generate session metrics
                if tick % 5 == 0:  # Generate sessions every 5 ticks
                    active_sessions = {'power': 0, 'regular': 0, 'idle': 0}
                    
                    for user in self.users:
                        session_data = self.metrics_generator.generate_session_metrics(user)
                        if session_data:
                            active_sessions[user.user_type] += 1
                    
                    # Update active session metrics
                    self.metrics_generator.update_active_sessions(active_sessions)
                
                # Status logging
                if tick % 100 == 0:
                    avg_activity = np.mean([u.activity_level for u in self.users])
                    total_sessions = sum(u.total_sessions for u in self.users)
                    total_cost = sum(u.total_cost for u in self.users)
                    
                    self.logger.info(
                        f"t={current_time:.1f}s: avg_activity={avg_activity:.2f}, "
                        f"sessions={total_sessions}, cost=${total_cost:.2f}"
                    )
                
                time.sleep(0.1)  # 100ms tick
                tick += 1
                
        except KeyboardInterrupt:
            self.logger.info("Received interrupt signal")
        finally:
            self.running = False
            self.logger.info("Scenario completed")
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get simulator health and status"""
        uptime = time.time() - self.start_time
        return {
            "status": "healthy" if self.running else "stopped",
            "uptime_seconds": round(uptime, 2),
            "users_count": len(self.users),
            "current_scenario": self.current_scenario.get('name') if self.current_scenario else None,
            "total_sessions": sum(u.total_sessions for u in self.users),
            "total_cost": round(sum(u.total_cost for u in self.users), 2),
            "avg_activity": round(np.mean([u.activity_level for u in self.users]), 2),
            "last_update": datetime.now().isoformat()
        }
    
    def stop(self):
        """Stop the simulator"""
        self.running = False


class SimulatorHTTPServer:
    """HTTP server for the simulator with metrics and health endpoints"""
    
    def __init__(self, simulator: Simulator, host: str = "localhost", port: int = 8000):
        self.simulator = simulator
        self.host = host
        self.port = port
        self.logger = logging.getLogger(f"{__name__}.SimulatorHTTPServer")
    
    def start_server(self):
        """Start the HTTP server"""
        class RequestHandler(BaseHTTPRequestHandler):
            def __init__(self, *args, **kwargs):
                self.simulator = simulator
                super().__init__(*args, **kwargs)
            
            def do_GET(self):
                if self.path == '/metrics':
                    self._handle_metrics()
                elif self.path == '/health':
                    self._handle_health()
                elif self.path == '/config':
                    self._handle_config()
                else:
                    self._handle_404()
            
            def _handle_metrics(self):
                try:
                    metrics_output = self.simulator.metrics_generator.get_metrics_output()
                    self.send_response(200)
                    self.send_header('Content-Type', CONTENT_TYPE_LATEST)
                    self.end_headers()
                    self.wfile.write(metrics_output.encode())
                except Exception as e:
                    self.send_error(500, f"Error generating metrics: {e}")
            
            def _handle_health(self):
                try:
                    health_data = self.simulator.get_health_status()
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps(health_data, indent=2).encode())
                except Exception as e:
                    self.send_error(500, f"Error getting health status: {e}")
            
            def _handle_config(self):
                try:
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps(self.simulator.config, indent=2).encode())
                except Exception as e:
                    self.send_error(500, f"Error getting configuration: {e}")
            
            def _handle_404(self):
                self.send_error(404, "Not found")
            
            def log_message(self, format, *args):
                # Suppress default logging
                pass
        
        server = HTTPServer((self.host, self.port), RequestHandler)
        self.logger.info(f"Starting HTTP server on {self.host}:{self.port}")
        
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            server.shutdown()
            self.logger.info("HTTP server stopped")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Enhanced Claude Code Metrics Simulator")
    parser.add_argument("--config", required=True, help="Configuration file path")
    parser.add_argument("--scenario", default="baseline", help="Scenario to run")
    parser.add_argument("--duration", type=float, help="Simulation duration in seconds")
    parser.add_argument("--host", default="localhost", help="HTTP server host")
    parser.add_argument("--port", type=int, default=8000, help="HTTP server port")
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create and start simulator
    simulator = Simulator(args.config)
    
    # Start HTTP server in a separate thread
    server = SimulatorHTTPServer(simulator, args.host, args.port)
    server_thread = threading.Thread(target=server.start_server, daemon=True)
    server_thread.start()
    
    try:
        # Run the scenario
        simulator.run_scenario(args.scenario, args.duration)
    except KeyboardInterrupt:
        pass
    finally:
        simulator.stop()
        logging.info("Simulator stopped")