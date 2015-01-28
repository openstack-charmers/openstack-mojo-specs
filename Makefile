#!/usr/bin/make
PYTHON := /usr/bin/env python

lint:
	@./scripts/check-lint.sh

gen_spec_summary:
	@./scripts/gen-spec-summary.sh > SPEC_SUMMARY.txt
