# -*- coding: utf-8 -*-
#
# This file is part of pytest-invenio.
# Copyright (C) 2017-2018 CERN.
#
# pytest-invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Pytest fixtures for Invenio."""

from __future__ import absolute_import, print_function

import json
import os
import shutil
import tempfile
from datetime import datetime

import pytest
import sqlalchemy as sa
from click.testing import CliRunner
from flask.cli import ScriptInfo
from invenio_db import db as db_
from invenio_search import current_search, current_search_client
from pytest_flask.plugin import _make_test_response_class
from selenium import webdriver
from sqlalchemy_utils.functions import create_database, database_exists


SCREENSHOT_SCRIPT = """import base64
with open('screenshot.png', 'wb') as fp:
    fp.write(base64.b64decode('''{data}'''))
"""


@pytest.fixture(scope='module')
def default_handler():
    """Flask default logging handler.

    Flask 0.13/1.0 changed logging to not add the default handler in case a
    handler is already installed. pytest automatically adds a handler to the
    root logger, causing Flask not to add a handler. This is an issue when
    testing Click output which uses the logger to output to the console.
    """
    try:
        from flask.logging import default_handler as handler
        return handler
    except ImportError:
        return None


@pytest.fixture(scope='module')
def instance_path():
    """Temporary instance path.

    Scope: module

    This fixture creates a temporary directory and sets the ``INSTANCE_PATH``
    environment variable to this directory. The directory is automatically
    removed.
    """
    path = tempfile.mkdtemp()
    os.environ.update(
        INVENIO_INSTANCE_PATH=os.environ.get('INSTANCE_PATH', path),
    )
    yield path
    os.environ.pop('INVENIO_INSTANCE_PATH', None)
    shutil.rmtree(path)


@pytest.fixture(scope='module')
def db_uri(instance_path):
    """Database URI (defaults to an SQLite datbase in the instance path).

    Scope: module

    The database can be overwritten by setting the ``SQLALCHEMY_DATABASE_URI``
    environment variable to a SQLAlchemy database URI.
    """
    if 'SQLALCHEMY_DATABASE_URI' in os.environ:
        yield os.environ['SQLALCHEMY_DATABASE_URI']
    else:
        filepath = tempfile.mkstemp(
            dir=instance_path, prefix='test', suffix='.db')[1]
        yield 'sqlite:///{}'.format(filepath)
        os.remove(filepath)


@pytest.fixture(scope='module')
def broker_uri():
    """Broker URI (defaults to an RabbitMQ on localhost).

    Scope: module

    The broker can be overwritten by setting the ``BROKER_URL`` environment
    variable.
    """
    yield os.environ.get('BROKER_URL', 'amqp://guest:guest@localhost:5672//')


@pytest.fixture(scope='module')
def celery_config(celery_config):
    """Celery configuration (defaults to eager tasks).

    Scope: module

    This fixture provides the default Celery configuration (eager tasks,
    in-memory result backend and exception propagation). It can easily be
    overwritten in a specific test module:

    .. code-block:: python

        # test_something.py
        import pytest

        pytest.fixture(scope='module')
        def celery_config(celery_config):
            celery_config['CELERY_ALWAYS_EAGER'] = False
            return celery_config
    """

    celery_config.update(dict(
        CELERY_ALWAYS_EAGER=True,
        CELERY_CACHE_BACKEND='memory',
        CELERY_EAGER_PROPAGATES_EXCEPTIONS=True,
        CELERY_RESULT_BACKEND='cache',
    ))
    return celery_config


@pytest.fixture(scope='module')
def app_config(db_uri, broker_uri, celery_config):
    """Application configuration fixture.

    Scope: module

    This fixture sets default configuration for an Invenio application to make
    it suitable for testing. The database and broker URL are injected into the
    config, CSRF-protection in forms disabled, HTTP secure headers is disabled,
    mail sending is output to console.

    The fixture can easily be customized in your ``conftest.py`` or specific
    test module:

    .. code-block:: python

        # conftest.py
        import pytest

        pytest.fixture(scope='module')
        def app_config(app_config):
            app_config['MYVAR'] = 'test'
            return app_config
    """
    return dict(
        APP_DEFAULT_SECURE_HEADERS=dict(
            force_https=False,
        ),
        # Broker configuration
        BROKER_URL=broker_uri,
        # Disable Flask-DebugToolbar if installed.
        DEBUG_TB_ENABLED=False,
        # Disable mail sending.
        MAIL_SUPPRESS_SEND=True,
        # Allow testing OAuth without SSL.
        OAUTHLIB_INSECURE_TRANSPORT=True,
        OAUTH2_CACHE_TYPE='simple',
        # Set test secret keys
        SECRET_KEY='test-secret-key',
        SECURITY_PASSWORD_SALT='test-secret-key',
        # Database configuration
        SQLALCHEMY_DATABASE_URI=db_uri,
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        # Flask testing mode
        TESTING=True,
        # Disable CRSF protection in WTForms
        WTF_CSRF_ENABLED=False,
        # Celery configuration
        **celery_config
    )


