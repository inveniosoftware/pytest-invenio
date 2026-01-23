# -*- coding: utf-8 -*-
#
# This file is part of pytest-invenio.
# Copyright (C) 2017-2025 CERN.
# Copyright (C) 2018 Esteban J. G. Garbancho.
# Copyright (C) 2024-2025 Graz University of Technology.
#
# pytest-invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Pytest fixtures for Invenio."""

import ast
import importlib.metadata
import os
import shutil
import sys
import tempfile
from datetime import datetime
from importlib.metadata import PackageNotFoundError, version
from warnings import warn

import pytest
from pytest_flask.plugin import _make_test_response_class
from selenium import webdriver

from .user import UserFixtureBase

python_minor = sys.version_info[1]

if python_minor < 10:
    import importlib_metadata


SCREENSHOT_SCRIPT = """import base64
with open('screenshot.png', 'wb') as fp:
    fp.write(base64.b64decode('''{data}'''))
"""


@pytest.fixture(scope="module")
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


@pytest.fixture(scope="module")
def instance_path():
    """Temporary instance path.

    Scope: module

    This fixture creates a temporary directory and sets the ``INSTANCE_PATH``
    environment variable to this directory. The directory is automatically
    removed.
    """
    path = tempfile.mkdtemp()
    os.environ.update(
        INVENIO_INSTANCE_PATH=os.environ.get("INSTANCE_PATH", path),
        INVENIO_STATIC_FOLDER=os.path.join(sys.prefix, "var/instance/static"),
    )
    yield path
    os.environ.pop("INVENIO_INSTANCE_PATH", None)
    shutil.rmtree(path)


@pytest.fixture(scope="module")
def cache_uri():
    """Cache uri."""
    if "CACHE_REDIS_URL" in os.environ:
        yield os.environ["CACHE_REDIS_URL"]
    else:
        yield None


@pytest.fixture(scope="module")
def db_uri(instance_path):
    """Database URI (defaults to an SQLite datbase in the instance path).

    Scope: module

    The database can be overwritten by setting the ``SQLALCHEMY_DATABASE_URI``
    environment variable to a SQLAlchemy database URI.
    """
    if "SQLALCHEMY_DATABASE_URI" in os.environ:
        yield os.environ["SQLALCHEMY_DATABASE_URI"]
    else:
        filepath = tempfile.mkstemp(dir=instance_path, prefix="test", suffix=".db")[1]
        yield "sqlite:///{}".format(filepath)
        os.remove(filepath)


@pytest.fixture(scope="module")
def broker_uri():
    """Broker URI (defaults to an RabbitMQ on localhost).

    Scope: module

    The broker can be overwritten by setting the ``BROKER_URL`` environment
    variable.
    """
    yield os.environ.get("BROKER_URL", "amqp://guest:guest@localhost:5672//")


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
        CELERY_CACHE_BACKEND="memory",
        CELERY_TASK_EAGER_PROPAGATES_EXCEPTIONS=True,
        CELERY_RESULT_BACKEND="cache",
    )

    try:
        version("celery")

        # Celery is installed, overwrite fixture
        def inner(celery_config):
            celery_config.update(default_config)
            return celery_config

    except PackageNotFoundError:
        # No Celery, return the default config
        def inner():
            return default_config

    return inner


celery_config_ext = pytest.fixture(scope="module", name="celery_config_ext")(
    _celery_config()
)
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


@pytest.fixture(scope="module")
def search_hosts():
    """Search hosts (default to localhost:9200).

    Scope: module

    The search hosts can be overwritten by setting the ``SEARCH_HOSTS``
    environment variable to a list of dictionaries with ``host`` and ``port`` keys.
    """
    if "SEARCH_HOSTS" in os.environ:
        yield ast.literal_eval(os.environ["SEARCH_HOSTS"])
    else:
        yield [{"host": "localhost", "port": 9200}]


