# ──────────────────────────────────────────────
# Copertine — Local & Production Targets
# ──────────────────────────────────────────────
#
# local-*  : Next.js dev server + SSH tunnel to mema3 PostgreSQL
# prod-*   : Docker Compose (full production stack)
#
# Usage:
#   make local-up       Start local dev (tunnel + next dev)
#   make local-down     Stop local dev
#   make local-restart  Restart local dev
#   make local-log      Tail Next.js dev output
#
#   make prod-up        Start production containers
#   make prod-down      Stop production containers
#   make prod-restart   Restart production containers
#   make prod-build     Force rebuild all images and start containers
#   make prod-log       Tail production container logs
# ──────────────────────────────────────────────

SHELL       := /bin/bash
FRONTEND    := frontend
SSH_HOST    := mema3
SSH_PID     := /tmp/copertine-ssh-tunnel.pid
TUNNEL_PORT := 5432

# ──────────────────────────────────────────────
# Local development
# ──────────────────────────────────────────────

.PHONY: local-up local-down local-restart local-log local-tunnel-up local-tunnel-down local-tunnel-status

local-tunnel-up:
	@if [ -f $(SSH_PID) ] && kill -0 $$(cat $(SSH_PID)) 2>/dev/null; then \
		echo "SSH tunnel already running (pid $$(cat $(SSH_PID)))"; \
	else \
		echo "Opening SSH tunnel to $(SSH_HOST):$(TUNNEL_PORT)..."; \
		ssh -f -N -L $(TUNNEL_PORT):localhost:$(TUNNEL_PORT) $(SSH_HOST) \
			-o ExitOnForwardFailure=yes \
			-o ServerAliveInterval=60 \
			-o ServerAliveCountMax=3; \
		lsof -ti :$(TUNNEL_PORT) -sTCP:LISTEN | head -1 > $(SSH_PID); \
		echo "Tunnel up (pid $$(cat $(SSH_PID)))"; \
	fi

local-tunnel-down:
	@if [ -f $(SSH_PID) ] && kill -0 $$(cat $(SSH_PID)) 2>/dev/null; then \
		kill $$(cat $(SSH_PID)) && rm -f $(SSH_PID); \
		echo "SSH tunnel stopped"; \
	else \
		rm -f $(SSH_PID); \
		echo "No tunnel running"; \
	fi

local-tunnel-status:
	@if [ -f $(SSH_PID) ] && kill -0 $$(cat $(SSH_PID)) 2>/dev/null; then \
		echo "Tunnel running (pid $$(cat $(SSH_PID)))"; \
	else \
		rm -f $(SSH_PID); \
		echo "Tunnel not running"; \
	fi

local-up: local-tunnel-up
	@echo "Starting Next.js dev server..."
	cd $(FRONTEND) && pnpm dev

local-down: local-tunnel-down
	@echo "Local environment stopped"

local-restart: local-down local-up

local-log:
	@echo "In local mode, logs appear in the terminal running 'make local-up'."
	@echo "Use 'make local-tunnel-status' to check the SSH tunnel."

# ──────────────────────────────────────────────
# Production (Docker Compose)
# ──────────────────────────────────────────────

.PHONY: prod-up prod-down prod-restart prod-log prod-build

prod-up:
	docker compose up -d

prod-down:
	docker compose down

prod-restart:
	docker compose down
	docker compose up -d

prod-build:
	docker compose build --no-cache
	docker compose up -d

prod-log:
	docker compose logs -f --tail=100