@pytest.fixture(scope='module')
def base_app(create_app, app_config, request, default_handler):
    """Base application fixture (without database, search and cache).

    Scope: module.

    This fixture is responsible for creating the Invenio application. It
    depends on an application factory fixture that must be defined by the user.

    .. code-block:: python

        # confest.py
        import pytest

        @pytest.fixture(scope='module)
        def create_app():
            from invenio_app.factory import create_api
            return create_api

    It is possible to overide the application factory for a specific test
    module, either by defining a fixture like above example, or simply setting
    the ``create_app`` property on the module:

    .. code-block:: python

        # test_something.py

        from invenio_app.factory import create_api
        create_app = create_api

        def test_acase(base_app):
            # ...
    """
    # Use create_app from the module if defined, otherwise use default
    # create_app fixture.
    create_app = getattr(request.module, 'create_app', create_app)
    app_ = create_app(**app_config)
    # See documentation for default_handler
    if default_handler:
        app_.logger.addHandler(default_handler)
    yield app_


@pytest.fixture(autouse=True, scope='function')
def _monkeypatch_response_class(request, monkeypatch):
    """Set custom response class to easily test JSON responses.

    .. code-block:: python

        def test_json(client):
            res = client.get(...)
            assert res.json == {'ping': 'pong'}

    Pytest-Flask provides this already for the "app" fixture
    """
    if 'base_app' not in request.fixturenames:
        return

    base_app = request.getfixturevalue('base_app')
    monkeypatch.setattr(
        base_app, 'response_class',
        _make_test_response_class(base_app.response_class))


@pytest.fixture(scope='function')
def base_client(base_app):
    """Test client for the base application fixture.

    Scope: function

    If you need the database and search indexes initialized, simply use the
    Pytest-Flask fixture ``client`` instead. This fixture is mainly useful if
    you need a test client without needing to initialize both the database and
    search indexes.
    """
    with base_app.test_client() as client:
        yield client


@pytest.fixture(scope='module')
def appctx(base_app):
    """Application context for the current base application.

    Scope: module

    This fixture pushes an application context on the stack, so that
    ``current_app`` is defined and e.g ``url_for`` will also work.
    """
    with base_app.app_context():
        yield base_app


@pytest.fixture(scope='module')
def script_info(base_app):
    """Get ScriptInfo object for testing a CLI command.

    Scope: module

    .. code-block:: python

        def test_cmd(script_info):
            runner = CliRunner()
            result = runner.invoke(mycmd, obj=script_info)
            assert result.exit_code == 0
    """
    return ScriptInfo(create_app=lambda info: base_app)


@pytest.fixture(scope='module')
def cli_runner(script_info):
    """Create a CLI runner for testing a CLI command.

    Scope: module

    .. code-block:: python

        def test_cmd(cli_runner):
            result = cli_runner(mycmd)
            assert result.exit_code == 0
    """
    def cli_invoke(command, input=None, *args):
        return CliRunner().invoke(command, args, input=input, obj=script_info)
    return cli_invoke


def _es_create_indexes():
    """Create all registered Elasticsearch indexes."""
    from elasticsearch.exceptions import RequestError
    try:
        list(current_search.create())
    except RequestError:
        list(current_search.delete(ignore=[404]))
        list(current_search.create())
    current_search_client.indices.refresh()


def _es_delete_indexes():
    """Delete all registered Elasticsearch indexes."""
    list(current_search.delete(ignore=[404]))


@pytest.fixture(scope='module')
def es(appctx):
    """Setup and teardown all registered Elasticsearch indices.

    Scope: module

    This fixture will create all registered indexes in Elasticsearch and remove
    once done. Fixtures that perform changes (e.g. index or remove documents),
    should used the function-scoped :py:data:`es_clear` fixture to leave the
    indexes clean for the following tests.
    """
    _es_create_indexes()
    yield current_search_client
    _es_delete_indexes()


@pytest.fixture(scope='function')
def es_clear(es):
    """Clear Elasticsearch indices after test finishes (function scope).

    Scope: function

    This fixture rollback any changes performed to the indexes during a test,
    in order to leave Elasticsearch in a clean state for the next test.
    """
    yield es
    _es_delete_indexes()
    _es_create_indexes()


