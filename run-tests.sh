#!/usr/bin/env sh
#
# This file is part of Invenio.
# Copyright (C) 2017 CERN.
#
# Invenio is free software; you can redistribute it and/or modify it under the
# terms of the MIT License; see LICENSE file for more details.
#
# In applying this license, CERN does not waive the privileges and immunities
# granted to it by virtue of its status as an Intergovernmental Organization
# or submit itself to any jurisdiction.

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
