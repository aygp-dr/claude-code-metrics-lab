#!/usr/bin/env python3
"""
Test script for the Logging Proxy
Demonstrates configuration-driven metrics collection and payload verification
"""

import json
import time
from pathlib import Path
from src.logging_proxy import LoggingProxy


def test_basic_functionality():
    """Test basic logging proxy functionality"""
    print("=== Testing Basic Logging Proxy Functionality ===")
    
    # Initialize proxy with custom config
    config_path = "config/logging_proxy.yaml"
    proxy = LoggingProxy(config_path)
    
    print(f"Proxy initialized with config: {config_path}")
    print(f"Export path: {proxy.config.export_path}")
    print(f"Output format: {proxy.config.output_format}")
    print()
    
    return proxy


def test_valid_metrics(proxy):
    """Test logging valid metrics"""
    print("=== Testing Valid Metrics ===")
    
    # Test token usage metric
    result1 = proxy.log_metric(
        "otel_claude_code_token_usage_tokens_total",
        2500,
        labels={
            "model": "claude-3-sonnet",
            "token_type": "input",
            "session_id": "test-session-001",
            "project": "claude-code-metrics-lab"
        },
        metadata={"request_id": "req-123", "user": "test-user"}
    )
    print(f"Token usage metric logged: {result1['validation']['valid']}")
    
    # Test session duration metric
    result2 = proxy.log_metric(
        "otel_claude_code_session_duration_seconds",
        1800,  # 30 minutes
        labels={
            "session_id": "test-session-001",
            "status": "completed",
            "project": "claude-code-metrics-lab"
        }
    )
    print(f"Session duration metric logged: {result2['validation']['valid']}")
    
    # Test cost metric
    result3 = proxy.log_metric(
        "otel_claude_code_cost_usd",
        3.75,
        labels={
            "model": "claude-3-sonnet",
            "session_id": "test-session-001",
            "project": "claude-code-metrics-lab"
        }
    )
    print(f"Cost metric logged: {result3['validation']['valid']}")
    
    # Test tool usage metric
    result4 = proxy.log_metric(
        "otel_claude_code_tool_usage_total",
        15,
        labels={
            "tool_name": "Bash",
            "session_id": "test-session-001",
            "project": "claude-code-metrics-lab",
            "status": "success"
        }
    )
    print(f"Tool usage metric logged: {result4['validation']['valid']}")
    print()


def test_invalid_metrics(proxy):
    """Test logging invalid metrics to verify validation"""
    print("=== Testing Invalid Metrics (Validation) ===")
    
    # Test missing required labels
    result1 = proxy.log_metric(
        "otel_claude_code_token_usage_tokens_total",
        1000,
        labels={"session_id": "test-session-002"}  # Missing model and token_type
    )
    print(f"Missing labels validation: {result1['validation']['valid']}")
    print(f"Errors: {result1['validation']['errors']}")
    
    # Test value out of range
    result2 = proxy.log_metric(
        "otel_claude_code_cost_usd",
        2000,  # Exceeds max of 1000
        labels={
            "model": "claude-3-sonnet",
            "session_id": "test-session-002",
            "project": "test"
        }
    )
    print(f"Out of range validation: {result2['validation']['valid']}")
    print(f"Errors: {result2['validation']['errors']}")
    
    # Test missing required fields
    result3 = proxy.log_metric(
        "otel_claude_code_tool_usage_total",
        5,
        labels={}  # Missing required tool_name label
    )
    print(f"Missing required field validation: {result3['validation']['valid']}")
    print(f"Errors: {result3['validation']['errors']}")
    print()


def test_threshold_monitoring(proxy):
    """Test threshold monitoring functionality"""
    print("=== Testing Threshold Monitoring ===")
    
    # Test cost threshold warning
    proxy.log_metric(
        "otel_claude_code_cost_usd",
        18.0,  # Exceeds max_cost_per_hour threshold of 15.0
        labels={
            "model": "claude-3-opus",
            "session_id": "test-session-003",
            "project": "high-cost-project"
        }
    )
    print("High cost metric logged (check logs for threshold warning)")
    
    # Test token rate threshold
    proxy.log_metric(
        "otel_claude_code_token_usage_tokens_total",
        15000,  # Exceeds max_tokens_per_minute threshold of 10000
        labels={
            "model": "claude-3-opus",
            "token_type": "output",
            "session_id": "test-session-003",
            "project": "high-usage-project"
        }
    )
    print("High token usage metric logged (check logs for threshold warning)")
    
    # Test session duration threshold
    proxy.log_metric(
        "otel_claude_code_session_duration_seconds",
        8000,  # Exceeds max_session_duration threshold of 7200
        labels={
            "session_id": "test-session-003",
            "status": "active",
            "project": "long-running-project"
        }
    )
    print("Long session metric logged (check logs for threshold warning)")
    print()


