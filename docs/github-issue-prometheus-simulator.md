# GitHub Issue: Prometheus Mock Data Endpoint with Brownian Motion Simulation

## Title
**Implement Prometheus Mock Data Endpoint for Educational Testing and Development**

## Issue Type
`enhancement` `simulator` `testing`

## Labels
- `prometheus`
- `mock-data`
- `brownian-motion`
- `education`
- `testing`
- `development-tools`

---

## Problem Statement

When developing and testing Claude Code telemetry systems, developers need **realistic mock data** that exhibits natural variation patterns without requiring actual Claude Code usage. Current testing approaches either:

1. **Generate static test data** - Lacks realistic variance and temporal patterns
2. **Require live Claude Code sessions** - Slow, resource-intensive, hard to control
3. **Use random data** - Doesn't exhibit realistic usage patterns

This creates a **gap in the educational telemetry pipeline** where developers can't easily:
- Test dashboard configurations with realistic data
- Validate alerting thresholds with natural variation
- Debug query performance with time-series patterns
- Practice troubleshooting with controlled scenarios

---

## Proposed Solution: Prometheus Simulator with Brownian Motion

### Educational Objectives

1. **Provide realistic mock data** that exhibits natural variation patterns
2. **Enable controlled testing scenarios** for different usage patterns
3. **Support educational progression** from simple to complex metrics
4. **Create debugging opportunities** with intentional anomalies
5. **Demonstrate time-series analysis** with mathematically sound patterns

### Technical Approach

#### Brownian Motion for Realistic Variation

Brownian motion provides **mathematically grounded** variation that mimics real usage patterns:

```python
# Simple Brownian motion formula
next_value = current_value + random.normal(mean=drift, std=volatility)
```

**Why Brownian Motion?**
- ✅ **Natural variation**: Continuous small changes with occasional larger moves
- ✅ **Configurable drift**: Can simulate growing/declining usage trends
- ✅ **Volatility control**: Adjust how "noisy" the data appears
- ✅ **Mathematical foundation**: Well-understood, predictable properties
- ✅ **Educational value**: Connects telemetry to statistical concepts

#### Metric Simulation Patterns

| Metric Type | Brownian Motion Application | Educational Value |
|-------------|---------------------------|-------------------|
| **Token Usage** | Drift=+0.1, Volatility=50 | Learn rate calculations, capacity planning |
| **Session Duration** | Drift=0, Volatility=30s | Practice histogram analysis, percentiles |
| **Cost Tracking** | Drift=+0.001, Volatility=0.1 | Understand cumulative metrics, budgeting |
| **Tool Usage** | Poisson arrival + Brownian intensity | Model event-driven metrics |
| **Error Rates** | Low baseline + spike simulation | Practice anomaly detection, alerting |

#### Prometheus Endpoint Implementation

```yaml
endpoint: "http://localhost:9090/metrics"
format: "Prometheus exposition format"
update_frequency: "10s"
metrics_exposed:
  - otel_claude_code_token_usage_tokens_total
  - otel_claude_code_session_duration_seconds
  - otel_claude_code_cost_usd
  - otel_claude_code_tool_usage_total
  - otel_claude_code_error_total
```

---

## Implementation Components

### 1. Core Simulator Engine

**Location**: `scripts/claude-metrics-simulator.py`

**Features**:
- **Brownian motion generator** with configurable drift and volatility
- **Multiple metric type support** (counters, gauges, histograms)
- **Temporal pattern simulation** (daily/weekly cycles, trends)
- **Anomaly injection** for testing alert systems
- **Prometheus exposition format** compliance

**Configuration**:
```yaml
simulator:
  update_interval: 10  # seconds
  retention_period: 24h
  metrics:
    token_usage:
      initial_value: 1000
      drift: 0.1  # tokens/second growth
      volatility: 50  # standard deviation
      bounds: [0, 100000]
    session_duration:
      initial_value: 300  # 5 minutes
      drift: 0
      volatility: 30
      bounds: [10, 7200]  # 10s to 2h
```

### 2. Prometheus HTTP Server

