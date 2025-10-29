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

help: ## [Help] Show help for targets (grouped)
	@C=$$(tput cols 2>/dev/null || echo 100); \
	W=$(HELP_WIDTH); \
	SEP=$$(printf '%*s' $$C | tr ' ' '$(SEP_CHAR)'); \
	grep -E '^[a-zA-Z0-9_-]+:.*?## ' $(MAKEFILE_LIST) \
	| sort \
	| awk -v C=$$C -v W=$$W -v CYAN='$(CYAN)' -v DIM='$(DIM)' -v RST='$(RST)' -v SEP="$$SEP" "$$AWK_HELP"

dev: ## [DEV] Run local services
	docker-compose up -d

build: ## [Build] Build docker images
	docker build -t api:dev services/api
	docker build -t payments:dev services/payments

test: ## [Test] Run pytest
	pytest -v

lint: ## [Test] Run code linters
	ruff check services/
