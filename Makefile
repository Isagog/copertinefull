# ──────────────────────────────────────────────
# Copertine — local development targets
# ──────────────────────────────────────────────
#
# Production is NOT here any more. Copertine is a Dokploy Compose app on mema4,
# deployed from Isagog/isagog-platform-dokploy (`copertine/docker-compose.yml`)
# out of images this repo's CI pushes to GHCR. The old prod-* targets drove a
# root docker-compose.yml that has been deleted; "deploying" now means merging
# to main (CI builds) and hitting Redeploy in Dokploy.
#
# Usage:
#   make local-up       Start local dev (DB tunnel + next dev)
#   make local-down     Stop local dev
#   make local-restart  Restart local dev
#   make images         Build the three container images locally (sanity check)
#
# ──────────────────────────────────────────────
# Why the tunnel takes two hops
# ──────────────────────────────────────────────
# On mema3 Postgres was a plain container with 5432 on the host, so a single
# `ssh -L` reached it. On mema4 it is a Dokploy MANAGED database that publishes
# NO host port at all — it is reachable only by name on the `dokploy-network`
# overlay, and the host's own network namespace is not attached to that overlay.
#
# So `local-tunnel-up` starts a throwaway socat container that IS on the overlay
# and republishes the port on the host's loopback, then forwards that. Both ends
# are torn down by `local-tunnel-down`; nothing persists on mema4.
# ──────────────────────────────────────────────

SHELL        := /bin/bash
FRONTEND     := frontend

SSH_HOST     := mema@mema4.ilmanifesto.it
SSH_PID      := /tmp/copertine-ssh-tunnel.pid

# Local port for `psql`/`next dev`; set DATABASE_URL to point at it.
TUNNEL_PORT  := 5432
# Host-side loopback port on mema4 that the bridge publishes. Deliberately not
# 5432: that would collide with anything else the host later binds there.
BRIDGE_PORT  := 15432
BRIDGE_NAME  := copertine-pgbridge
PG_SERVICE   := mema-psqlvect-618e9h

.PHONY: local-up local-down local-restart local-log \
        local-tunnel-up local-tunnel-down local-tunnel-status images

# ──────────────────────────────────────────────
# Local development
# ──────────────────────────────────────────────

local-tunnel-up:
	@if [ -f $(SSH_PID) ] && kill -0 $$(cat $(SSH_PID)) 2>/dev/null; then \
		echo "SSH tunnel already running (pid $$(cat $(SSH_PID)))"; \
	else \
		echo "Starting socat bridge on $(SSH_HOST) ($(PG_SERVICE) -> 127.0.0.1:$(BRIDGE_PORT))..."; \
		ssh $(SSH_HOST) "docker rm -f $(BRIDGE_NAME) >/dev/null 2>&1; \
			docker run -d --name $(BRIDGE_NAME) --network dokploy-network \
				-p 127.0.0.1:$(BRIDGE_PORT):5432 alpine/socat:latest \
				tcp-listen:5432,fork,reuseaddr tcp-connect:$(PG_SERVICE):5432" >/dev/null; \
		echo "Opening SSH tunnel localhost:$(TUNNEL_PORT) -> $(BRIDGE_PORT)..."; \
		ssh -f -N -L $(TUNNEL_PORT):localhost:$(BRIDGE_PORT) $(SSH_HOST) \
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
	@echo "Removing socat bridge on $(SSH_HOST)..."
	@ssh $(SSH_HOST) "docker rm -f $(BRIDGE_NAME) >/dev/null 2>&1 || true"

local-tunnel-status:
	@if [ -f $(SSH_PID) ] && kill -0 $$(cat $(SSH_PID)) 2>/dev/null; then \
		echo "Tunnel running (pid $$(cat $(SSH_PID)))"; \
	else \
		rm -f $(SSH_PID); \
		echo "Tunnel not running"; \
	fi
	@ssh $(SSH_HOST) "docker ps --filter name=$(BRIDGE_NAME) --format 'bridge: {{.Status}}'" || true

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
# Images — the same three CI builds, run locally
# ──────────────────────────────────────────────
# A pre-push sanity check only. What actually deploys is always the CI-built
# image from GHCR; nothing built here is ever pushed.

images:
	docker build -t copertine-frontend:local ./frontend
	docker build -t copertine-scraper:local  ./backend
	docker build -t copertine-images:local   ./nginx
	@echo "Built copertine-{frontend,scraper,images}:local"