**Endpoint**: `GET /metrics`
**Format**: Standard Prometheus exposition format
**Features**:
- Real-time metric generation
- Consistent label handling
- Proper timestamp management
- Health check endpoint

### 3. Makefile Integration

```makefile
# Target for easy simulation
simulate:
	@echo "Starting Claude Code metrics simulator..."
	python scripts/claude-metrics-simulator.py --config config/simulator.yaml

# Alternative using Guile (for advanced users)
simulate-guile:
	@echo "Starting Guile-based simulator..."
	guile-3.0 scripts/claude-metrics-simulator.scm

# Development mode with live reloading
simulate-dev:
	python scripts/claude-metrics-simulator.py --dev --reload
```

### 4. Educational Scenarios

#### Scenario 1: Normal Operations
```yaml
patterns:
  - name: "normal_usage"
    duration: "1h"
    token_drift: 0.05
    session_frequency: 0.1  # sessions/minute
    error_rate: 0.001
```

#### Scenario 2: High Load Testing
```yaml
patterns:
  - name: "load_test"
    duration: "30m"
    token_drift: 2.0
    session_frequency: 1.0
    error_rate: 0.01
```

#### Scenario 3: System Degradation
```yaml
patterns:
  - name: "degradation"
    duration: "45m"
    token_drift: -0.1  # declining performance
    session_frequency: 0.05
    error_rate: 0.1  # increasing errors
```

#### Scenario 4: Daily Usage Patterns
```yaml
patterns:
  - name: "daily_cycle"
    duration: "24h"
    cycles:
      - peak_hours: [9, 17]  # 9 AM to 5 PM
      - weekend_reduction: 0.3
      - night_baseline: 0.1
```

---

## Educational Use Cases

### 1. Dashboard Development
```bash
# Start simulator with realistic data
make simulate

# Open Grafana, create dashboards
# Practice with real-time updating data
# Test different visualization types
```

### 2. Alert Configuration
```bash
# Run high-error scenario
make simulate SCENARIO=degradation

# Configure alert rules in Prometheus
# Test notification channels
# Validate threshold settings
```

### 3. Query Optimization
```bash
# Generate 24h of data
make simulate DURATION=24h

# Practice PromQL queries
# Analyze performance patterns
# Learn aggregation functions
```

### 4. Anomaly Detection
```bash
# Inject controlled anomalies
make simulate SCENARIO=anomaly_detection

# Practice identifying unusual patterns
# Test detection algorithms
# Validate alert sensitivity
```

---

## Implementation Specifications

### Brownian Motion Algorithm

```python
class BrownianMotionGenerator:
    def __init__(self, initial_value, drift, volatility, bounds=None):
        self.value = initial_value
        self.drift = drift
        self.volatility = volatility
        self.bounds = bounds or (0, float('inf'))
    
    def next_value(self, dt=1.0):
        # Standard Brownian motion with drift
        random_shock = np.random.normal(0, self.volatility * np.sqrt(dt))
        drift_component = self.drift * dt
        
        self.value += drift_component + random_shock
        
        # Apply bounds if specified
        self.value = max(self.bounds[0], min(self.bounds[1], self.value))
        
        return self.value
```

### Prometheus Exposition Format

```prometheus
# HELP otel_claude_code_token_usage_tokens_total Total tokens used (simulated)
# TYPE otel_claude_code_token_usage_tokens_total counter
otel_claude_code_token_usage_tokens_total{model="claude-3-sonnet",token_type="input"} 15420 1640995200000
otel_claude_code_token_usage_tokens_total{model="claude-3-sonnet",token_type="output"} 8945 1640995200000

# HELP otel_claude_code_session_duration_seconds Session duration (simulated)
# TYPE otel_claude_code_session_duration_seconds histogram
otel_claude_code_session_duration_seconds_bucket{le="60"} 145
otel_claude_code_session_duration_seconds_bucket{le="300"} 832
otel_claude_code_session_duration_seconds_bucket{le="600"} 1240
otel_claude_code_session_duration_seconds_bucket{le="+Inf"} 1456
otel_claude_code_session_duration_seconds_sum 425600
otel_claude_code_session_duration_seconds_count 1456
```

### HTTP Server Specification

