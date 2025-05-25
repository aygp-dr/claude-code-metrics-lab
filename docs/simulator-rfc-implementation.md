# Enhanced Metrics Simulator Implementation

This document describes the implementation of the RFC: Metrics Dashboard Simulator and Development Instance.

## Overview

The enhanced simulator provides a comprehensive framework for testing Prometheus metrics and Grafana dashboards with realistic user behavior patterns, fault injection, and scenario-based testing.

## Architecture

### Core Components

1. **Enhanced Metrics Simulator** (`src/metrics_simulator.py`)
   - User population modeling with power, regular, and idle users
   - Brownian motion activity models with seasonal variations
   - Comprehensive metrics generation for Claude Code telemetry
   - HTTP API for control and monitoring

2. **Docker Development Environment** (`docker-compose.dev.yml`)
   - Isolated Prometheus instance (port 9091)
   - Isolated Grafana instance (port 3001)
   - AlertManager for testing alerts
   - OTEL Collector for telemetry processing
   - Redis for session storage
   - Nginx for load balancing tests

3. **Testing Framework**
   - `scripts/test_dashboard.py` - Dashboard performance testing
   - `scripts/scenario_runner.py` - Automated scenario execution
   - Performance benchmarking and validation

4. **Configuration Management**
   - `config/simulator-config.yml` - Comprehensive simulator configuration
   - `config/prometheus-dev.yml` - Development Prometheus setup
   - Multiple scenario definitions with timeline events

## Key Features Implemented

### 1. User Population Modeling

```yaml
users:
  total: 100
  distribution:
    power_users:
      percentage: 0.1
      activity_range: [2.0, 3.5]
      volatility: 0.2
    regular_users:
      percentage: 0.7
      activity_range: [0.8, 1.5]
      volatility: 0.3
    idle_users:
      percentage: 0.2
      activity_range: [0.1, 0.5]
      volatility: 0.4
```

### 2. Activity Models

- **Brownian Motion**: Realistic activity variations with mean reversion
- **Seasonal Patterns**: Business hours and weekend adjustments
- **Burst Patterns**: Configurable spike generation for load testing

### 3. Scenario Management

Implemented scenarios:
- **Baseline**: Normal operation patterns
- **Black Friday**: High load with 10x traffic and failure injection
- **Gradual Rollout**: Progressive user onboarding simulation
- **Disaster Recovery**: Outage and recovery testing
- **Stress Test**: Breaking point identification

### 4. Comprehensive Metrics

Generated metrics match production Claude Code telemetry:
- Session counts and durations
- Token usage by model and type
- Cost tracking in USD
- Tool usage patterns
- Error rates and types
- Commit metrics

### 5. Fault Injection

- Model outages and degradation
- Network latency simulation
- Authentication failures
- Resource exhaustion scenarios

### 6. Validation Framework

- Dashboard load time testing
- Query performance benchmarking
- Cardinality monitoring
- Assertion-based scenario validation

## Usage

### Quick Start

```bash
# Start complete development environment
make dev-env

# Start enhanced simulator
make simulate-enhanced

# Run scenario tests
make test-scenarios

# Test dashboard performance
make test-dashboard
```

### Available Make Commands

#### Simulator Commands
- `make simulate-enhanced` - Start enhanced simulator
- `make simulate-docker` - Start in Docker environment
- `make simulate-black-friday` - Quick Black Friday scenario
- `make simulate-stress-test` - Quick stress test

#### Environment Management
- `make dev-env` - Start complete development stack
- `make dev-env-down` - Stop development environment
- `make dev-env-logs` - View environment logs

#### Testing Commands
- `make test-scenarios` - Run all scenario tests
- `make test-scenario SCENARIO=baseline` - Run specific scenario
- `make test-dashboard` - Test dashboard performance
- `make test-concurrent` - Run concurrent scenarios

#### Monitoring Commands
- `make monitor-cardinality` - Monitor Prometheus cardinality
- `make export-test-data` - Export metrics for analysis
- `make validate-config` - Validate configuration

### Configuration

The simulator uses `config/simulator-config.yml` for comprehensive configuration:

