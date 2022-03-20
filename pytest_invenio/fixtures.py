# -*- coding: utf-8 -*-
#
# This file is part of pytest-invenio.
# Copyright (C) 2017-2018 CERN.
# Copyright (C) 2018 Esteban J. G. Garbancho.
#
# pytest-invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Pytest fixtures for Invenio."""

import os
import shutil
import sys
import tempfile
from datetime import datetime

import importlib_metadata
import pkg_resources
import pytest
from pytest_flask.plugin import _make_test_response_class
from selenium import webdriver

from .user import UserFixtureBase

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
        INVENIO_STATIC_FOLDER=os.path.join(sys.prefix, 'var/instance/static'),
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


def _celery_config():
    """Factory/Helper function to create the ``celery_config`` fixture.

    When Celery is installed it provides with this same fixture via
    `celery.contrib.pytest
    <https://github.com/celery/celery/blob/master/celery/contrib/pytest.py>`_,
    in this is the case we overwrite this fixture and update the configuration
    with Invenio's default configuration.
    If it is not installed, then we just define a new fixture which returns the
    default Invenio Celery configuration.
    """
    default_config = dict(
        CELERY_TASK_ALWAYS_EAGER=True,
        CELERY_CACHE_BACKEND='memory',
        CELERY_TASK_EAGER_PROPAGATES_EXCEPTIONS=True,
        CELERY_RESULT_BACKEND='cache',
    )

    try:
        pkg_resources.get_distribution('celery')

        # Celery is installed, overwrite fixture
        def inner(celery_config):
            celery_config.update(default_config)
            return celery_config
    except pkg_resources.DistributionNotFound:
        # No Celery, return the default config
        def inner():
            return default_config

    return inner


celery_config_ext = pytest.fixture(
    scope='module', name='celery_config_ext')(_celery_config())
"""Celery configuration (defaults to eager tasks).

Scope: module

This fixture provides the default Celery configuration (eager tasks,
in-memory result backend and exception propagation). It can easily be
overwritten in a specific test module:

.. code-block:: python

    # test_something.py
    import pytest

    pytest.fixture(scope='module')
    def celery_config_ext(celery_config_ext):
        celery_config_ext['CELERY_TASK_ALWAYS_EAGER'] = False
        return celery_config_ext
"""


