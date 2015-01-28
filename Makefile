#!/usr/bin/make
PYTHON := /usr/bin/env python

lint:
	@flake8 helper

gen_spec_summary:
	@./gen-spec-summary.sh
