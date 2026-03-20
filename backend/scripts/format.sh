#!/bin/sh -e
set -x

ruff check app cli scripts --fix
ruff format app cli scripts
