# satoshi-pgp-audit
#
# Two ways to run the lab:
#   make docker-*   reproducible container build (needs Docker + registry access)
#   make native-*   build GnuPG 1.4.7 on this host (needs a C toolchain + autotools)

SHELL     := /bin/bash
ROOT      := $(shell pwd)
PY        := python3
PYTHONPATH:= $(ROOT)/src
export PYTHONPATH

GNUPG_REPO   := https://github.com/gpg/gnupg.git
GNUPG_TAG    := gnupg-1.4.7
GNUPG_COMMIT := 7cb81bb3ef2769812678719d440aa844c0bb889a
GNUPG_TREE   := c9cb62c8dcee5935c4ad86b190d171beec5035d0
SRC_DIR      := $(ROOT)/data/gnupg-src/gnupg
SRC_DIR_1421 := $(ROOT)/data/gnupg-src/gnupg-1.4.21
GPG147       := $(SRC_DIR)/g10/gpg

HIST_CFLAGS := -O2 -w -std=gnu89 -fcommon -Wno-implicit-function-declaration \
               -Wno-int-conversion -Wno-incompatible-pointer-types

.PHONY: help
help:
	@echo "Targets:"
	@echo "  make setup            fetch and verify pinned GnuPG source"
	@echo "  make native-gnupg147  build the historical gpg binary on this host"
	@echo "  make analyze          Part 1 - parse and analyse the public key"
	@echo "  make cve              reproduce CVE-2016-6313"
	@echo "  make differential     Python pool model vs real GnuPG C code"
	@echo "  make synth            Part 2 - synthetic keys with real GnuPG 1.4.7"
	@echo "  make rngstats         statistical battery over pool output"
	@echo "  make report           produce the five-category audit report"
	@echo "  make test             run the test suite"
	@echo "  make all              setup + build + full pipeline + report"
	@echo "  make docker-build     build both container images"
	@echo "  make docker-report    run the report inside the container"

# ---------------------------------------------------------------- source
.PHONY: setup
setup: $(SRC_DIR) $(SRC_DIR_1421)

$(SRC_DIR):
	@mkdir -p $(dir $(SRC_DIR))
	git clone --filter=blob:none --no-checkout $(GNUPG_REPO) $(SRC_DIR)
	cd $(SRC_DIR) && git checkout -q $(GNUPG_TAG)
	@cd $(SRC_DIR) && \
	  test "$$(git rev-parse HEAD)" = "$(GNUPG_COMMIT)" || { echo "COMMIT MISMATCH"; exit 1; } && \
	  test "$$(git rev-parse HEAD^{tree})" = "$(GNUPG_TREE)" || { echo "TREE MISMATCH"; exit 1; } && \
	  echo "provenance verified: $(GNUPG_TAG) @ $(GNUPG_COMMIT)"

$(SRC_DIR_1421): $(SRC_DIR)
	cd $(SRC_DIR) && git worktree add -f $(SRC_DIR_1421) gnupg-1.4.21

# ---------------------------------------------------------------- native build
.PHONY: native-gnupg147
native-gnupg147: $(GPG147)

$(GPG147): $(SRC_DIR)
	cd $(SRC_DIR) && ./autogen.sh
	cd $(SRC_DIR) && ./configure --disable-nls --disable-card-support \
	    --disable-gnupg-iconv --without-readline --disable-asm
	@# The texinfo manual does not build against modern makeinfo; g10/ and its
	@# dependencies are built directly. This affects documentation only.
	for d in util mpi cipher zlib g10; do \
	  $(MAKE) -C $(SRC_DIR)/$$d CFLAGS="$(HIST_CFLAGS)" || exit 1; \
	done
	@$(GPG147) --version | head -2
	@sha256sum $(GPG147)

# ---------------------------------------------------------------- pipeline
.PHONY: analyze cve differential synth rngstats report test provenance
provenance:
	$(PY) -m spa.cli verify-provenance

analyze:
	$(PY) -m spa.cli analyze-key --json $(ROOT)/reports/key_analysis.json

cve:
	$(PY) -m spa.cli lab-cve --trials 500

differential: $(SRC_DIR)
	SPA_GNUPG_SRC=$(SRC_DIR) $(PY) -m spa.cli lab-differential \
	  --src147 $(SRC_DIR) --src1421 $(SRC_DIR_1421)

synth: $(GPG147)
	SPA_GPG147=$(GPG147) $(PY) -m spa.cli lab-synth --count 100

rngstats:
	$(PY) -m spa.cli lab-rngstats --bytes 131072

report:
	SPA_GNUPG_SRC=$(SRC_DIR) $(PY) -m spa.cli report \
	  --gnupg-src $(SRC_DIR) \
	  --output $(ROOT)/reports/AUDIT_REPORT.md \
	  --json $(ROOT)/reports/audit_report.json

test:
	$(PY) -m pytest tests -v

.PHONY: all
all: setup native-gnupg147 provenance analyze cve differential synth rngstats report test
	@echo "complete - see reports/AUDIT_REPORT.md"

# ---------------------------------------------------------------- docker
.PHONY: docker-build docker-report docker-test
docker-build:
	docker compose -f docker/docker-compose.yml build

docker-report: docker-build
	docker compose -f docker/docker-compose.yml run --rm lab

docker-test: docker-build
	docker compose -f docker/docker-compose.yml run --rm tests

.PHONY: clean
clean:
	rm -rf /tmp/spa-cbridge reports/*.json
	find . -name __pycache__ -type d -exec rm -rf {} + 2>/dev/null || true
