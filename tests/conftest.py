# -*- coding: utf-8 -*-
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

        def _factory(name, **config):
            app_ = Flask(name)
            app_.config.update(**config)
            InvenioDB(app_)
            InvenioSearch(app_)
            InvenioMail(app_)

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
    return testdir
