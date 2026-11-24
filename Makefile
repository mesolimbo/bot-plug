PYTHON ?= python
SERVER := $(PYTHON) -I tools/server.py

.DEFAULT_GOAL := help
.PHONY: help start stop restart status

help: ## Show this help
	@echo "Alan's Bot Plugs: the game is served from game/ at http://127.0.0.1:8807/"
	@echo ""
	@echo "  make start     Start the local server (does nothing if it is already running)"
	@echo "  make stop      Stop the server"
	@echo "  make restart   Stop, then start the server"
	@echo "  make status    Say whether the server is running"

start: ## Start the local server
	@$(SERVER) start

stop: ## Stop the server
	@$(SERVER) stop

restart: stop start ## Stop, then start the server

status: ## Say whether the server is running
	@$(SERVER) status
