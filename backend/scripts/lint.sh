#!/usr/bin/env bash

set -e
set -x

pyright
ruff check app scripts
ruff format app scripts --check
