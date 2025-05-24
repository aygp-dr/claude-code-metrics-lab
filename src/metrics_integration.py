#!/usr/bin/env python3
"""
Integration example showing how to use the Logging Proxy
with the existing Claude Code metrics collection system
"""

import time
import sys
from pathlib import Path
from typing import Dict, Any

# Add src to path for imports
sys.path.append(str(Path(__file__).parent))

from logging_proxy import LoggingProxy
from project_metrics import get_project_metrics, export_metrics


class MetricsCollector:
    """Enhanced metrics collector with logging proxy integration"""
    
    def __init__(self, config_path: str = "config/logging_proxy.yaml"):
        self.proxy = LoggingProxy(config_path)
        self.session_id = f"session-{int(time.time())}"
        self.project_name = "claude-code-metrics-lab"
    
    def collect_and_log_metrics(self, days: int = 30) -> Dict[str, Any]:
        """Collect metrics from Prometheus and log through proxy"""
        print(f"Collecting metrics for the last {days} days...")
        
        # Log collection start
        self.proxy.log_metric(
            "otel_claude_code_tool_usage_total",
            1,
            labels={
                "tool_name": "metrics_collector",
                "session_id": self.session_id,
                "project": self.project_name,
                "status": "started"
            },
            metadata={"action": "collect_metrics", "days": days}
        )
        
        try:
            # Get metrics from existing system
            metrics = get_project_metrics(days)
            
            if not metrics:
                self.proxy.log_metric(
                    "otel_claude_code_error_total",
                    1,
                    labels={
                        "error_type": "prometheus_connection",
                        "session_id": self.session_id,
                        "tool_name": "metrics_collector"
                    }
                )
                return {"error": "Failed to collect metrics"}
            
            # Log collected metrics through proxy
            for project, data in metrics.items():
                # Log token usage
                if data.get('tokens', 0) > 0:
                    self.proxy.log_metric(
                        "otel_claude_code_token_usage_tokens_total",
                        data['tokens'],
                        labels={
                            "model": "aggregated",
                            "token_type": "total",
                            "session_id": self.session_id,
                            "project": project
                        },
                        metadata={"collection_period_days": days}
                    )
                
                # Log estimated cost (simplified calculation)
                estimated_cost = data['tokens'] * 0.0001  # Example rate
                if estimated_cost > 0:
                    self.proxy.log_metric(
                        "otel_claude_code_cost_usd",
                        estimated_cost,
                        labels={
                            "model": "aggregated",
                            "session_id": self.session_id,
                            "project": project
                        },
                        metadata={"calculation_method": "token_based"}
                    )
                
                # Log model distribution
                for model, tokens in data.get('models', {}).items():
                    if tokens > 0:
                        self.proxy.log_metric(
                            "otel_claude_code_token_usage_tokens_total",
                            tokens,
                            labels={
                                "model": model,
                                "token_type": "mixed",
                                "session_id": self.session_id,
                                "project": project
                            }
                        )
            
            # Log successful collection
            self.proxy.log_metric(
                "otel_claude_code_tool_usage_total",
                1,
                labels={
                    "tool_name": "metrics_collector",
                    "session_id": self.session_id,
                    "project": self.project_name,
                    "status": "completed"
                },
                metadata={
                    "projects_processed": len(metrics),
                    "total_tokens": sum(m.get('tokens', 0) for m in metrics.values())
                }
            )
            
            return metrics
            
        except Exception as e:
            # Log error
            self.proxy.log_metric(
                "otel_claude_code_error_total",
                1,
                labels={
                    "error_type": "collection_error",
                    "session_id": self.session_id,
                    "tool_name": "metrics_collector"
                },
                metadata={"error_message": str(e)}
            )
            raise
    
    def export_with_logging(self, metrics: Dict[str, Any], output_dir: str = 'exports') -> str:
        """Export metrics with logging proxy tracking"""
        try:
            # Export using existing function
            filename = export_metrics(metrics, output_dir)
            
            # Log successful export
            self.proxy.log_metric(
                "otel_claude_code_tool_usage_total",
                1,
                labels={
                    "tool_name": "file_exporter",
                    "session_id": self.session_id,
                    "project": self.project_name,
                    "status": "success"
                },
                metadata={"export_file": filename}
            )
            
            return filename
            
        except Exception as e:
            # Log export error
            self.proxy.log_metric(
                "otel_claude_code_error_total",
                1,
                labels={
                    "error_type": "export_error",
                    "session_id": self.session_id,
                    "tool_name": "file_exporter"
                },
                metadata={"error_message": str(e)}
            )
            raise
    
    def log_session_summary(self):
        """Log summary of the collection session"""
        session_summary = self.proxy.get_metrics_summary()
        
        # Calculate session duration
        if session_summary.get('time_range'):
            duration = session_summary['time_range']['end'] - session_summary['time_range']['start']
            self.proxy.log_metric(
                "otel_claude_code_session_duration_seconds",
                duration,
                labels={
                    "session_id": self.session_id,
                    "status": "completed",
                    "project": self.project_name
                },
                metadata={
                    "metrics_logged": session_summary['total_metrics'],
                    "validation_success_rate": session_summary['validation_summary']['valid'] / max(session_summary['total_metrics'], 1)
                }
            )
        
        return session_summary
    
    def export_proxy_data(self) -> str:
        """Export proxy session data for analysis"""
        return self.proxy.export_session_data(f"metrics_collection_{self.session_id}.json")


