#+TITLE: Claude Code Metrics Lab - Project Configuration
#+AUTHOR: aygp-dr
#+DATE: 2025-05-23
#+PROPERTY: header-args :mkdirp yes

* Project Overview

A dedicated lab for tracking, analyzing, and visualizing Claude Code usage metrics using OpenTelemetry. This project focuses on understanding usage patterns, cost analysis, and efficiency metrics for Claude Code sessions.

* Development Workflow

** Git Commit Standards

- Use conventional commit format: =<type>(<scope>): <description>=
- Always use =--no-gpg-sign= for commits
- Use =--trailer= for Co-Authored-By, never put "Generated with" in commit body
- Types: feat, fix, docs, style, refactor, test, chore

** Code Organization

- Python scripts in =src/= for analysis
- Grafana dashboards in =dashboards/=
- Prometheus queries in =queries/=
- Documentation in =docs/=
- Export artifacts in =exports/=

** Literate Programming

- Primary configuration in =SETUP.org=
- Use =make tangle= to extract all source files
- Enable Babel execution with =:mkdirp yes=
- Mermaid diagrams for system modeling

* Dependencies

- Python 3.8+ with pandas, matplotlib, requests
- OpenTelemetry infrastructure (Prometheus + Grafana)
- Emacs with org-mode for tangling
- Claude Code with telemetry enabled

* Local Configuration Notes

- Prometheus endpoint: http://localhost:9090
- Grafana endpoint: http://pi.lan:3000
- OTEL metrics prefix: =otel_claude_code_=
- Export directory: =exports/= (gitignored)

* Usage Commands

** Basic Operations
#+begin_src bash
# Extract source from org files
make tangle

# Install dependencies
make install

# Clean generated files
make clean
#+end_src

** Code Quality
#+begin_src bash
# Check code style
make lint

# Format code
make format
#+end_src

** Analysis and Dashboards
#+begin_src bash
# Run all analysis scripts
make analyze

# Generate Grafana dashboards
make dashboards
make dashboards-dev
make dashboards-prod
#+end_src

** Metrics Simulation
#+begin_src bash
# Start metrics simulator
make simulate

# Simulator with scenarios
make simulate-scenario SCENARIO=normal
make simulate-dev
make simulate-guile

# Test simulator
make test-simulator
#+end_src

** Help
#+begin_src bash
# Show all available commands
make help
#+end_src