```yaml
# User populations
users:
  total: 100
  distribution: {...}

# Model costs and distributions
model_distribution: {...}
costs_per_1k_tokens: {...}

# Test scenarios with timelines
scenarios:
  black_friday:
    duration: 14400
    timeline:
      - time: 600
        event: "increase_load"
        multiplier: 3.0
      - time: 7200
        event: "inject_failure"
        type: "model_outage"
```

### Docker Environment

Access points for development environment:
- **Prometheus**: http://localhost:9091
- **Grafana**: http://localhost:3001 (admin/admin123)
- **Simulator API**: http://localhost:8000
- **Simulator Metrics**: http://localhost:8001/metrics
- **AlertManager**: http://localhost:9093

## Testing Scenarios

### 1. Dashboard Performance Testing

```bash
# Test specific dashboard
python scripts/test_dashboard.py --dashboard claude-metrics-overview

# Full performance benchmark
python scripts/test_dashboard.py --config config/simulator-config.yml
```

### 2. Scenario Execution

```bash
# Run single scenario
python scripts/scenario_runner.py --scenario black_friday

# Run all scenarios
python scripts/scenario_runner.py --all

# Concurrent scenarios
python scripts/scenario_runner.py --concurrent baseline stress_test
```

### 3. Automated Validation

Each scenario includes assertions:
```yaml
assertions:
  - metric: "error_rate"
    condition: "< 0.05"
  - metric: "p99_latency"
    condition: "< 5000"
```

## Performance Benchmarks

Configured thresholds:
- Dashboard load time: < 2 seconds
- Simple counter queries: < 100ms
- Rate calculations: < 500ms
- Histogram quantiles: < 1 second
- Total series: < 1M
- Per-metric series: < 10K

## Metrics Generated

The simulator generates realistic Claude Code metrics:

```
otel_claude_code_session_count_total
otel_claude_code_token_usage_tokens_total
otel_claude_code_cost_usage_USD_total
otel_claude_code_tool_usage_total
otel_claude_code_error_total
otel_claude_code_commit_count_total
otel_claude_code_session_duration_seconds
otel_claude_code_active_sessions
```

## Implementation Benefits

### For Development
- Safe testing environment isolated from production
- Realistic data patterns for dashboard development
- Early performance issue detection
- Reproducible test conditions

### For Operations
- Capacity planning with growth projections
- Disaster recovery validation
- Alert threshold optimization
- Query performance optimization

### For Product
- A/B testing of dashboard designs
- User behavior pattern analysis
- Cost estimation for different usage levels
- Metric usefulness validation

## Integration with Existing Codebase

The implementation enhances the existing simulator while maintaining compatibility:
- Existing `scripts/claude-metrics-simulator.py` preserved
- New enhanced simulator in `src/metrics_simulator.py`
- Makefile extended with new commands
- Configuration follows existing patterns

## Future Enhancements

Potential improvements:
1. Machine learning for more realistic user patterns
2. Integration with production trace replay
3. Automated dashboard generation based on scenarios
4. Real-time alerting during scenario execution
5. Integration with CI/CD pipelines for automated testing

## Troubleshooting

### Common Issues

1. **Configuration validation failed**
   ```bash
   make validate-config
   ```

2. **Docker services not starting**
   ```bash
   docker-compose -f docker-compose.dev.yml logs
   ```

3. **Metrics not appearing**
   - Check simulator health: `curl http://localhost:8000/health`
   - Verify Prometheus scraping: http://localhost:9091/targets

4. **Performance tests failing**
   - Ensure development environment is running
   - Check resource availability
   - Review test thresholds in configuration

### Logs and Debugging

- Simulator logs: Check container logs or stdout
- Prometheus logs: `docker-compose logs prometheus-dev`
- Grafana logs: `docker-compose logs grafana-dev`
- Test results: `test_results/` directory

## Conclusion

This implementation provides a comprehensive simulator that meets all requirements from the RFC:
- ✅ Configurable user populations with realistic activity models
- ✅ Complete Docker development environment
- ✅ Fault injection and scenario management
- ✅ Performance testing and validation framework
- ✅ Integration with existing toolchain
- ✅ Comprehensive documentation and usage examples

The system enables safe validation of dashboard performance, alert thresholds, and capacity planning under realistic load conditions before production deployment.