#!/usr/bin/make
PYTHON := /usr/bin/env python

lint:
	@./helper/scripts/check-lint.sh
	@echo Checking lint...
	@pep8 -v helper/collect  helper/setup  helper/tests  helper/utils

gen_spec_summary:
	@./helper/scripts/gen-spec-summary.sh > SPEC_SUMMARY.txt

list_specs:
	@./helper/scripts/list-specs.sh
