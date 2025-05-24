.PHONY: tangle install clean analyze lint simulate simulate-guile simulate-dev test-simulator

# Tangle all org files to extract source code
tangle:
	emacs --batch --eval "(require 'org)" --eval "(find-file \"SETUP.org\")" --eval "(org-babel-tangle)" --kill

# Install Python dependencies
install:
	pip3 install -r requirements.txt

# Run all analysis scripts
analyze:
	uv run python src/project_metrics.py
	uv run python src/cost_analyzer.py
	uv run python src/session_analyzer.py

# Clean generated files
clean:
	rm -f exports/*.json exports/*.csv exports/*.png
	find . -name "__pycache__" -type d -exec rm -rf {} +
	find . -name "*.pyc" -delete

# Lint Python code
lint:
	@which ruff > /dev/null 2>&1 && ruff check src/ || echo "ruff not installed, skipping lint"
	@which black > /dev/null 2>&1 && black --check src/ || echo "black not installed, skipping format check"

# Format Python code
format:
	@which black > /dev/null 2>&1 && black src/ || echo "black not installed, skipping format"

# Generate dashboard templates
dashboards:
	uv run python scripts/generate_dashboards.py

# Generate dashboards for specific environment
dashboards-dev:
	uv run python scripts/generate_dashboards.py --environment development

dashboards-prod:
	uv run python scripts/generate_dashboards.py --environment production

# Simulate Claude Code metrics using Brownian motion
simulate:
	@echo "Starting Claude Code metrics simulator..."
	@echo "Prometheus endpoint: http://localhost:9090/metrics"
	@echo "Health check: http://localhost:9090/health"
	@echo "Press Ctrl+C to stop"
	uv run python scripts/claude-metrics-simulator.py --scenario normal

# Simulate with specific scenario
simulate-scenario:
	@echo "Starting simulator with scenario: $(SCENARIO)"
	uv run python scripts/claude-metrics-simulator.py --scenario $(SCENARIO)

# Simulate using Guile Scheme (for advanced users)
simulate-guile:
	@echo "Starting Guile-based simulator..."
	@if command -v guile-3.0 >/dev/null 2>&1; then \
		guile-3.0 scripts/claude-metrics-simulator.scm; \
	else \
		echo "Error: guile-3.0 not found. Install with: sudo apt-get install guile-3.0"; \
		echo "Falling back to Python simulator..."; \
		$(MAKE) simulate; \
	fi

# Development mode with custom port and live reloading
simulate-dev:
	@echo "Starting simulator in development mode..."
	uv run python scripts/claude-metrics-simulator.py --dev --port 9091 --scenario high_load

# Test simulator functionality
test-simulator:
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

# Help
help:
	@echo "Available targets:"
	@echo "  tangle      - Extract source files from SETUP.org"
	@echo "  install     - Install Python dependencies"
	@echo "  analyze     - Run all analysis scripts"
	@echo "  dashboards  - Generate Grafana dashboards from templates"
	@echo "  dashboards-dev  - Generate dashboards for development environment"
	@echo "  dashboards-prod - Generate dashboards for production environment"
	@echo "  simulate    - Start Claude Code metrics simulator (Brownian motion)"
	@echo "  simulate-scenario SCENARIO=name - Start simulator with specific scenario"
	@echo "  simulate-guile - Start Guile-based simulator (fallback to Python)"
	@echo "  simulate-dev - Start simulator in development mode"
	@echo "  test-simulator - Test simulator functionality"
	@echo "  clean       - Remove generated files"
	@echo "  lint        - Check code style"
	@echo "  format      - Format code"
	@echo "  help        - Show this help"
