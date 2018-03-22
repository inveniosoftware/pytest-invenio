#!/usr/bin/env sh
# -*- coding: utf-8 -*-
#
# This file is part of pytest-invenio.
# Copyright (C) 2017-2018 CERN.
#
# pytest-invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

rm -f .coverage
rm -f .coverage.eager.*
pydocstyle pytest_invenio tests docs && \
isort -rc -c -df && \
check-manifest --ignore ".travis-*" && \
sphinx-build -qnNW docs docs/_build/html && \
# Following is needed in order to get proper code coverage for pytest plugins.
# See https://pytest-cov.readthedocs.io/en/latest/plugins.html
COV_CORE_SOURCE=pytest_invenio COV_CORE_CONFIG=.coveragerc COV_CORE_DATAFILE=.coverage.eager py.test --cov=pytest_invenio
# Run twice to get proper test coverage results
COV_CORE_SOURCE=pytest_invenio COV_CORE_CONFIG=.coveragerc COV_CORE_DATAFILE=.coverage.eager py.test --cov=pytest_invenio