@pytest.fixture(scope='module')
def app_config(db_uri, broker_uri, celery_config_ext):
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
    icons = {
        'semantic-ui': {
            'key': 'key icon',
            'link': 'linkify icon',
            'shield': 'shield alternate icon',
            'user': 'user icon',
            'codepen': 'codepen icon',
            'cogs': 'cogs icon',
            '*': '{} icon'
        },
        'bootstrap3': {
            'key': 'fa fa-key fa-fw',
            'link': 'fa fa-link fa-fw',
            'shield': 'fa fa-shield fa-fw',
            'user': 'fa fa-user fa-fw',
            'codepen': 'fa fa-codepen fa-fw',
            'cogs': 'fa fa-cogs fa-fw',
            '*': 'fa fa-{} fa-fw',
        }
    }

    return dict(
        APP_DEFAULT_SECURE_HEADERS=dict(
            force_https=False,
            content_security_policy={'default-src': []}
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
        **celery_config_ext,
        # Theme
        APP_THEME=["semantic-ui"],
        THEME_ICONS=icons,
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
    from flask.cli import ScriptInfo
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
    from click.testing import CliRunner

    def cli_invoke(command, input=None, *args):
        return CliRunner().invoke(command, args, input=input, obj=script_info)
    return cli_invoke


def _es_create_indexes(current_search, current_search_client):
    """Create all registered Elasticsearch indexes."""
    from elasticsearch.exceptions import RequestError
    try:
        list(current_search.create())
    except RequestError:
        list(current_search.delete(ignore=[404]))
        list(current_search.create())
    current_search_client.indices.refresh()


def _es_delete_indexes(current_search):
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
    from invenio_search import current_search, current_search_client
    _es_create_indexes(current_search, current_search_client)
    yield current_search_client
    _es_delete_indexes(current_search)


@pytest.fixture(scope='function')
def es_clear(es):
    """Clear Elasticsearch indices after test finishes (function scope).

    Scope: function

    This fixture rollback any changes performed to the indexes during a test,
    in order to leave Elasticsearch in a clean state for the next test.
    """
    from invenio_search import current_search, current_search_client
    yield es
    _es_delete_indexes(current_search)
    _es_create_indexes(current_search, current_search_client)


@pytest.fixture(scope='module')
def database(appctx):
    """Setup database.

    Scope: module

    Normally, tests should use the function-scoped :py:data:`db` fixture
    instead. This fixture takes care of creating the database/tables and
    removing the tables once tests are done.
    """
    from invenio_db import db as db_
    from sqlalchemy_utils.functions import create_database, database_exists
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
    import sqlalchemy as sa
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

    if browser_name.lower() == "chrome":
        # this special handling is required to avoid the
        # 'DevToolsActivePort file doesn't exist' error on github actions
        from selenium.webdriver.chrome.options import Options
        options = Options()
        options.add_argument("--headless")
        driver = getattr(webdriver, browser_name)(chrome_options=options)
    else:
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


@pytest.yield_fixture(scope='module')
def location(database):
    """Creates a simple default location for a test.

    Scope: function

    Use this fixture if your test requires a `files location <https://invenio-
    files-rest.readthedocs.io/en/latest/api.html#invenio_files_rest.models.
    Location>`_. The location will be a default location with the name
    ``pytest-location``.
    """
    from invenio_files_rest.models import Location
    uri = tempfile.mkdtemp()
    location_obj = Location(name="pytest-location", uri=uri, default=True)

    database.session.add(location_obj)
    database.session.commit()

    yield location_obj

    shutil.rmtree(location_obj.uri)


@pytest.fixture(scope="function")
def bucket_from_dir(db, location):
    '''Creates a bucket from the specified directory.

    Scope: function

    Use this fixture if your test requires a `files bucket <https://invenio-
    files-rest.readthedocs.io/en/latest/api.html#invenio_files_rest.models.
    Bucket>`_. The ``bucket_from_dir`` fixture returns a function with the
    following signature:

    .. code-block:: python

        def create_bucket_from_dir(source_dir, location_obj=None):
            """Create bucket from the specified source directory.

            :param source_dir: The directory to create the bucket from.
            :param location_obj: Optional location object to use. If None
                is specified, get the current default location.
            :returns: The new bucket object.
            """

    Below is an example of how to use the ``bucket_from_dir`` fixture:

    .. code-block:: python

        def test_with_bucket(bucket_from_dir):
            bucket = bucket_from_dir('/my/directory/path')
            # ... use the bucket for your test
    '''
    def create_bucket_from_dir(source_dir, location_obj=None):
        """Create bucket from the specified source directory.

        :param source_dir: The directory to create the bucket from.
        :param location_obj: Optional location object to use. If None
            is specified, get the current default location.
        :returns: The new bucket object.
        """
        if not location_obj:
            from invenio_files_rest.models import Bucket, Location, \
                ObjectVersion
            location_obj = Location.get_default() or location
        bucket_obj = Bucket.create(location_obj)
        for file_name in os.listdir(source_dir):
            full_file_path = os.path.join(source_dir, file_name)
            if os.path.isdir(full_file_path):
                continue
            file_obj = open(full_file_path, 'rb')
            ObjectVersion.create(bucket_obj, key=file_name, stream=file_obj)
        db.session.commit()
        return bucket_obj
    return create_bucket_from_dir


class MockDistribution(pkg_resources.Distribution):
    """A mocked distribution that we can inject entry points with."""

    def __init__(self, extra_entry_points):
        """Initialise the extra entry point."""
        self._ep_map = {}
        # Create the entry point group map (which eventually will be used to
        # iterate over entry points). See source code for Distribution,
        # EntryPoint and WorkingSet in pkg_resources module.
        for group, entries in extra_entry_points.items():
            group_map = {}
            for ep_str in entries:
                ep = pkg_resources.EntryPoint.parse(ep_str)
                ep.require = self._require_noop
                group_map[ep.name] = ep
            self._ep_map[group] = group_map
        # Note location must have a non-empty string value, as it is used as a
        # key into a dictionary.
        super().__init__(location='unknown')

    def _require_noop(self, *args, **kwargs):
        """Do nothing on entry point require."""
        pass


class MockImportlibDistribution(importlib_metadata.Distribution):
    """A mocked distribution where we can inject entry points."""

    def __init__(self, extra_entry_points):
        """Entry points for the distribution."""
        self._entry_points = extra_entry_points

    @property
    def name(self):
        """Return the 'Name' metadata for the distribution package."""
        return 'MockDistribution'

    @property
    def entry_points(self):
        """Iterate over entry points."""
        for group, eps_lines in self._entry_points.items():
            for ep_line in eps_lines:
                name, value = ep_line.split('=', maxsplit=1)
                yield importlib_metadata.EntryPoint(
                    # strip possible white space due to split on "="
                    name=name.strip(), value=value.strip(), group=group
                )


@pytest.fixture(scope="module")
def entry_points(extra_entry_points):
    """Entry points fixture.

    Scope: module

    Invenio relies heavily on Python entry points for constructing an
    application and it can be rather cumbersome to try to register database
    models, search mappings etc yourself afterwards.

    This fixture allows you to inject extra entry points into the application
    loading, so that you can load e.g. a testing module or test mapping.

    To use the fixture simply define the ``extra_entry_points()`` fixture,
    and then depend on the ``entry_points()`` fixture in your ``create_app``
    fixture:

    .. code-block:: python

        @pytest.fixture(scope="module")
        def extra_entry_points():
            return {
                'invenio_db.models': [
                    'mock_module = mock_module.models',
                ]
            }

        @pytest.fixture(scope="module")
        def create_app(instance_path, entry_points):
            return _create_api
    """
    # Create mocked distributions
    pkg_resources_dist = MockDistribution(extra_entry_points)
    importlib_dist = MockImportlibDistribution(extra_entry_points)

    #
    # Patch importlib
    #
    old_distributions = importlib_metadata.distributions

    def distributions(**kwargs):
        for dist in old_distributions(**kwargs):
            yield dist
        yield importlib_dist

    importlib_metadata.distributions = distributions

    #
    # Patch pkg_resources
    #
    # First make a copy of the working_set state, so that we can restore the
    # state.
    workingset_state = pkg_resources.working_set.__getstate__()
    # Next, make a fake distribution that will yield the extra entry points and
    # add them to the global working_set.
    pkg_resources.working_set.add(pkg_resources_dist)

    yield pkg_resources_dist

    # Last, we restore the original workingset state and old importlib.
    pkg_resources.working_set.__setstate__(workingset_state)
    importlib_metadata.distributions = old_distributions


@pytest.fixture(scope="module")
def extra_entry_points():
    """Extra entry points.

    Overwrite this fixture to define extra entry points.
    """
    return {}


@pytest.fixture(scope="module")
def celery_config():
    """Empty celery config."""
    return {}


@pytest.fixture(scope='session')
def UserFixture():
    """Fixture to help create user fixtures.

    Scope: session

    .. code-block:: python

        @pytest.fixture()
        def myuser(UserFixture, app, db):
            u = UserFixture(
                email="myuser@inveniosoftware.org",
                password="auser",
            )
            u.create(app, db)
            return u

        def test_with_user(service, myuser):
            service.dosomething(myuser.identity)



    """
    return UserFixtureBase
