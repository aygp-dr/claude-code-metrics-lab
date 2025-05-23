.PHONY: tangle install clean analyze lint

# Tangle all org files to extract source code
tangle:
	emacs --batch --eval "(require 'org)" --eval "(find-file \"SETUP.org\")" --eval "(org-babel-tangle)" --kill

# Install Python dependencies
install:
	pip3 install -r requirements.txt

# Run all analysis scripts
analyze:
	python3 src/project_metrics.py
	python3 src/cost_analyzer.py
	python3 src/session_analyzer.py

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

# Help
help:
	@echo "Available targets:"
	@echo "  tangle      - Extract source files from SETUP.org"
	@echo "  install     - Install Python dependencies"
	@echo "  analyze     - Run all analysis scripts"
	@echo "  dashboards  - Generate Grafana dashboards from templates"
	@echo "  dashboards-dev  - Generate dashboards for development environment"
	@echo "  dashboards-prod - Generate dashboards for production environment"
	@echo "  clean       - Remove generated files"
	@echo "  lint        - Check code style"
	@echo "  format      - Format code"
	@echo "  help        - Show this help"