@pytest.fixture(scope="module")
def app_config(db_uri, broker_uri, celery_config_ext, search_hosts):
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
        "semantic-ui": {
            "key": "key icon",
            "link": "linkify icon",
            "shield": "shield alternate icon",
            "user": "user icon",
            "codepen": "codepen icon",
            "cogs": "cogs icon",
            "*": "{} icon",
        },
        "bootstrap3": {
            "key": "fa fa-key fa-fw",
            "link": "fa fa-link fa-fw",
            "shield": "fa fa-shield fa-fw",
            "user": "fa fa-user fa-fw",
            "codepen": "fa fa-codepen fa-fw",
            "cogs": "fa fa-cogs fa-fw",
            "*": "fa fa-{} fa-fw",
        },
    }

    # extra database options to avoid connection pool exhaustion in tests
    # not every package depends on sqlalchemy, so we need to import it here
    # with the exception handled
    try:
        from sqlalchemy.pool import NullPool

        db_options = {
            "SQLALCHEMY_ENGINE_OPTIONS": {
                "poolclass": NullPool,
            },
        }
    except ImportError:
        db_options = {}

    return dict(
        APP_DEFAULT_SECURE_HEADERS=dict(
            force_https=False, content_security_policy={"default-src": []}
        ),
        # Broker configuration
        BROKER_URL=broker_uri,
        # Disable Flask-DebugToolbar if installed.
        DEBUG_TB_ENABLED=False,
        # Disable mail sending.
        MAIL_SUPPRESS_SEND=True,
        # Allow testing OAuth without SSL.
        OAUTHLIB_INSECURE_TRANSPORT=True,
        OAUTH2_CACHE_TYPE="simple",
        # Disable rate-limiting
        RATELIMIT_ENABLED=False,
        # Set test secret keys
        SECRET_KEY="test-secret-key",
        SECURITY_PASSWORD_SALT="test-secret-key",
        # Database configuration
        SQLALCHEMY_DATABASE_URI=db_uri,
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        # Search configuration
        SEARCH_HOSTS=search_hosts,
        # Flask testing mode
        TESTING=True,
        # Disable CRSF protection in WTForms
        WTF_CSRF_ENABLED=False,
        # Celery configuration
        **celery_config_ext,
        # Theme
        APP_THEME=["semantic-ui"],
        THEME_ICONS=icons,
        **db_options,
    )


@pytest.fixture(scope="module")
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

    create_app = getattr(request.module, "create_app", create_app)
    app_ = create_app(**app_config)

    def delete_user_from_g(exception):
        """Delete user from `flask.g` when the request is tearing down.

        Flask-login==0.6.2 changed the way the user is saved i.e uses `flask.g`.
        Flask.g is pointing to the application context which is initialized per
        request. That said, `pytest-flask` is pushing an application context on each
        test initialization that causes problems as subsequent requests during a test
        are detecting the active application request and not popping it when the
        sub-request is tearing down. That causes the logged in user to remain cached
        for the whole duration of the test. To fix this, we add an explicit teardown
        handler that will pop out the logged in user in each request and it will force
        the user to be loaded each time.
        """
        from flask import g

        if "_login_user" in g:
            del g._login_user

    app_.teardown_request(delete_user_from_g)

    # See documentation for default_handler
    if default_handler:
        app_.logger.addHandler(default_handler)
    yield app_


@pytest.fixture(autouse=True, scope="function")
def _monkeypatch_response_class(request, monkeypatch):
    """Set custom response class to easily test JSON responses.

    .. code-block:: python

        def test_json(client):
            res = client.get(...)
            assert res.json == {'ping': 'pong'}

    Pytest-Flask provides this already for the "app" fixture
    """
    if "base_app" not in request.fixturenames:
        return

    base_app = request.getfixturevalue("base_app")
    monkeypatch.setattr(
        base_app, "response_class", _make_test_response_class(base_app.response_class)
    )


