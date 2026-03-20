#!/usr/bin/env bash

set -e
set -x

mypy app cli
ruff check app cli scripts
ruff format app cli scripts --check
