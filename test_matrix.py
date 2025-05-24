#!/usr/bin/env python3
"""
Comprehensive Test Matrix for Claude Code Telemetry Configuration

This module generates and executes test scenarios covering all permutations
of telemetry configuration variables with detailed validation and debugging.
"""

import os
import json
import time
import itertools
import subprocess
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
import yaml


@dataclass
class TelemetryConfig:
    """Configuration for a telemetry test scenario"""
    enable_telemetry: bool
    metrics_exporter: str
    otlp_protocol: Optional[str] = None
    otlp_endpoint: Optional[str] = None
    export_interval: int = 10000
    timeout: int = 30000
    headers: Optional[str] = None
    description: str = ""
    expected_behavior: str = ""
    debugging_focus: str = ""


@dataclass
class TestResult:
    """Result of a telemetry test execution"""
    config: TelemetryConfig
    success: bool
    output: str
    error: Optional[str] = None
    metrics_collected: int = 0
    execution_time: float = 0.0
    validation_errors: List[str] = None
    debugging_notes: str = ""


class TelemetryTestMatrix:
    """Generates and executes comprehensive telemetry test matrix"""
    
    def __init__(self, output_dir: str = "test_results"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.results: List[TestResult] = []
        
    def generate_test_configurations(self) -> List[TelemetryConfig]:
        """Generate all permutations of telemetry configurations"""
        configurations = []
        
        # Base configuration dimensions
        exporters = ["otlp", "prometheus", "console", "logging", "none"]
        protocols = ["grpc", "http/protobuf", "http/json"]
        
        endpoints = [
            "http://localhost:4317",      # Local GRPC
            "http://localhost:4318",      # Local HTTP
            "http://pi.lan:4317",         # Remote GRPC  
            "http://pi.lan:4318",         # Remote HTTP
            "https://api.honeycomb.io",   # SaaS provider
            "http://invalid-endpoint",    # Invalid endpoint
            "http://unreachable:4317",    # Network failure
        ]
        
        intervals = [1000, 5000, 10000, 30000, 60000]  # milliseconds
        timeouts = [1000, 5000, 30000]  # milliseconds
        
        # Generate happy path configurations
        for exporter in exporters:
            if exporter in ["console", "logging", "none"]:
                # Non-OTLP exporters don't need protocol/endpoint
                config = TelemetryConfig(
                    enable_telemetry=True,
                    metrics_exporter=exporter,
                    export_interval=10000,
                    description=f"Basic {exporter} exporter test",
                    expected_behavior="Local output generation",
                    debugging_focus="Output format validation"
                )
                configurations.append(config)
                
            elif exporter == "prometheus":
                # Prometheus uses pull-based collection
                config = TelemetryConfig(
                    enable_telemetry=True,
                    metrics_exporter=exporter,
                    export_interval=30000,
                    description="Prometheus exposition format test",
                    expected_behavior="Metrics available at /metrics endpoint",
                    debugging_focus="Exposition format compliance"
                )
                configurations.append(config)
                
            elif exporter == "otlp":
                # OTLP configurations with different protocols and endpoints
                for protocol in protocols:
                    for endpoint in endpoints:
                        for interval in [10000, 30000]:  # Test key intervals
                            # Determine expected behavior based on endpoint
                            if "localhost" in endpoint:
                                expected = "Local collector ingestion"
                                debug_focus = "Local protocol debugging"
                            elif "pi.lan" in endpoint:
                                expected = "Remote collector transmission"
                                debug_focus = "Network connectivity validation"
                            elif "invalid" in endpoint or "unreachable" in endpoint:
                                expected = "Graceful error handling"
                                debug_focus = "Failure mode analysis"
                            else:
                                expected = "SaaS provider integration"
                                debug_focus = "Authentication and routing"
                            
                            config = TelemetryConfig(
                                enable_telemetry=True,
                                metrics_exporter=exporter,
                                otlp_protocol=protocol,
                                otlp_endpoint=endpoint,
                                export_interval=interval,
                                description=f"OTLP {protocol} to {endpoint}",
                                expected_behavior=expected,
                                debugging_focus=debug_focus
                            )
                            configurations.append(config)
        
        # Generate error condition tests
        error_configs = [
            TelemetryConfig(
                enable_telemetry=False,
                metrics_exporter="otlp",
                otlp_protocol="grpc",
                otlp_endpoint="http://localhost:4317",
                description="Telemetry disabled test",
                expected_behavior="No metrics generation",
                debugging_focus="Disable mechanism validation"
            ),
            TelemetryConfig(
                enable_telemetry=True,
                metrics_exporter="invalid_exporter",
                description="Invalid exporter test",
                expected_behavior="Configuration error",
                debugging_focus="Invalid configuration handling"
            ),
            TelemetryConfig(
                enable_telemetry=True,
                metrics_exporter="otlp",
                otlp_protocol="invalid_protocol",
                otlp_endpoint="http://localhost:4317",
                description="Invalid protocol test",
                expected_behavior="Protocol error",
                debugging_focus="Protocol validation"
            ),
            TelemetryConfig(
                enable_telemetry=True,
                metrics_exporter="otlp",
                otlp_protocol="grpc",
                otlp_endpoint="http://localhost:4317",
                timeout=100,  # Very short timeout
                description="Timeout test",
                expected_behavior="Timeout error handling",
                debugging_focus="Timeout behavior analysis"
            ),
            TelemetryConfig(
                enable_telemetry=True,
                metrics_exporter="otlp",
                otlp_protocol="grpc",
                otlp_endpoint="http://localhost:4317",
                headers="Authorization: Bearer invalid-token",
                description="Authentication failure test",
                expected_behavior="Auth error handling",
                debugging_focus="Authentication debugging"
            )
        ]
        
        configurations.extend(error_configs)
        
        # Generate performance test configurations
        performance_configs = []
        for interval in [100, 500, 1000]:  # High frequency intervals
            config = TelemetryConfig(
                enable_telemetry=True,
                metrics_exporter="console",
                export_interval=interval,
                description=f"High frequency test ({interval}ms)",
                expected_behavior="High throughput metrics",
                debugging_focus="Performance impact analysis"
            )
            performance_configs.append(config)
            
        configurations.extend(performance_configs)
        
        return configurations
    
    def execute_test(self, config: TelemetryConfig) -> TestResult:
        """Execute a single test configuration"""
        print(f"Executing: {config.description}")
        
        start_time = time.time()
        result = TestResult(
            config=config,
            success=False,
            output="",
            validation_errors=[]
        )
        
        try:
            # Set environment variables
            env = os.environ.copy()
            env["CLAUDE_CODE_ENABLE_TELEMETRY"] = "1" if config.enable_telemetry else "0"
            env["OTEL_METRICS_EXPORTER"] = config.metrics_exporter
            
            if config.otlp_protocol:
                env["OTEL_EXPORTER_OTLP_PROTOCOL"] = config.otlp_protocol
            if config.otlp_endpoint:
                env["OTEL_EXPORTER_OTLP_ENDPOINT"] = config.otlp_endpoint
            if config.timeout:
                env["OTEL_EXPORTER_OTLP_TIMEOUT"] = str(config.timeout)
            if config.headers:
                env["OTEL_EXPORTER_OTLP_HEADERS"] = config.headers
                
            env["OTEL_METRIC_EXPORT_INTERVAL"] = str(config.export_interval)
            
            # Execute test using logging proxy
            cmd = ["python", "src/logging_proxy.py"]
            process = subprocess.run(
                cmd,
                env=env,
                capture_output=True,
                text=True,
                timeout=30,
                cwd=str(Path.cwd())
            )
            
            result.output = process.stdout + process.stderr
            result.success = process.returncode == 0
            
            if not result.success:
                result.error = process.stderr
            
            # Validate output based on expected behavior
            result.validation_errors = self._validate_output(config, result.output)
            
            # Count metrics if available
            result.metrics_collected = self._count_metrics(result.output)
            
        except subprocess.TimeoutExpired:
            result.error = "Test execution timeout"
            result.debugging_notes = "Consider increasing timeout or checking for infinite loops"
        except Exception as e:
            result.error = str(e)
            result.debugging_notes = f"Unexpected error: {type(e).__name__}"
        
        result.execution_time = time.time() - start_time
        
        # Add debugging notes based on configuration
        if not result.success:
            result.debugging_notes += self._generate_debugging_notes(config, result)
        
        return result
    
    def _validate_output(self, config: TelemetryConfig, output: str) -> List[str]:
        """Validate test output against expected behavior"""
        errors = []
        
        if config.metrics_exporter == "console":
            if "METRIC_JSON:" not in output and "METRIC_PROMETHEUS:" not in output:
                errors.append("Expected console output not found")
        
        elif config.metrics_exporter == "logging":
            if "proxy.log" not in output and "Session data exported" not in output:
                errors.append("Expected logging output not found")
        
        elif config.metrics_exporter == "otlp":
            if config.otlp_endpoint and "invalid" in config.otlp_endpoint:
                if "error" not in output.lower():
                    errors.append("Expected error for invalid endpoint not found")
            elif "localhost" in (config.otlp_endpoint or ""):
                if "connection" in output.lower() and "refused" in output.lower():
                    errors.append("Local collector not available (expected for testing)")
        
        return errors
    
    def _count_metrics(self, output: str) -> int:
        """Count number of metrics in output"""
        return output.count("METRIC_JSON:") + output.count("METRIC_PROMETHEUS:")
    
    def _generate_debugging_notes(self, config: TelemetryConfig, result: TestResult) -> str:
        """Generate contextual debugging notes"""
        notes = []
        
        if config.metrics_exporter == "otlp":
            if "connection refused" in (result.error or "").lower():
                notes.append("Start local OTLP collector: docker run -p 4317:4317 -p 4318:4318 otel/opentelemetry-collector")
            
            if "invalid" in (config.otlp_endpoint or ""):
                notes.append("This is expected behavior for invalid endpoint testing")
            
            if config.timeout and config.timeout < 5000:
                notes.append("Short timeout may cause false failures; consider increasing for real scenarios")
        
        elif config.metrics_exporter == "prometheus":
            notes.append("Check /metrics endpoint availability and format compliance")
        
        return " | ".join(notes)
    
    def run_all_tests(self) -> Dict[str, Any]:
        """Execute all test configurations and generate comprehensive report"""
        configurations = self.generate_test_configurations()
        
        print(f"Generated {len(configurations)} test configurations")
        print("=" * 60)
        
        for i, config in enumerate(configurations, 1):
            print(f"[{i}/{len(configurations)}] {config.description}")
            result = self.execute_test(config)
            self.results.append(result)
            
            status = "✅ PASS" if result.success else "❌ FAIL"
            print(f"  {status} ({result.execution_time:.2f}s)")
            
            if result.validation_errors:
                print(f"  ⚠️  Validation: {'; '.join(result.validation_errors)}")
            
            if result.debugging_notes:
                print(f"  🔍 Debug: {result.debugging_notes}")
            
            print()
        
        # Generate comprehensive report
        report = self._generate_test_report()
        
        # Save results
        self._save_results()
        
        return report
    
    def _generate_test_report(self) -> Dict[str, Any]:
        """Generate comprehensive test report"""
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results if r.success)
        failed_tests = total_tests - passed_tests
        
        # Group by exporter type
        exporter_stats = {}
        for result in self.results:
            exporter = result.config.metrics_exporter
            if exporter not in exporter_stats:
                exporter_stats[exporter] = {"total": 0, "passed": 0, "failed": 0}
            
            exporter_stats[exporter]["total"] += 1
            if result.success:
                exporter_stats[exporter]["passed"] += 1
            else:
                exporter_stats[exporter]["failed"] += 1
        
        # Group by expected vs actual failures
        expected_failures = sum(1 for r in self.results 
                              if "error" in r.config.expected_behavior.lower() 
                              or "invalid" in r.config.description.lower()
                              or "timeout" in r.config.description.lower())
        
        unexpected_failures = failed_tests - expected_failures
        
        report = {
            "summary": {
                "total_tests": total_tests,
                "passed": passed_tests,
                "failed": failed_tests,
                "success_rate": f"{(passed_tests/total_tests)*100:.1f}%",
                "expected_failures": expected_failures,
                "unexpected_failures": unexpected_failures
            },
            "exporter_breakdown": exporter_stats,
            "configuration_coverage": {
                "exporters_tested": list(set(r.config.metrics_exporter for r in self.results)),
                "protocols_tested": list(set(r.config.otlp_protocol for r in self.results if r.config.otlp_protocol)),
                "endpoints_tested": list(set(r.config.otlp_endpoint for r in self.results if r.config.otlp_endpoint)),
                "intervals_tested": list(set(r.config.export_interval for r in self.results))
            },
            "debugging_insights": self._generate_debugging_insights(),
            "recommendations": self._generate_recommendations()
        }
        
        return report
    
    def _generate_debugging_insights(self) -> List[str]:
        """Generate debugging insights from test results"""
        insights = []
        
        # Analyze failure patterns
        otlp_failures = [r for r in self.results 
                        if r.config.metrics_exporter == "otlp" and not r.success]
        
        if otlp_failures:
            insights.append(f"OTLP failures: {len(otlp_failures)} tests failed, "
                          f"likely due to missing local collector")
        
        # Analyze timeout patterns
        timeout_tests = [r for r in self.results if r.config.timeout and r.config.timeout < 5000]
        if timeout_tests:
            insights.append(f"Short timeout tests: {len(timeout_tests)} configurations "
                          f"with timeouts < 5s may cause false failures")
        
        # Analyze performance impact
        high_freq_tests = [r for r in self.results if r.config.export_interval < 1000]
        if high_freq_tests:
            avg_time = sum(r.execution_time for r in high_freq_tests) / len(high_freq_tests)
            insights.append(f"High frequency tests averaged {avg_time:.2f}s execution time")
        
        return insights
    
    def _generate_recommendations(self) -> List[str]:
        """Generate recommendations for telemetry configuration"""
        recommendations = []
        
        # Based on test results, provide configuration recommendations
        console_results = [r for r in self.results if r.config.metrics_exporter == "console"]
        if all(r.success for r in console_results):
            recommendations.append("Console exporter: Reliable for local development and debugging")
        
        otlp_local_results = [r for r in self.results 
                             if r.config.metrics_exporter == "otlp" 
                             and r.config.otlp_endpoint 
                             and "localhost" in r.config.otlp_endpoint]
        
        if any(r.success for r in otlp_local_results):
            recommendations.append("OTLP local: Requires running collector but provides full pipeline testing")
        
        recommendations.append("Start with console exporter for development, progress to OTLP for integration")
        recommendations.append("Use logging proxy for payload inspection and validation")
        recommendations.append("Test error scenarios regularly to ensure graceful degradation")
        
        return recommendations
    
    def _save_results(self):
        """Save test results to files"""
        # Save detailed results as JSON
        results_file = self.output_dir / "test_results.json"
        with open(results_file, 'w') as f:
            json.dump([asdict(result) for result in self.results], f, indent=2, default=str)
        
        # Save summary report
        report = self._generate_test_report()
        report_file = self.output_dir / "test_report.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        # Save configuration matrix as YAML
        configs = [asdict(result.config) for result in self.results]
        config_file = self.output_dir / "configuration_matrix.yaml"
        with open(config_file, 'w') as f:
            yaml.dump(configs, f, default_flow_style=False)
        
        print(f"Results saved to {self.output_dir}/")
        print(f"  - {results_file.name}: Detailed test results")
        print(f"  - {report_file.name}: Summary report")
        print(f"  - {config_file.name}: Configuration matrix")


def main():
    """Main function to run the test matrix"""
    print("Claude Code Telemetry Configuration Test Matrix")
    print("=" * 60)
    
    matrix = TelemetryTestMatrix()
    report = matrix.run_all_tests()
    
    print("=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    summary = report["summary"]
    print(f"Total Tests: {summary['total_tests']}")
    print(f"Passed: {summary['passed']}")
    print(f"Failed: {summary['failed']}")
    print(f"Success Rate: {summary['success_rate']}")
    print(f"Expected Failures: {summary['expected_failures']}")
    print(f"Unexpected Failures: {summary['unexpected_failures']}")
    
    print("\nEXPORTER BREAKDOWN:")
    for exporter, stats in report["exporter_breakdown"].items():
        print(f"  {exporter}: {stats['passed']}/{stats['total']} passed")
    
    print("\nDEBUGGING INSIGHTS:")
    for insight in report["debugging_insights"]:
        print(f"  • {insight}")
    
    print("\nRECOMMENDATIONS:")
    for rec in report["recommendations"]:
        print(f"  • {rec}")


if __name__ == "__main__":
    main()