@pytest.fixture(scope="function")
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


@pytest.fixture(scope="module")
def appctx(base_app):
    """Application context for the current base application.

    Scope: module

    This fixture pushes an application context on the stack, so that
    ``current_app`` is defined and e.g ``url_for`` will also work.
    """
    with base_app.app_context():
        yield base_app


@pytest.fixture(scope="module")
def script_info(base_app):
    """Get ScriptInfo object for testing a CLI command (DEPRECATED).

    Scope: module

    Use the ``cli_runner`` runner fixture directly, or use the base_app:
    """
    from flask.cli import ScriptInfo

    warn(
        "script_info is deprecated. Use cli_runner directly instead.",
        DeprecationWarning,
    )
    return ScriptInfo(create_app=lambda *args: base_app)


@pytest.fixture(scope="module")
def cli_runner(base_app):
    """Create a CLI runner for testing a CLI command.

    Scope: module

    .. code-block:: python

        def test_cmd(cli_runner):
            result = cli_runner(mycmd)
            assert result.exit_code == 0
    """

    def cli_invoke(command, input=None, *args):
        return base_app.test_cli_runner().invoke(command, args, input=input)

    return cli_invoke


def _search_create_indexes(current_search, current_search_client):
    """Create all registered search indexes."""
    from invenio_search.engine import search

    try:
        list(current_search.create())
    except search.RequestError:
        list(current_search.delete(ignore=[404]))
        list(current_search.create())
    current_search_client.indices.refresh()


def _search_delete_indexes(current_search):
    """Delete all registered search indexes."""
    list(current_search.delete(ignore=[404]))


@pytest.fixture(scope="module")
def search(appctx):
    """Setup and teardown all registered search indices.

    Scope: module

    This fixture will create all registered indexes in search and remove
    once done. Fixtures that perform changes (e.g. index or remove documents),
    should used the function-scoped :py:data:`search_clear` fixture to leave the
    indexes clean for the following tests.
    """
    from invenio_search import current_search, current_search_client

    _search_create_indexes(current_search, current_search_client)
    yield current_search_client
    _search_delete_indexes(current_search)


@pytest.fixture(scope="module")
def es(search):
    """Alias for search fixture."""
    warn(
        "`es` fixture is deprecated, use `search` instead.",
        DeprecationWarning,
    )
    yield search


@pytest.fixture(scope="function")
def search_clear(search):
    """Clear search indices after test finishes (function scope).

    Scope: function

    This fixture rollback any changes performed to the indexes during a test,
    in order to leave search in a clean state for the next test.
    """
    from invenio_search import current_search, current_search_client

    yield search
    _search_delete_indexes(current_search)
    _search_create_indexes(current_search, current_search_client)


@pytest.fixture(scope="function")
def es_clear(search_clear):
    """Alias for search_clear fixture."""
    warn(
        "`es_clear` fixture is deprecated, use `search_clear` instead.",
        DeprecationWarning,
    )
    yield search_clear


@pytest.fixture(scope="module")
def database(appctx):
    """Setup database.

    Scope: module

    Normally, tests should use the function-scoped :py:data:`db` fixture
    instead. This fixture takes care of creating the database/tables and
    removing the tables once tests are done.
    """
    from invenio_db import db as db_
    from sqlalchemy_utils.functions import create_database, database_exists

    if not database_exists(str(db_.engine.url.render_as_string(hide_password=False))):
        create_database(str(db_.engine.url.render_as_string(hide_password=False)))

    # Use unlogged tables for PostgreSQL (see https://github.com/sqlalchemy/alembic/discussions/1108)
    if db_.engine.name == "postgresql":
        from sqlalchemy.ext.compiler import compiles
        from sqlalchemy.schema import CreateTable

        @compiles(CreateTable)
        def _compile_unlogged(element, compiler, **kwargs):
            return compiler.visit_create_table(element).replace(
                "CREATE TABLE ",
                "CREATE UNLOGGED TABLE ",
            )

    db_.create_all()

    yield db_

    db_.session.remove()
    db_.drop_all()


