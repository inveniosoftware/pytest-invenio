# -*- coding: utf-8 -*-
#
# This file is part of pytest-invenio.
# Copyright (C) 2017-2018 CERN.
# Copyright (C) 2018 Northwestern University, Feinberg School of Medicine,
# Galter Health Sciences Library.
#
# pytest-invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Pytest plugin for Invenio.

The plugin adds fixtures to help with creation of applications as well as
configuring and initializing the database and search engine.

Additional the plugin helps with configuring end-to-end tests with selenium
and taking screenshots of failed selenium tests (useful for inspecting why
the test failed on CI systems).
"""

from __future__ import absolute_import, print_function

import os

import pytest

from .fixtures import _monkeypatch_response_class, app, app_config, appctx, \
    base_app, base_client, broker_uri, browser, bucket_from_dir, \
    celery_config_ext, cli_runner, database, db, db_uri, default_handler, \
    entry_points, es, es_clear, extra_entry_points, instance_path, location, \
    mailbox, script_info


def pytest_generate_tests(metafunc):
    """Skip end-to-end tests unless requested via ``E2E`` env variable.

    A screenshot is taken in case of test failures. Set the environment
    variable ``E2E_OUTPUT`` to ``base64`` to have the base64 encoded screenshot
    printed to stdout (useful in e.g. CI systems). Screenshots are saved to
    an ``.e2e_screenshots`` folder.

    Overrides pytest's default test collection function to skip tests using the
    ``browser`` fixture, unless the environment variable ``E2E`` is set to
    ``yes``.

    Each test using the ``browser`` fixture is parameterized with the list of
    browsers declared by the ``E2E_WEBDRIVER_BROWSERS`` environment variable.
    By default only Chrome is tested.
    """
    if 'browser' in metafunc.fixturenames:
        if os.environ.get('E2E', 'no').lower() != 'yes':
            pytest.skip(
                "End-to-end tests skipped because E2E environment variable "
                "was not set to 'yes'.")

        # Parameterize test based on list of browsers.
        browsers = os.environ.get('E2E_WEBDRIVER_BROWSERS', 'Chrome').split()
        metafunc.parametrize(
            'browser', browsers, indirect=True, scope='function'
        )


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """Add hook to track if the test passed or failed."""
    # execute all other hooks to obtain the report object
    outcome = yield
    rep = outcome.get_result()

    # set a report attribute for each phase of a call, which can
    # be "setup", "call", "teardown"
    # used to e.g. during browser tests to take screenshot on failure
    setattr(item, "rep_" + rep.when, rep)
