# SPDX-FileCopyrightText: 2017-2018 CERN.
# SPDX-License-Identifier: MIT

"""Pytest configuration."""

import pytest

pytest_plugins = ["pytester"]


@pytest.fixture()
def conftest_testdir(testdir):
    """Conftest fixture with app factories defined."""
    testdir.makeconftest(
        """
        import pytest

        from flask import Flask, jsonify, current_app
        from functools import partial
        from invenio_db import InvenioDB
        from invenio_mail import InvenioMail
        from invenio_search import InvenioSearch
        from invenio_files_rest import InvenioFilesREST

        def _factory(name, **config):
            app_ = Flask(name)
            app_.config.update(DB_VERSIONING=False, **config)
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
    """
    )
    testdir.makefile(
        ".ini",
        pytest="""
        [pytest]
        live_server_scope = module
        """,
    )
    return testdir
