#!/usr/bin/env python3
"""
Dashboard Performance Testing Framework

Implementation of the testing scenarios and validation framework
from the RFC: Simulator and Development Instance
"""

import time
import requests
import json
import logging
import yaml
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass
class PerformanceTest:
    """Represents a dashboard performance test"""
    name: str
    dashboard_id: str
    time_range: str
    max_load_time: float  # seconds
    max_query_time: float  # seconds
    expected_panels: int


@dataclass
class TestResult:
    """Represents test execution results"""
    test_name: str
    success: bool
    load_time: float
    query_times: List[float]
    error_message: Optional[str] = None
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


class DashboardTester:
    """Framework for testing dashboard performance and functionality"""
    
    def __init__(self, grafana_url: str, prometheus_url: str, 
                 api_key: Optional[str] = None):
        self.grafana_url = grafana_url.rstrip('/')
        self.prometheus_url = prometheus_url.rstrip('/')
        self.api_key = api_key
        self.session = requests.Session()
        
        if api_key:
            self.session.headers.update({
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json'
            })
        
        self.logger = self._setup_logging()
        self.test_results: List[TestResult] = []
    
    def _setup_logging(self) -> logging.Logger:
        """Setup logging configuration"""
        logger = logging.getLogger(f"{__name__}.DashboardTester")
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    def test_dashboard_load_time(self, dashboard_uid: str, 
                                time_range: str = "1h") -> TestResult:
        """Test dashboard load time performance"""
        test_name = f"dashboard_load_{dashboard_uid}_{time_range}"
        
        try:
            start_time = time.time()
            
            # Get dashboard definition
            response = self.session.get(
                f"{self.grafana_url}/api/dashboards/uid/{dashboard_uid}"
            )
            
            if response.status_code != 200:
                return TestResult(
                    test_name=test_name,
                    success=False,
                    load_time=0,
                    query_times=[],
                    error_message=f"Failed to load dashboard: {response.status_code}"
                )
            
            load_time = time.time() - start_time
            dashboard_data = response.json()
            
            # Test individual panel queries
            query_times = self._test_panel_queries(
                dashboard_data.get('dashboard', {}),
                time_range
            )
            
            success = load_time < 2.0  # 2 second threshold
            
            result = TestResult(
                test_name=test_name,
                success=success,
                load_time=load_time,
                query_times=query_times
            )
            
            self.test_results.append(result)
            
            self.logger.info(
                f"Dashboard {dashboard_uid} load time: {load_time:.3f}s, "
                f"Avg query time: {sum(query_times)/len(query_times):.3f}s"
            )
            
            return result
            
        except Exception as e:
            result = TestResult(
                test_name=test_name,
                success=False,
                load_time=0,
                query_times=[],
                error_message=str(e)
            )
            self.test_results.append(result)
            return result
    
    def _test_panel_queries(self, dashboard: Dict[str, Any], 
                           time_range: str) -> List[float]:
        """Test individual panel query performance"""
        query_times = []
        panels = dashboard.get('panels', [])
        
        # Calculate time range for queries
        now = int(time.time() * 1000)
        range_seconds = self._parse_time_range(time_range)
        from_time = now - (range_seconds * 1000)
        
        for panel in panels:
            panel_type = panel.get('type', '')
            if panel_type in ['graph', 'stat', 'table', 'heatmap']:
                targets = panel.get('targets', [])
                
                for target in targets:
                    query = target.get('expr', '')
                    if query:
                        query_time = self._test_prometheus_query(
                            query, from_time, now, range_seconds
                        )
                        if query_time > 0:
                            query_times.append(query_time)
        
        return query_times
    
    def _test_prometheus_query(self, query: str, start: int, end: int, 
                              step: int) -> float:
        """Test individual Prometheus query performance"""
        try:
            start_time = time.time()
            
            params = {
                'query': query,
                'start': start // 1000,  # Convert to seconds
                'end': end // 1000,
                'step': min(step // 100, 60)  # Reasonable step size
            }
            
            response = requests.get(
                f"{self.prometheus_url}/api/v1/query_range",
                params=params,
                timeout=10
            )
            
            query_time = time.time() - start_time
            
            if response.status_code == 200:
                return query_time
            else:
                self.logger.warning(f"Query failed: {query} - {response.status_code}")
                return 0
                
        except Exception as e:
            self.logger.warning(f"Query error: {query} - {str(e)}")
            return 0
    
    def _parse_time_range(self, time_range: str) -> int:
        """Parse Grafana time range to seconds"""
        time_range = time_range.lower()
        
        if time_range.endswith('m'):
            return int(time_range[:-1]) * 60
        elif time_range.endswith('h'):
            return int(time_range[:-1]) * 3600
        elif time_range.endswith('d'):
            return int(time_range[:-1]) * 86400
        else:
            return 3600  # Default 1 hour
    
    def test_cardinality_limits(self) -> TestResult:
        """Test cardinality limits and series counts"""
        test_name = "cardinality_limits"
        
        try:
            # Query total series count
            response = requests.get(
                f"{self.prometheus_url}/api/v1/query",
                params={'query': 'prometheus_tsdb_head_series'}
            )
            
            if response.status_code != 200:
                return TestResult(
                    test_name=test_name,
                    success=False,
                    load_time=0,
                    query_times=[],
                    error_message="Failed to query series count"
                )
            
            data = response.json()
            series_count = 0
            
            if data['status'] == 'success' and data['data']['result']:
                series_count = int(float(data['data']['result'][0]['value'][1]))
            
            # Check against limits (1M series)
            success = series_count < 1000000
            
            result = TestResult(
                test_name=test_name,
                success=success,
                load_time=0,
                query_times=[],
                error_message=None if success else f"Series count too high: {series_count}"
            )
            
            self.test_results.append(result)
            self.logger.info(f"Current series count: {series_count}")
            
            return result
            
        except Exception as e:
            result = TestResult(
                test_name=test_name,
                success=False,
                load_time=0,
                query_times=[],
                error_message=str(e)
            )
            self.test_results.append(result)
            return result
    
    def run_performance_benchmark(self, config_file: str) -> Dict[str, Any]:
        """Run comprehensive performance benchmark suite"""
        self.logger.info("Starting performance benchmark suite")
        
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
        
        benchmarks = config.get('benchmarks', {})
        results = {
            'timestamp': datetime.now().isoformat(),
            'total_tests': 0,
            'passed_tests': 0,
            'failed_tests': 0,
            'test_results': []
        }
        
        # Test dashboard load times
        dashboard_config = benchmarks.get('dashboard_load', {})
        if dashboard_config:
            # Test main dashboards
            dashboards = ['claude-metrics-overview', 'claude-cost-tracking']
            for dashboard in dashboards:
                result = self.test_dashboard_load_time(
                    dashboard,
                    dashboard_config.get('time_range', '24h')
                )
                results['test_results'].append(result)
                results['total_tests'] += 1
                if result.success:
                    results['passed_tests'] += 1
                else:
                    results['failed_tests'] += 1
        
        # Test query performance
        query_config = benchmarks.get('query_performance', {})
        if query_config:
            test_queries = [
                ('simple_counter', 'otel_claude_code_session_count_total'),
                ('rate_calculation', 'rate(otel_claude_code_session_count_total[5m])'),
                ('histogram_quantile', 
                 'histogram_quantile(0.95, otel_claude_code_session_duration_seconds_bucket)')
            ]
            
            for query_name, query in test_queries:
                max_time = query_config.get(query_name, 1000) / 1000  # Convert ms to s
                query_time = self._test_prometheus_query(
                    query, 
                    int(time.time() - 3600) * 1000,  # 1 hour ago
                    int(time.time()) * 1000,         # now
                    3600                             # 1 hour range
                )
                
                success = query_time > 0 and query_time < max_time
                result = TestResult(
                    test_name=f"query_{query_name}",
                    success=success,
                    load_time=query_time,
                    query_times=[query_time],
                    error_message=None if success else f"Query too slow: {query_time:.3f}s"
                )
                
                results['test_results'].append(result)
                results['total_tests'] += 1
                if result.success:
                    results['passed_tests'] += 1
                else:
                    results['failed_tests'] += 1
        
        # Test cardinality limits
        cardinality_result = self.test_cardinality_limits()
        results['test_results'].append(cardinality_result)
        results['total_tests'] += 1
        if cardinality_result.success:
            results['passed_tests'] += 1
        else:
            results['failed_tests'] += 1
        
        self.logger.info(
            f"Benchmark completed: {results['passed_tests']}/{results['total_tests']} tests passed"
        )
        
        return results
    
    def generate_report(self, output_file: str):
        """Generate HTML performance report"""
        if not self.test_results:
            self.logger.warning("No test results to report")
            return
        
        html_content = self._generate_html_report()
        
        with open(output_file, 'w') as f:
            f.write(html_content)
        
        self.logger.info(f"Performance report generated: {output_file}")
    
    def _generate_html_report(self) -> str:
        """Generate HTML report content"""
        passed = sum(1 for r in self.test_results if r.success)
        total = len(self.test_results)
        
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Dashboard Performance Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .summary {{ background: #f5f5f5; padding: 15px; border-radius: 5px; }}
        .test-result {{ margin: 10px 0; padding: 10px; border-radius: 3px; }}
        .success {{ background: #d4edda; border-left: 4px solid #28a745; }}
        .failure {{ background: #f8d7da; border-left: 4px solid #dc3545; }}
        table {{ width: 100%; border-collapse: collapse; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
    </style>
</head>
<body>
    <h1>Claude Code Metrics Dashboard Performance Report</h1>
    
    <div class="summary">
        <h2>Summary</h2>
        <p><strong>Tests Passed:</strong> {passed}/{total}</p>
        <p><strong>Success Rate:</strong> {(passed/total*100):.1f}%</p>
        <p><strong>Generated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>
    
    <h2>Test Results</h2>
    <table>
        <tr>
            <th>Test Name</th>
            <th>Status</th>
            <th>Load Time</th>
            <th>Avg Query Time</th>
            <th>Error Message</th>
        </tr>
"""
        
        for result in self.test_results:
            status_class = "success" if result.success else "failure"
            status_text = "PASS" if result.success else "FAIL"
            avg_query_time = sum(result.query_times) / len(result.query_times) if result.query_times else 0
            
            html += f"""
        <tr class="{status_class}">
            <td>{result.test_name}</td>
            <td>{status_text}</td>
            <td>{result.load_time:.3f}s</td>
            <td>{avg_query_time:.3f}s</td>
            <td>{result.error_message or ''}</td>
        </tr>
"""
        
        html += """
    </table>
</body>
</html>
"""
        return html


def main():
    """Main function for running dashboard tests"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Dashboard Performance Tester")
    parser.add_argument("--grafana-url", default="http://localhost:3001", 
                       help="Grafana URL")
    parser.add_argument("--prometheus-url", default="http://localhost:9091",
                       help="Prometheus URL")
    parser.add_argument("--config", default="config/simulator-config.yml",
                       help="Configuration file")
    parser.add_argument("--dashboard", help="Specific dashboard UID to test")
    parser.add_argument("--output", default="test_results/dashboard_performance.html",
                       help="Output report file")
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    tester = DashboardTester(args.grafana_url, args.prometheus_url)
    
    if args.dashboard:
        # Test specific dashboard
        result = tester.test_dashboard_load_time(args.dashboard)
        print(f"Dashboard {args.dashboard}: {'PASS' if result.success else 'FAIL'}")
    else:
        # Run full benchmark suite
        results = tester.run_performance_benchmark(args.config)
        print(f"Benchmark results: {results['passed_tests']}/{results['total_tests']} tests passed")
    
    # Generate report
    tester.generate_report(args.output)


if __name__ == "__main__":
    main()