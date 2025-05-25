#!/usr/bin/env python3
"""
Scenario Runner for Automated Testing

Implementation of automated scenario execution and validation
from the RFC: Simulator and Development Instance
"""

import time
import requests
import json
import yaml
import logging
import concurrent.futures
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import threading


@dataclass
class ScenarioResult:
    """Results from scenario execution"""
    scenario_name: str
    success: bool
    duration: float
    metrics_collected: int
    assertions_passed: int
    assertions_failed: int
    error_message: Optional[str] = None
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


class ScenarioRunner:
    """Automated scenario execution and validation framework"""
    
    def __init__(self, simulator_url: str, prometheus_url: str, 
                 grafana_url: str, config_file: str):
        self.simulator_url = simulator_url.rstrip('/')
        self.prometheus_url = prometheus_url.rstrip('/')
        self.grafana_url = grafana_url.rstrip('/')
        
        with open(config_file, 'r') as f:
            self.config = yaml.safe_load(f)
        
        self.logger = self._setup_logging()
        self.results: List[ScenarioResult] = []
    
    def _setup_logging(self) -> logging.Logger:
        """Setup logging configuration"""
        logger = logging.getLogger(f"{__name__}.ScenarioRunner")
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    def run_scenario(self, scenario_name: str) -> ScenarioResult:
        """Run a single scenario and validate results"""
        if scenario_name not in self.config['scenarios']:
            return ScenarioResult(
                scenario_name=scenario_name,
                success=False,
                duration=0,
                metrics_collected=0,
                assertions_passed=0,
                assertions_failed=1,
                error_message=f"Scenario '{scenario_name}' not found"
            )
        
        scenario = self.config['scenarios'][scenario_name]
        self.logger.info(f"Starting scenario: {scenario_name}")
        
        start_time = time.time()
        
        try:
            # Start the scenario on the simulator
            response = requests.post(
                f"{self.simulator_url}/scenario",
                json={
                    'scenario': scenario_name,
                    'duration': scenario.get('duration', 3600)
                },
                timeout=10
            )
            
            if response.status_code != 200:
                return ScenarioResult(
                    scenario_name=scenario_name,
                    success=False,
                    duration=time.time() - start_time,
                    metrics_collected=0,
                    assertions_passed=0,
                    assertions_failed=1,
                    error_message=f"Failed to start scenario: {response.status_code}"
                )
            
            # Monitor scenario execution
            duration = scenario.get('duration', 3600)
            metrics_collected = self._monitor_scenario(scenario_name, duration)
            
            # Wait for scenario completion
            self._wait_for_completion(scenario_name, duration)
            
            # Validate assertions
            assertions_passed, assertions_failed = self._validate_assertions(scenario)
            
            execution_time = time.time() - start_time
            success = assertions_failed == 0
            
            result = ScenarioResult(
                scenario_name=scenario_name,
                success=success,
                duration=execution_time,
                metrics_collected=metrics_collected,
                assertions_passed=assertions_passed,
                assertions_failed=assertions_failed
            )
            
            self.results.append(result)
            
            self.logger.info(
                f"Scenario {scenario_name} completed: "
                f"{'SUCCESS' if success else 'FAILED'} in {execution_time:.1f}s"
            )
            
            return result
            
        except Exception as e:
            result = ScenarioResult(
                scenario_name=scenario_name,
                success=False,
                duration=time.time() - start_time,
                metrics_collected=0,
                assertions_passed=0,
                assertions_failed=1,
                error_message=str(e)
            )
            self.results.append(result)
            return result
    
    def _monitor_scenario(self, scenario_name: str, duration: float) -> int:
        """Monitor scenario execution and collect metrics"""
        metrics_collected = 0
        check_interval = 30  # Check every 30 seconds
        checks = int(duration / check_interval)
        
        for i in range(checks):
            try:
                # Check simulator health
                response = requests.get(f"{self.simulator_url}/health", timeout=5)
                if response.status_code == 200:
                    health_data = response.json()
                    self.logger.debug(
                        f"Scenario {scenario_name} progress: "
                        f"{health_data.get('total_sessions', 0)} sessions, "
                        f"${health_data.get('total_cost', 0):.2f} cost"
                    )
                
                # Collect metrics count
                response = requests.get(f"{self.prometheus_url}/api/v1/label/__name__/values", timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    if data['status'] == 'success':
                        metrics_collected = len([m for m in data['data'] if 'otel_claude_code' in m])
                
                time.sleep(check_interval)
                
            except Exception as e:
                self.logger.warning(f"Monitoring error: {e}")
        
        return metrics_collected
    
    def _wait_for_completion(self, scenario_name: str, duration: float):
        """Wait for scenario to complete"""
        end_time = time.time() + duration + 30  # Add buffer
        
        while time.time() < end_time:
            try:
                response = requests.get(f"{self.simulator_url}/health", timeout=5)
                if response.status_code == 200:
                    health_data = response.json()
                    if health_data.get('status') == 'stopped':
                        self.logger.info(f"Scenario {scenario_name} completed")
                        return
                
                time.sleep(5)
                
            except Exception as e:
                self.logger.warning(f"Completion check error: {e}")
                time.sleep(5)
        
        self.logger.warning(f"Scenario {scenario_name} may not have completed properly")
    
    def _validate_assertions(self, scenario: Dict[str, Any]) -> tuple[int, int]:
        """Validate scenario assertions"""
        assertions = scenario.get('assertions', [])
        passed = 0
        failed = 0
        
        for assertion in assertions:
            metric = assertion['metric']
            condition = assertion['condition']
            
            try:
                if self._check_assertion(metric, condition):
                    passed += 1
                    self.logger.debug(f"Assertion passed: {metric} {condition}")
                else:
                    failed += 1
                    self.logger.warning(f"Assertion failed: {metric} {condition}")
            except Exception as e:
                failed += 1
                self.logger.error(f"Assertion error: {metric} {condition} - {e}")
        
        return passed, failed
    
    def _check_assertion(self, metric: str, condition: str) -> bool:
        """Check individual assertion"""
        # Parse condition (e.g., "< 0.05", "> 1000", "= 0")
        operator = condition.split()[0]
        threshold = float(condition.split()[1])
        
        # Get metric value from Prometheus
        metric_value = self._get_metric_value(metric)
        
        if metric_value is None:
            return False
        
        if operator == '<':
            return metric_value < threshold
        elif operator == '>':
            return metric_value > threshold
        elif operator == '=':
            return abs(metric_value - threshold) < 0.001
        elif operator == '<=':
            return metric_value <= threshold
        elif operator == '>=':
            return metric_value >= threshold
        else:
            return False
    
    def _get_metric_value(self, metric: str) -> Optional[float]:
        """Get current metric value from Prometheus"""
        try:
            if metric == 'error_rate':
                # Calculate error rate
                query = '''
                    rate(otel_claude_code_error_total[5m]) /
                    rate(otel_claude_code_session_count_total[5m])
                '''
            elif metric == 'avg_session_duration':
                # Calculate average session duration
                query = '''
                    rate(otel_claude_code_session_duration_seconds_sum[5m]) /
                    rate(otel_claude_code_session_duration_seconds_count[5m])
                '''
            elif metric == 'p99_latency':
                # Calculate 99th percentile latency (simulated)
                query = '''
                    histogram_quantile(0.99, 
                        rate(otel_claude_code_session_duration_seconds_bucket[5m])
                    )
                '''
            elif metric == 'cost_efficiency':
                # Calculate cost efficiency (tokens per dollar)
                query = '''
                    rate(otel_claude_code_token_usage_tokens_total[5m]) /
                    rate(otel_claude_code_cost_usage_USD_total[5m])
                '''
            elif metric == 'response_time':
                # Use session duration as proxy for response time
                query = '''
                    histogram_quantile(0.95,
                        rate(otel_claude_code_session_duration_seconds_bucket[5m])
                    )
                '''
            else:
                # Direct metric query
                query = metric
            
            response = requests.get(
                f"{self.prometheus_url}/api/v1/query",
                params={'query': query},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if data['status'] == 'success' and data['data']['result']:
                    return float(data['data']['result'][0]['value'][1])
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error getting metric {metric}: {e}")
            return None
    
    def run_all_scenarios(self) -> Dict[str, Any]:
        """Run all configured scenarios"""
        self.logger.info("Starting automated scenario execution")
        
        scenario_names = list(self.config['scenarios'].keys())
        results = {
            'timestamp': datetime.now().isoformat(),
            'total_scenarios': len(scenario_names),
            'successful_scenarios': 0,
            'failed_scenarios': 0,
            'results': []
        }
        
        for scenario_name in scenario_names:
            result = self.run_scenario(scenario_name)
            results['results'].append(asdict(result))
            
            if result.success:
                results['successful_scenarios'] += 1
            else:
                results['failed_scenarios'] += 1
            
            # Brief pause between scenarios
            time.sleep(10)
        
        self.logger.info(
            f"All scenarios completed: "
            f"{results['successful_scenarios']}/{results['total_scenarios']} successful"
        )
        
        return results
    
    def run_concurrent_scenarios(self, scenario_names: List[str], 
                               max_workers: int = 3) -> Dict[str, Any]:
        """Run multiple scenarios concurrently"""
        self.logger.info(f"Starting {len(scenario_names)} scenarios concurrently")
        
        results = {
            'timestamp': datetime.now().isoformat(),
            'total_scenarios': len(scenario_names),
            'successful_scenarios': 0,
            'failed_scenarios': 0,
            'results': []
        }
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_scenario = {
                executor.submit(self.run_scenario, name): name 
                for name in scenario_names
            }
            
            for future in concurrent.futures.as_completed(future_to_scenario):
                scenario_name = future_to_scenario[future]
                try:
                    result = future.result()
                    results['results'].append(asdict(result))
                    
                    if result.success:
                        results['successful_scenarios'] += 1
                    else:
                        results['failed_scenarios'] += 1
                        
                except Exception as e:
                    self.logger.error(f"Scenario {scenario_name} failed: {e}")
                    results['failed_scenarios'] += 1
        
        return results
    
    def generate_report(self, output_file: str):
        """Generate test execution report"""
        if not self.results:
            self.logger.warning("No results to report")
            return
        
        report_data = {
            'summary': {
                'total_scenarios': len(self.results),
                'successful': sum(1 for r in self.results if r.success),
                'failed': sum(1 for r in self.results if not r.success),
                'total_duration': sum(r.duration for r in self.results),
                'total_metrics': sum(r.metrics_collected for r in self.results),
                'generated_at': datetime.now().isoformat()
            },
            'results': [asdict(result) for result in self.results]
        }
        
        with open(output_file, 'w') as f:
            json.dump(report_data, f, indent=2, default=str)
        
        self.logger.info(f"Test report generated: {output_file}")


def main():
    """Main function for scenario runner"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Scenario Runner")
    parser.add_argument("--simulator-url", default="http://localhost:8000",
                       help="Simulator URL")
    parser.add_argument("--prometheus-url", default="http://localhost:9091",
                       help="Prometheus URL")
    parser.add_argument("--grafana-url", default="http://localhost:3001",
                       help="Grafana URL")
    parser.add_argument("--config", default="config/simulator-config.yml",
                       help="Configuration file")
    parser.add_argument("--scenario", help="Specific scenario to run")
    parser.add_argument("--all", action="store_true", help="Run all scenarios")
    parser.add_argument("--concurrent", nargs='+', help="Run scenarios concurrently")
    parser.add_argument("--output", default="test_results/scenario_results.json",
                       help="Output report file")
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    runner = ScenarioRunner(
        args.simulator_url,
        args.prometheus_url,
        args.grafana_url,
        args.config
    )
    
    if args.scenario:
        # Run single scenario
        result = runner.run_scenario(args.scenario)
        print(f"Scenario {args.scenario}: {'SUCCESS' if result.success else 'FAILED'}")
    elif args.all:
        # Run all scenarios
        results = runner.run_all_scenarios()
        print(f"All scenarios: {results['successful_scenarios']}/{results['total_scenarios']} successful")
    elif args.concurrent:
        # Run scenarios concurrently
        results = runner.run_concurrent_scenarios(args.concurrent)
        print(f"Concurrent scenarios: {results['successful_scenarios']}/{results['total_scenarios']} successful")
    else:
        print("Please specify --scenario, --all, or --concurrent")
        return
    
    # Generate report
    runner.generate_report(args.output)


if __name__ == "__main__":
    main()