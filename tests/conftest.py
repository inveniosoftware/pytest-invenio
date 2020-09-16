# -*- coding: utf-8 -*-
#
# This file is part of pytest-invenio.
# Copyright (C) 2017-2018 CERN.
#
# pytest-invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Pytest configuration."""

from __future__ import absolute_import, print_function

import pytest

pytest_plugins = ["pytester"]


@pytest.fixture()
def conftest_testdir(testdir):
    """Conftest fixture with app factories defined."""
    testdir.makeconftest("""
        import pytest

        from flask import Flask, jsonify, current_app
        from functools import partial
        from invenio_db import InvenioDB
        from invenio_mail import InvenioMail
        from invenio_search import InvenioSearch
        from invenio_files_rest import InvenioFilesREST

        def _factory(name, **config):
            app_ = Flask(name)
            app_.config.update(**config)
            InvenioDB(app_)
            InvenioSearch(app_)
            InvenioMail(app_)
            InvenioFilesREST(app_)

            @app_.route('/')
            def index():
                return ('<html>'
                '<head><title>pytest-invenio</title></head>'
                '<body><h1>Hello, World!</h1></body>'
                '</html>')

            @app_.route('/api/')
            def api():
                return jsonify({'app_name': current_app.name})

            return app_

        @pytest.fixture(scope='module')
        def create_app():
            return partial(_factory, 'app')

        @pytest.fixture(scope='module')
        def UserCls():
            return User
    """)
    testdir.makefile(
        ".ini",
        pytest="""
        [pytest]
        live_server_scope = module
        """
    )
    return testdir
