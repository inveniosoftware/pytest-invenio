#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2020 CERN.
# SPDX-FileCopyrightText: 2022 Graz University of Technology.
# SPDX-License-Identifier: MIT

# Quit on errors
set -o errexit

# Quit on unbound symbols
set -o nounset

# Always bring down docker services
function cleanup() {
    eval "$(docker-services-cli down --env)"
}
trap cleanup EXIT


python -m check_manifest
python -m sphinx.cmd.build -qnNW docs docs/_build/html
eval "$(docker-services-cli up --search ${SEARCH:-opensearch2} --env)"
python -m pytest --runpytest=subprocess
tests_exit_code=$?
exit "$tests_exit_code"