@pytest.fixture(scope="function")
def db_session_options():
    """Database session options.

    Use to override options like ``expire_on_commit`` for the database session, which
    helps with ``sqlalchemy.orm.exc.DetachedInstanceError`` when models are not bound
    to the session between transactions/requests/service-calls.

    .. code-block:: python

        @pytest.fixture(scope='function')
        def db_session_options():
            return dict(expire_on_commit=False)
    """
    return {}


@pytest.fixture(scope="function")
def db(database, db_session_options):
    """Creates a new database session for a test.

    Scope: function

    You must use this fixture if your test connects to the database. The
    fixture will set a save point and rollback all changes performed during
    the test (this is much faster than recreating the entire database).
    """
    from flask_sqlalchemy.session import Session as FlaskSQLAlchemySession

    class PytestInvenioSession(FlaskSQLAlchemySession):
        def get_bind(self, mapper=None, clause=None, bind=None, **kwargs):
            if self.bind:
                return self.bind
            return super().get_bind(mapper=mapper, clause=clause, bind=bind, **kwargs)

        def rollback(self) -> None:
            if self._transaction is None:
                pass
            else:
                self._transaction.rollback(_to_root=False)

    connection = database.engine.connect()
    connection.begin()

    options = dict(
        bind=connection,
        binds={},
        **db_session_options,
        class_=PytestInvenioSession,
    )
    session = database._make_scoped_session(options=options)

    session.begin_nested()

    old_session = database.session
    database.session = session

    yield database

    session.rollback()
    connection.close()
    database.session = old_session


@pytest.fixture(scope="function")
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
    ext = base_app.extensions.get("mail")
    if ext is None:
        raise RuntimeError("Invenio-Mail extension is not installed on application.")
    else:
        with ext.record_messages() as outbox:
            yield outbox


@pytest.fixture(scope="module")
def app(base_app, search, database):
    """Invenio application with database and search.

    Scope: module

    See also :py:data:`base_app` for an Invenio application fixture that
    does not initialize database and search.
    """
    yield base_app


@pytest.fixture(scope="session")
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
    browser_name = getattr(request, "param", "Chrome")

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
        filename = "{modname}::{funname}::{now}.png".format(
            modname=request.module.__name__,
            funname=request.function.__name__ if request.function else "",
            now=datetime.now().isoformat(),
        )
        filepath = os.path.join(_get_screenshots_dir(), filename)
        driver.get_screenshot_as_file(filepath)
        print("Screenshot of failing test:")
        if os.environ.get("E2E_OUTPUT") == "base64":
            print(SCREENSHOT_SCRIPT.format(data=driver.get_screenshot_as_base64()))
        else:
            print(filepath)


def _get_screenshots_dir():
    """Create the screenshots directory."""
    directory = ".e2e_screenshots"
    if not os.path.exists(directory):
        os.makedirs(directory)
    return directory


@pytest.yield_fixture(scope="module")
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
            from invenio_files_rest.models import Bucket, Location, ObjectVersion

            location_obj = Location.get_default() or location
        bucket_obj = Bucket.create(location_obj)
        for file_name in os.listdir(source_dir):
            full_file_path = os.path.join(source_dir, file_name)
            if os.path.isdir(full_file_path):
                continue
            file_obj = open(full_file_path, "rb")
            ObjectVersion.create(bucket_obj, key=file_name, stream=file_obj)
        db.session.commit()
        return bucket_obj

    return create_bucket_from_dir