@pytest.fixture(scope='module')
def database(appctx):
    """Setup database.

    Scope: module

    Normally, tests should use the function-scoped :py:data:`db` fixture
    instead. This fixture takes care of creating the database/tables and
    removing the tables once tests are done.
    """
    if not database_exists(str(db_.engine.url)):
        create_database(str(db_.engine.url))
    db_.create_all()

    yield db_

    db_.session.remove()
    db_.drop_all()


@pytest.fixture(scope='function')
def db(database):
    """Creates a new database session for a test.

    Scope: function

    You must use this fixture if your test connects to the database. The
    fixture will set a save point and rollback all changes performed during
    the test (this is much faster than recreating the entire database).
    """
    connection = database.engine.connect()
    transaction = connection.begin()

    options = dict(bind=connection, binds={})
    session = database.create_scoped_session(options=options)

    session.begin_nested()

    # `session` is actually a scoped_session. For the `after_transaction_end`
    # event, we need a session instance to listen for, hence the `session()`
    # call.
    @sa.event.listens_for(session(), 'after_transaction_end')
    def restart_savepoint(sess, trans):
        if trans.nested and not trans._parent.nested:
            session.expire_all()
            session.begin_nested()

    old_session = database.session
    database.session = session

    yield database

    session.remove()
    transaction.rollback()
    connection.close()
    database.session = old_session


@pytest.fixture(scope='function')
def mailbox(base_app):
    """Mailbox fixture.

    Scope: function

    This fixture provides a mailbox that captures all outgoing emails and thus
    easily allow you to test mail sending in your app:

    .. code-block:: python

        def test_mailbox(appctx, mailbox):
            appctx.extensions['mail'].send_message(
                sender='no-reply@localhost',
                subject='Testing',
                body='Test',
                recipients=['no-reply@localhost'])
            assert len(mailbox) == 1
    """
    ext = base_app.extensions.get('mail')
    if ext is None:
        raise RuntimeError(
            'Invenio-Mail extension is not installed on application.')
    else:
        with ext.record_messages() as outbox:
            yield outbox


@pytest.fixture(scope='module')
def app(base_app, es, database):
    """Invenio application with database and Elasticsearch.

    Scope: module

    See also :py:data:`base_app` for an Invenio application fixture that
    does not initialize database and Elasticsearch.
    """
    yield base_app


@pytest.fixture(scope='session')
def browser(request):
    """Selenium webdriver fixture.

    Scope: session

    The fixture initializes a Selenium webdriver which can be used for
    end-to-end testing of your application:

    .. code-block:: python

        from flask import url_for

        def test_browser(live_server, browser):
            browser.get(url_for('index', _external=True))

    The ``live_server`` fixture is provided by Pytest-Flask and uses the
    :py:data:`app` fixture to determine which application to start.

    .. note::

        End-to-end test are only executed if the environment variable ``E2E``
        is set to yes::

            $ export E2E=yes

        This allows you to easily switch on/off end-to-end tests.

    By default, a Chrome webdriver client will be created. However, you can
    customize which browsers to test via the ``E2E_WEBDRIVER_BROWSERS``
    environment variable:

    .. code-block:: console

        $ export E2E_WEBDRIVER_BROWSERS="Chrome Firefox"

    If multiple browsers are requested, each test case using the
    :py:data:`browser` fixture will be parameterized with the list of browsers.

    In case the test fail, a screenshot will be taken and saved in folder
    ``.e2e_screenshots``.
    """
    browser_name = getattr(request, 'param', 'Chrome')
    driver = getattr(webdriver, browser_name)()

    yield driver

    _take_screenshot_if_test_failed(driver, request)

    # Quit the webdriver instance
    driver.quit()


def _take_screenshot_if_test_failed(driver, request):
    """Take a screenshot if the test failed."""
    if request.node.rep_call.failed:
        filename = '{modname}::{funname}::{now}.png'.format(
            modname=request.module.__name__,
            funname=request.function.__name__ if request.function else '',
            now=datetime.now().isoformat())
        filepath = os.path.join(_get_screenshots_dir(), filename)
        driver.get_screenshot_as_file(filepath)
        print("Screenshot of failing test:")
        if os.environ.get('E2E_OUTPUT') == 'base64':
            print(SCREENSHOT_SCRIPT.format(
                data=driver.get_screenshot_as_base64()))
        else:
            print(filepath)


def _get_screenshots_dir():
    """Create the screenshots directory."""
    directory = ".e2e_screenshots"
    if not os.path.exists(directory):
        os.makedirs(directory)
    return directory
