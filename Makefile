# Default target
.DEFAULT_GOAL := help

# Phony targets
.PHONY: help install clean analyze lint format dashboards dashboards-dev dashboards-prod \
        simulate simulate-scenario simulate-guile simulate-dev test-simulator \
        otlp-debug-sink otlp-interceptor otlp-interceptor-verbose \
        tcs-report tcs-badges tcs

help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install Python dependencies
	pip3 install -r requirements.txt

analyze: ## Run all analysis scripts
	uv run python src/project_metrics.py
	uv run python src/cost_analyzer.py
	uv run python src/session_analyzer.py

clean: ## Remove generated files and caches
	rm -f exports/*.json exports/*.csv exports/*.png
	find . -name "__pycache__" -type d -exec rm -rf {} +
	find . -name "*.pyc" -delete

lint: ## Check code style with ruff
	@which ruff > /dev/null 2>&1 && ruff check src/ || echo "ruff not installed, skipping lint"
	@which black > /dev/null 2>&1 && black --check src/ || echo "black not installed, skipping format check"

format: ## Format code with black
	@which black > /dev/null 2>&1 && black src/ || echo "black not installed, skipping format"

dashboards: ## Generate Grafana dashboards from templates
	uv run python scripts/generate_dashboards.py

dashboards-dev: ## Generate dashboards for development environment
	uv run python scripts/generate_dashboards.py --environment development

dashboards-prod: ## Generate dashboards for production environment
	uv run python scripts/generate_dashboards.py --environment production

simulate: ## Start Claude Code metrics simulator (Brownian motion)
	@echo "Starting Claude Code metrics simulator..."
	@echo "Prometheus endpoint: http://localhost:9090/metrics"
	@echo "Health check: http://localhost:9090/health"
	@echo "Press Ctrl+C to stop"
	uv run python scripts/claude-metrics-simulator.py --scenario normal

simulate-scenario: ## Start simulator with specific scenario (use SCENARIO=name)
	@echo "Starting simulator with scenario: $(SCENARIO)"
	uv run python scripts/claude-metrics-simulator.py --scenario $(SCENARIO)

simulate-guile: ## Start Guile-based simulator (fallback to Python)
	@echo "Starting Guile-based simulator..."
	@if command -v guile-3.0 >/dev/null 2>&1; then \
		guile-3.0 scripts/claude-metrics-simulator.scm; \
	else \
		echo "Error: guile-3.0 not found. Install with: sudo apt-get install guile-3.0"; \
		echo "Falling back to Python simulator..."; \
		$(MAKE) simulate; \
	fi

simulate-dev: ## Start simulator in development mode (port 9091)
	@echo "Starting simulator in development mode..."
	uv run python scripts/claude-metrics-simulator.py --dev --port 9091 --scenario high_load

test-simulator: ## Test simulator functionality
	@echo "Testing simulator functionality..."
	uv run python scripts/claude-metrics-simulator.py --duration 30 --scenario normal --port 9092 &
	@sleep 5
	@echo "Testing metrics endpoint..."
	@curl -s http://localhost:9092/metrics | head -10 || echo "Metrics endpoint test failed"
	@echo "Testing health endpoint..."
	@curl -s http://localhost:9092/health | uv run python -m json.tool || echo "Health endpoint test failed"
	@echo "Waiting for simulator to complete..."
	@wait
	@echo "Simulator test completed"

otlp-debug-sink: ## Capture raw OTLP HTTP requests without forwarding
	@echo "Starting OTLP debug sink on port 14318..."
	@echo "This captures raw OTLP HTTP requests for debugging"
	@echo "Configure Claude Code with:"
	@echo "  export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:14318"
	@echo "  export OTEL_METRICS_EXPORTER=otlp"
	@echo ""
	@echo "Press Ctrl+C to stop"
	@echo "Logging to: otlp-debug-sink-$$(date +%Y%m%d-%H%M%S).log"
	@nc -l 14318 | tee "otlp-debug-sink-$$(date +%Y%m%d-%H%M%S).log"

otlp-interceptor: ## Capture AND forward OTLP HTTP requests to pi.lan
	@echo "Starting OTLP interceptor on port 14318..."
	@echo "This captures raw OTLP HTTP requests AND forwards to pi.lan:4318"
	@echo "Configure Claude Code with:"
	@echo "  export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:14318"
	@echo "  export OTEL_METRICS_EXPORTER=otlp"
	@echo ""
	@echo "Press Ctrl+C to stop"
	@echo "Logging to: otlp-interceptor-$$(date +%Y%m%d-%H%M%S).log"
	@nc -l 14318 | tee "otlp-interceptor-$$(date +%Y%m%d-%H%M%S).log" | nc pi.lan 4318

otlp-interceptor-verbose: ## OTLP interceptor with real-time analysis
	@echo "Starting OTLP interceptor with analysis on port 14318..."
	@echo "Forwarding to: pi.lan:4318"
	@echo "Logging to: otlp-interceptor-$$(date +%Y%m%d-%H%M%S).log"
	@nc -l 14318 | tee "otlp-interceptor-$$(date +%Y%m%d-%H%M%S).log" | tee >(grep -E "(POST|service\.name|tokens)" >&2) | nc pi.lan 4318

tcs-report: ## Generate TCS (Trailer Consistency Score) report
	@echo "Generating TCS report..."
	@bash scripts/tcs-report-generator.sh
	@echo "Report generated at: reports/tcs_report.md"

tcs-badges: tcs-report ## Generate TCS badges from report data
	@echo "Generating TCS badges..."
	@uv run python scripts/generate_tcs_badges.py

tcs: tcs-badges ## Run full TCS analysis (report + badges)
	@echo "TCS analysis complete!"
	@echo "View report: reports/tcs_report.md"
	@echo "Badges created: static/badges/"