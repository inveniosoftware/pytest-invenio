#!/usr/bin/env bash
# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2020 CERN.
# Copyright (C) 2022 Graz University of Technology.
#
# Invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

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
