# MQTT Antena Mobile - Automation Makefile
# All commands are strictly executed within the Python 3.11.14 virtual environment (.venv)

PYTHON_VERSION := 3.11.14
PYENV_PYTHON   := $(shell pyenv prefix $(PYTHON_VERSION) 2>/dev/null)/bin/python
PYTHON         := $(if $(wildcard $(PYENV_PYTHON)),$(PYENV_PYTHON),python3)
VENV           := .venv
VENV_BIN       := $(VENV)/bin

.PHONY: help setup run dev test build-apk clean

help:
	@echo "======================================================"
	@echo "📡 MQTT Antena Mobile - Development Commands"
	@echo "======================================================"
	@echo "  make setup      - Create .venv (Python $(PYTHON_VERSION)) and install dependencies"
	@echo "  make run        - Run application locally in desktop window"
	@echo "  make dev        - Run application with hot-reloading enabled"
	@echo "  make test       - Run automated test suite with pytest"
	@echo "  make build-apk  - Build release Android APK using Flet"
	@echo "  make clean      - Clean cache, build artifacts, and test caches"
	@echo "======================================================"

setup:
	@echo "Checking Python $(PYTHON_VERSION)..."
	@if [ ! -d "$(VENV)" ]; then \
		echo "Creating virtual environment at $(VENV)..."; \
		$(PYTHON) -m venv $(VENV); \
	fi
	$(VENV_BIN)/pip install --upgrade pip
	$(VENV_BIN)/pip install "flet==1.0.4" "paho-mqtt>=2.0.0" "pytest" "pytest-asyncio"
	@echo "Setup complete. Virtual environment ready at $(VENV)."

run:
	$(VENV_BIN)/flet run src/main.py

dev:
	$(VENV_BIN)/flet run -d src/main.py

test:
	$(VENV_BIN)/pytest tests/ -v

build-apk:
	@echo "Building Android APK with Flet..."
	$(VENV_BIN)/flet build apk --project-name "mqtt_antena_mobile" --product-name "MQTT Antena"

clean:
	rm -rf build/ dist/ __pycache__ .pytest_cache .flet
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
