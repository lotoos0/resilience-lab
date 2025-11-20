HELP_WIDTH ?= 26
NO_COLOR   ?= 0
SEP_CHAR   ?= =

# ANSI (wyłączalne)
ifeq ($(NO_COLOR),0)
  CYAN := \033[36m
  DIM  := \033[2m
  RST  := \033[0m
else
  CYAN :=
  DIM  :=
  RST  :=
endif

# --- AWK program as a Make variable (no quoting hell) ---
define AWK_HELP
BEGIN { FS=":.*?## " }
{
  tgt=$$1; desc=$$2; grp="";
  if (desc ~ /^\[/) {
    g=desc; sub(/^\[/,"",g); sub(/\].*$$/,"",g); grp=g;
    sub(/^\[[^]]+\][[:space:]]*/,"",desc);
  }
  key=(grp==""?"_misc":grp);
  bucket[key]=bucket[key] tgt "\037" desc "\n";
}
END {
  print SEP;
  n=asorti(bucket, ks);
  for (i=1; i<=n; i++) {
    k=ks[i];
    if (k!="_misc") printf(" %s%s%s\n", DIM, k, RST);
    m=split(bucket[k], rows, "\n");
    for (j=1; j<=m; j++) {
      if (rows[j]=="") continue;
      split(rows[j], p, "\037");
      printf("  %s%-*s%s %s\n", CYAN, W, p[1], RST, p[2]);
    }
    print SEP;
  }
}
endef
export AWK_HELP

.PHONY: run down logs logs-api logs-payments clean ps restart 

help: ## [Help] Show help for targets (grouped)
	@C=$$(tput cols 2>/dev/null || echo 100); \
	W=$(HELP_WIDTH); \
	SEP=$$(printf '%*s' $$C | tr ' ' '$(SEP_CHAR)'); \
	grep -E '^[a-zA-Z0-9_-]+:.*?## ' $(MAKEFILE_LIST) \
	| sort \
	| awk -v C=$$C -v W=$$W -v CYAN='$(CYAN)' -v DIM='$(DIM)' -v RST='$(RST)' -v SEP="$$SEP" "$$AWK_HELP"

install: ## [Setup] Install dev dependencies in venv (lightweight)
	@if [ ! -d "venv" ]; then \
		echo "Creating virtual environment..."; \
		python -m venv venv; \
	fi
	@echo "Installing dev dependencies in venv..."
	./venv/bin/pip install -r requirements-dev.txt
	@echo ""
	@echo "✅ Done! Activate venv with: source venv/bin/activate"
	@echo "Or use: make test (will use venv automatically)"

install-full: ## [Setup] Install ALL dependencies in venv (requires: postgresql-libs)
	@if [ ! -d "venv" ]; then \
		echo "Creating virtual environment..."; \
		python -m venv venv; \
	fi
	@echo "Installing full dependencies in venv..."
	./venv/bin/pip install -r requirements.txt
	@echo ""
	@echo "✅ Done!"

dev: ## [DEV] Run local services
	docker-compose up -d

build: ## [Build] Build docker images
	docker build -t api:dev -f services/api/Dockerfile .
	docker build -t payments:dev -f services/payments/Dockerfile .

test: ## [Test] Run unit tests (no services required)
	@if [ -d "venv" ]; then \
		./venv/bin/pytest -v -m "not integration"; \
	elif command -v pytest >/dev/null 2>&1; then \
		pytest -v -m "not integration"; \
	else \
		echo "❌ Error: pytest not found. Run: make install"; \
		exit 1; \
	fi

test-all: ## [Test] Run ALL tests including integration (requires: make dev)
	@echo "⚠️  Integration tests require services. Checking if services are running..."
	@if ! curl -s -f http://localhost:8000/healthz > /dev/null 2>&1 || \
	    ! curl -s -f http://localhost:8001/healthz > /dev/null 2>&1; then \
		echo "❌ Error: Services not running. Start with: make dev"; \
		echo "   Then wait ~30s for services to be healthy before running tests."; \
		exit 1; \
	fi
	@echo "✅ Services are running. Running all tests..."
	@if [ -d "venv" ]; then \
		./venv/bin/pytest -v; \
	elif command -v pytest >/dev/null 2>&1; then \
		pytest -v; \
	else \
		echo "❌ Error: pytest not found. Run: make install"; \
		exit 1; \
	fi

test-unit: ## [Test] Run unit tests only (same as 'make test')
	@if [ -d "venv" ]; then \
		./venv/bin/pytest -v -m "not integration"; \
	elif command -v pytest >/dev/null 2>&1; then \
		pytest -v -m "not integration"; \
	else \
		echo "❌ Error: pytest not found. Run: make install"; \
		exit 1; \
	fi

test-integration: ## [Test] Run integration tests only (requires: make dev)
	@echo "⚠️  Integration tests require services. Checking if services are running..."
	@if ! curl -s -f http://localhost:8000/healthz > /dev/null 2>&1 || \
	    ! curl -s -f http://localhost:8001/healthz > /dev/null 2>&1; then \
		echo "❌ Error: Services not running. Start with: make dev"; \
		echo "   Then wait ~30s for services to be healthy before running tests."; \
		exit 1; \
	fi
	@echo "✅ Services are running. Running integration tests..."
	@if [ -d "venv" ]; then \
		./venv/bin/pytest -v -m integration; \
	elif command -v pytest >/dev/null 2>&1; then \
		pytest -v -m integration; \
	else \
		echo "❌ Error: pytest not found. Run: make install"; \
		exit 1; \
	fi

test-docker: ## [Test] Run pytest in Docker container
	docker run --rm -v $(PWD):/app -w /app python:3.11-slim sh -c "pip install -q -r requirements.txt && pytest -v"

lint: ## [Test] Run code linters (uses venv if available)
	@if [ -d "venv" ]; then \
		./venv/bin/ruff check services/; \
	elif command -v ruff >/dev/null 2>&1; then \
		ruff check services/; \
	else \
		echo "❌ Error: ruff not found. Run: make install"; \
		exit 1; \
	fi

run: dev ## [DEV] Alias for 'dev' - start all services

down: ## [DEV] Stop all services
	docker-compose down 

logs: ## [OPS] Show logs from all services
	docker-compose logs -f

logs-api: ## [OPS] Show logs from API service only
	docker-compose logs -f api

logs-payments: ## [OPS] Show logs from Payments service only
	docer-compose logs -f payments 

clean: ## [OPS] Clean up Docker images, containers, volumes
	docker-compose down -v --remove-orphans
	docker system prune -f

clean-venv: ## [Setup] Remove virtual environment
	rm -rf venv
	@echo "✅ Virtual environment removed"

ps: ## [DEV] Show status of all services
	docker-compose ps 

restart: down dev ## [DEV] Restart all services