```yaml
server:
  host: "localhost"
  port: 9090
  endpoints:
    - path: "/metrics"
      method: "GET"
      content_type: "text/plain; version=0.0.4; charset=utf-8"
    - path: "/health"
      method: "GET"
      response: {"status": "healthy", "uptime": "3h45m"}
    - path: "/config"
      method: "GET"
      response: "Current simulator configuration"
```

---

## Success Metrics

### Technical Deliverables
- [ ] **Python simulator script** with Brownian motion implementation
- [ ] **Prometheus HTTP endpoint** serving realistic mock data
- [ ] **Makefile targets** for easy simulation control
- [ ] **Configuration system** for different scenarios
- [ ] **Educational documentation** explaining statistical concepts

### Educational Outcomes
- [ ] Developers understand **time-series variation patterns**
- [ ] Teams can **test dashboard configurations** with realistic data
- [ ] Alert thresholds can be **validated before production**
- [ ] Query performance can be **optimized with controlled data**
- [ ] Statistical concepts are **connected to operational metrics**

### Integration Success
- [ ] Simulator integrates with existing **logging proxy system**
- [ ] Data appears correctly in **Grafana dashboards**
- [ ] **Prometheus queries** work seamlessly with simulated data
- [ ] **Educational scenarios** provide meaningful learning experiences

---

## Implementation Phases

### Phase 1: Core Simulator ⏳
- [x] Research Brownian motion implementation approaches
- [ ] Implement basic simulator with single metric type
- [ ] Add Prometheus exposition format support
- [ ] Create simple HTTP server
- [ ] Test with Prometheus scraping

### Phase 2: Multi-Metric Support
- [ ] Extend to all Claude Code metric types
- [ ] Implement proper label handling
- [ ] Add histogram and counter support
- [ ] Create configuration system
- [ ] Add bounds checking and validation

### Phase 3: Educational Scenarios  
- [ ] Design realistic usage patterns
- [ ] Implement temporal cycles (daily/weekly)
- [ ] Add anomaly injection capabilities
- [ ] Create pre-configured scenarios
- [ ] Document educational use cases

### Phase 4: Integration & Polish
- [ ] Integrate with existing telemetry system
- [ ] Add Makefile targets
- [ ] Create comprehensive documentation
- [ ] Test with real Grafana dashboards
- [ ] Optimize performance and resource usage

---

## Alternative Implementations

### Guile Scheme Version
For users preferring functional programming approaches:

```scheme
#!/usr/bin/env guile-3.0
;;; Claude Code Metrics Simulator in Guile Scheme

(use-modules (web server)
             (web request)
             (web response)
             (srfi srfi-19)  ; Date/time
             (srfi srfi-26)) ; Cut

(define (brownian-motion initial drift volatility)
  "Generate next value using Brownian motion"
  (+ initial 
     (* drift 1.0)
     (* volatility (random:normal))))
```

**Makefile target**: `make simulate-guile`

### Docker Container Version
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY scripts/claude-metrics-simulator.py .
COPY config/simulator.yaml .
EXPOSE 9090
CMD ["python", "claude-metrics-simulator.py"]
```

**Makefile target**: `make simulate-docker`

---

## Related Issues & Dependencies

- **Logging Proxy Integration**: Simulator should work with existing `src/logging_proxy.py`
- **Test Matrix Enhancement**: Add simulator testing to `test_matrix.py`
- **Dashboard Templates**: Update Grafana dashboards to work with simulated data
- **Documentation Updates**: Integrate simulator into educational curriculum

---

## Call to Action

This simulator bridges the gap between **theoretical telemetry understanding** and **practical implementation experience**. By providing mathematically sound mock data, developers can:

1. **Learn faster** - No need to wait for real usage data
2. **Test thoroughly** - Validate configurations before production
3. **Understand patterns** - See how different scenarios affect metrics
4. **Practice debugging** - Work with controlled anomalies

**Ready to contribute?**
1. Review the Brownian motion algorithm
2. Suggest additional educational scenarios
3. Test with your favorite dashboard tools
4. Document learning insights and best practices

Every improvement makes the educational experience better for everyone! 🎯📊