def test_prometheus_simulation(proxy):
    """Test Prometheus format simulation"""
    print("=== Testing Prometheus Format Simulation ===")
    
    # Log some metrics and show Prometheus format
    proxy.log_metric(
        "otel_claude_code_error_total",
        2,
        labels={
            "error_type": "tool_timeout",
            "session_id": "test-session-004",
            "tool_name": "Bash"
        }
    )
    
    # Show current metrics store
    print("Current Prometheus metrics store:")
    for key, metric in proxy.simulator.metrics_store.items():
        print(f"  {metric['formatted']}")
    print()


def test_session_summary_and_export(proxy):
    """Test session summary and export functionality"""
    print("=== Testing Session Summary and Export ===")
    
    # Get session summary
    summary = proxy.get_metrics_summary()
    print("Session Summary:")
    print(json.dumps(summary, indent=2, default=str))
    print()
    
    # Export session data
    export_file = proxy.export_session_data("test_session_export.json")
    print(f"Session data exported to: {export_file}")
    
    # Verify export file exists and show size
    export_path = Path(export_file)
    if export_path.exists():
        file_size = export_path.stat().st_size
        print(f"Export file size: {file_size:,} bytes")
    print()


def simulate_realistic_session(proxy):
    """Simulate a realistic Claude Code session"""
    print("=== Simulating Realistic Claude Code Session ===")
    
    session_id = "realistic-session-001"
    project = "claude-code-metrics-lab"
    
    # Session start
    print("Starting session...")
    start_time = time.time()
    
    # Initial token usage
    proxy.log_metric(
        "otel_claude_code_token_usage_tokens_total",
        500,
        labels={
            "model": "claude-3-sonnet",
            "token_type": "input",
            "session_id": session_id,
            "project": project
        }
    )
    
    # Tool usage simulation
    tools_used = ["Read", "Write", "Bash", "Glob", "Edit"]
    for i, tool in enumerate(tools_used):
        proxy.log_metric(
            "otel_claude_code_tool_usage_total",
            1,
            labels={
                "tool_name": tool,
                "session_id": session_id,
                "project": project,
                "status": "success"
            }
        )
        time.sleep(0.1)  # Small delay to simulate real usage
    
    # More token usage (responses)
    proxy.log_metric(
        "otel_claude_code_token_usage_tokens_total",
        1200,
        labels={
            "model": "claude-3-sonnet",
            "token_type": "output",
            "session_id": session_id,
            "project": project
        }
    )
    
    # Session completion
    session_duration = time.time() - start_time + 300  # Add some realistic duration
    proxy.log_metric(
        "otel_claude_code_session_duration_seconds",
        session_duration,
        labels={
            "session_id": session_id,
            "status": "completed",
            "project": project
        }
    )
    
    # Final cost calculation
    estimated_cost = 0.85
    proxy.log_metric(
        "otel_claude_code_cost_usd",
        estimated_cost,
        labels={
            "model": "claude-3-sonnet",
            "session_id": session_id,
            "project": project
        }
    )
    
    print(f"Realistic session completed:")
    print(f"  Duration: {session_duration:.2f} seconds")
    print(f"  Tools used: {len(tools_used)}")
    print(f"  Estimated cost: ${estimated_cost}")
    print()


def main():
    """Main test function"""
    print("Claude Code Metrics Logging Proxy Test")
    print("=" * 50)
    print()
    
    try:
        # Initialize proxy
        proxy = test_basic_functionality()
        
        # Run test suites
        test_valid_metrics(proxy)
        test_invalid_metrics(proxy)
        test_threshold_monitoring(proxy)
        test_prometheus_simulation(proxy)
        simulate_realistic_session(proxy)
        test_session_summary_and_export(proxy)
        
        print("=== All Tests Completed Successfully ===")
        
        # Final summary
        final_summary = proxy.get_metrics_summary()
        print(f"Total metrics logged: {final_summary['total_metrics']}")
        print(f"Valid metrics: {final_summary['validation_summary']['valid']}")
        print(f"Invalid metrics: {final_summary['validation_summary']['invalid']}")
        
    except Exception as e:
        print(f"Test failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()