class MockImportlibDistribution(importlib.metadata.Distribution):
    """A mocked distribution where we can inject entry points."""

    def __init__(self, extra_entry_points):
        """Entry points for the distribution."""
        self._entry_points = extra_entry_points

    @property
    def name(self):
        """Return the 'Name' metadata for the distribution package."""
        return "MockDistribution"

    @property
    def entry_points(self):
        """Iterate over entry points."""
        for group, eps_lines in self._entry_points.items():
            for ep_line in eps_lines:
                name, value = ep_line.split("=", maxsplit=1)
                yield importlib.metadata.EntryPoint(
                    # strip possible white space due to split on "="
                    name=name.strip(),
                    value=value.strip(),
                    group=group,
                )

    def read_text(self, *args, **kwargs):
        """Implement abstract method."""

    def locate_file(self, *args, **kwargs):
        """Implement abstract method."""


if python_minor < 10:

    class MockImportlibLegacyDistribution(importlib_metadata.Distribution):
        """A mocked distribution where we can inject entry points."""

        def __init__(self, extra_entry_points):
            """Entry points for the distribution."""
            self._entry_points = extra_entry_points

        @property
        def name(self):
            """Return the 'Name' metadata for the distribution package."""
            return "MockDistribution"

        @property
        def entry_points(self):
            """Iterate over entry points."""
            for group, eps_lines in self._entry_points.items():
                for ep_line in eps_lines:
                    name, value = ep_line.split("=", maxsplit=1)
                    yield importlib_metadata.EntryPoint(
                        # strip possible white space due to split on "="
                        name=name.strip(),
                        value=value.strip(),
                        group=group,
                    )

        def read_text(self, *args, **kwargs):
            """Implement abstract method."""

        def locate_file(self, *args, **kwargs):
            """Implement abstract method."""


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
    importlib_dist = MockImportlibDistribution(extra_entry_points)
    if python_minor < 10:
        importlib_legacy_dist = MockImportlibLegacyDistribution(extra_entry_points)

    #
    # Patch importlib
    #
    old_distributions = importlib.metadata.distributions
    if python_minor < 10:
        old_legacy_distributions = importlib_metadata.distributions

    def distributions(**kwargs):
        for dist in old_distributions(**kwargs):
            yield dist
        yield importlib_dist

    if python_minor < 10:

        def distributions_legacy(**kwargs):
            for dist in old_legacy_distributions(**kwargs):
                yield dist
                yield importlib_legacy_dist

    importlib.metadata.distributions = distributions
    if python_minor < 10:
        importlib_metadata.distributions = distributions_legacy

    yield

    importlib.metadata.distributions = old_distributions
    if python_minor < 10:
        importlib_metadata.distributions = old_legacy_distributions


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


@pytest.fixture(scope="session")
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


@pytest.fixture(scope="function")
def set_app_config_fn_scoped(base_app):
    """Fixture to temporarily set app config values.

    Oftentimes, tests set application configuration values but don't first
    save the original value (if any) and restore them
    after the test concluded (if any prior). This causes test leakage because
    base_app (the Flask application) is a module scoped fixture.
    This fixture provides a function to call to temporarily set config
    values automatically: without further intervention, it resets them to their
    original values after the test is done.

    Scope: function

    .. code-block:: python

        def test_with_tmp_config(app, set_app_config_fn_scoped):
            set_app_config_fn_scoped({
                "MAX_CONTENT_LENGTH": 2**20,
                "SECRET_KEY": "foo"
            })
            # app.config will contain MAX_CONTENT_LENGTH = 2**20 and
            # SECRET_KEY = "foo" .
            # No other call is needed to revert values.
            # Other tests will see the original values for these configs.
    """
    config_prev = {}

    def _set_tmp_config(config):
        for key, value in config.items():
            key_present = key in base_app.config
            config_prev[key] = (key_present, base_app.config.get(key, None))
            base_app.config[key] = value

    yield _set_tmp_config

    for key, (key_present, value) in config_prev.items():
        if key_present:
            base_app.config[key] = value
        else:
            # in case the key was deleted during the test - to be super clean
            base_app.config.pop(key, None)