def simulate_claude_code_usage():
    """Simulate various Claude Code usage patterns for testing"""
    proxy = LoggingProxy("config/logging_proxy.yaml")
    session_id = "simulation-001"
    
    print("Simulating Claude Code usage patterns...")
    
    # Simulate different projects
    projects = [
        "web-development",
        "data-analysis", 
        "machine-learning",
        "infrastructure"
    ]
    
    models = ["claude-3-sonnet", "claude-3-haiku", "claude-3-opus"]
    tools = ["Read", "Write", "Edit", "Bash", "Glob", "Grep", "WebFetch"]
    
    for i, project in enumerate(projects):
        current_session = f"{session_id}-{project}"
        
        # Simulate token usage for different models
        for model in models:
            input_tokens = 800 + (i * 200)  # Varying complexity
            output_tokens = 600 + (i * 150)
            
            proxy.log_metric(
                "otel_claude_code_token_usage_tokens_total",
                input_tokens,
                labels={
                    "model": model,
                    "token_type": "input",
                    "session_id": current_session,
                    "project": project
                }
            )
            
            proxy.log_metric(
                "otel_claude_code_token_usage_tokens_total",
                output_tokens,
                labels={
                    "model": model,
                    "token_type": "output",
                    "session_id": current_session,
                    "project": project
                }
            )
            
            # Calculate and log cost
            cost = (input_tokens * 0.0001) + (output_tokens * 0.0002)
            proxy.log_metric(
                "otel_claude_code_cost_usd",
                cost,
                labels={
                    "model": model,
                    "session_id": current_session,
                    "project": project
                }
            )
        
        # Simulate tool usage
        for j, tool in enumerate(tools):
            if j <= i:  # Different projects use different numbers of tools
                proxy.log_metric(
                    "otel_claude_code_tool_usage_total",
                    j + 1,
                    labels={
                        "tool_name": tool,
                        "session_id": current_session,
                        "project": project,
                        "status": "success"
                    }
                )
        
        # Simulate session completion
        session_duration = 600 + (i * 300)  # 10-30 minutes
        proxy.log_metric(
            "otel_claude_code_session_duration_seconds",
            session_duration,
            labels={
                "session_id": current_session,
                "status": "completed",
                "project": project
            }
        )
    
    # Simulate some errors
    proxy.log_metric(
        "otel_claude_code_error_total",
        1,
        labels={
            "error_type": "timeout",
            "session_id": f"{session_id}-web-development",
            "tool_name": "WebFetch"
        }
    )
    
    summary = proxy.get_metrics_summary()
    print(f"Simulation completed: {summary['total_metrics']} metrics logged")
    
    return proxy.export_session_data("simulation_data.json")


def main():
    """Main integration demonstration"""
    print("=== Claude Code Metrics Integration Demo ===")
    print()
    
    # 1. Demonstrate metrics collection with logging
    print("1. Collecting metrics with logging proxy...")
    collector = MetricsCollector()
    
    try:
        metrics = collector.collect_and_log_metrics(days=7)
        print(f"Collected metrics for {len(metrics)} projects")
        
        # Export with logging
        export_file = collector.export_with_logging(metrics)
        print(f"Exported to: {export_file}")
        
        # Get session summary
        summary = collector.log_session_summary()
        print(f"Session logged {summary['total_metrics']} metrics")
        
        # Export proxy data
        proxy_export = collector.export_proxy_data()
        print(f"Proxy data exported to: {proxy_export}")
        
    except Exception as e:
        print(f"Collection failed (expected if Prometheus not running): {e}")
    
    print()
    
    # 2. Demonstrate simulation
    print("2. Running usage simulation...")
    simulation_export = simulate_claude_code_usage()
    print(f"Simulation data exported to: {simulation_export}")
    
    print()
    print("=== Integration Demo Complete ===")
    print("Check the exports/proxy_logs/ directory for detailed logs and data files.")


if __name__ == "__main__":
    main()