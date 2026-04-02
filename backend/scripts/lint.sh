#!/usr/bin/env bash

set -e
set -x

pyright
ruff check app cli scripts
ruff format app cli scripts --check
