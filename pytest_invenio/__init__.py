# -*- coding: utf-8 -*-
#
# This file is part of pytest-invenio.
# Copyright (C) 2017-2025 CERN.
# Copyright (C) 2024-2026 Graz University of Technology.
#
# pytest-invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Pytest fixtures for Invenio.

.. _quick-start:

Quick start
-----------
1. Define a module-scoped fixture named ``create_app`` that returns an
   application factory for your Invenio installation. If you are using
   Invenio-App, it's as simple as:

   .. code-block:: python

       # conftest.py
       from invenio_app.factory import create_ui

       @pytest.fixture(scope='module')
       def create_app():
           return create_ui


2. Write tests:

   .. code-block:: python

       # test_something.py

       def test_e2e(live_server, browser):
           browser.get(url_for('index', _external=True))

       def test_testclient(client):
           res = client.get('/api/')
           res.json == {'test-client': 'with-json-decoder'}

       def test_db(base_app, db):
           # Database with rollback

       def test_cli(cli_runner):
           result = cli_runner(mycmd)
           assert result.exit_code == 0

       def test_mailbox(appctx, mailbox):
           # ...
           assert len(mailbox) == 1

Running tests
-------------
Running tests with py.test is pretty simple. Your package might support the
standard way of running tests:

.. code-block:: console

    $ python setup.py test

Alternatively you can use the ``pytest`` command to run all or specific test
cases:

.. code-block:: console

    $ pytest
    $ pytest tests/test_something.py
    $ pytest tests/test_something.py::test_acase

Fixtures
--------
All available fixtures are documented in the API documentation
(see :ref:`fixtures`).

In addition to the ones provided by pytest-invenio, there are further fixtures
defined pytest-flask (see
`documentation <http://pytest-flask.readthedocs.io/en/latest/>`_ for details).

Structuring tests
-----------------
The pytest fixtures in pytest-invenio all work on *one* Flask application,
however most Invenio instances usually consits of *two* Flask applications:
UI and API. Thus, to use the pytest-invenio fixtures it's important to
understand how to structure your tests, and know exactly which application you
are dealing with.

Scope
~~~~~
Most of pytest-invenio fixtures are either *module* scoped or *function*
scoped.

* *Module* scoped fixtures are created/destroyed once per Python test file.
* *Function* scoped fixtures are created/destroyed per test.

The fixtures which creates the database and applications are module scoped,
hence, all tests in a Python file run against either the UI or the API
application, but not both.

.. note::

    All tests in a single file, run against the one and only one application
    (e.g. UI or REST).

Thus, in a single test file you cannot mix both UI and API tests, which is
normally not an issue.

Overriding fixtures
~~~~~~~~~~~~~~~~~~~
Pytest provides rich support for overriding fixtures at various level and
combined with module/function-scoped we can easily override fixtures. Also,
you can use ``conftest.py`` to define per-directory fixtures.

Following is an example of how fixtures overriding works:

.. code-block:: python

    # conftest.py:
    @pytest.fixture()
    def myfix():
        return 'root'

    # test_root.py
    def test_a(myfix):
        print(myfix)
        # will output "root"

    # a/conftest.py
    @pytest.fixture()
    def myfix(myfix):
        return myfix + '-a'

    # a/test_subdir.py
    def test_a(myfix):
        print(myfix)
        # will output "root-a"

Notice that:

* **Overriding:** In ``a/test_subdir.py`` the fixture ``myfix`` is coming from
  ``a/conftest.py`` which is overriding the fixture from ``conftest.py``. In
  ``test_root.py`` it's however the ``myfix`` fixture from ``conftest.py``
  being used.
* **Parent fixture:** In ``a/conftest.py``, the fixture ``myfix`` has access to
  the parent fixture from ``conftest.py``.

Recommend layout
~~~~~~~~~~~~~~~~
If you are using Invenio-App (recommended), then the following layout is
recommended:

.. code-block:: python

    # ### tests/conftest.py ###
    # Common application configuration goes here
    @pytest.fixture(scope='module')
    def app_config(app_config):
        app_config['MYCONF'] = True
        return app_config

    # ### tests/ui/conftest.py ###
    # UI tests goes in tests/ui/ folder.
    from invenio_app.factory import create_ui

    @pytest.fixture(scope='module')
    def create_app():
        return create_ui

    # ### tests/api/confest.py ###
    # API tests goes in tests/api/ folder.
    from invenio_app.factory import create_api

    @pytest.fixture(scope='module')
    def create_app():
        return create_api

    # ### tests/e2e/conftest.py ###
    # E2E tests (requring both UI/API) goes in tests/e2e/ folder.
    from invenio_app.factory import create_app as create_ui_api

    @pytest.fixture(scope='module')
    def create_app():
        return create_ui_api

Using above layout you essentially split your tests into three folders::

    tests/ui/
    tests/api/
    tests/e2e/

Each subfolder holds tests related to a specific application (UI or API).
The ``e2e`` folder holds tests that need both UI and API application (which
is typically the case for end-to-end tests). The E2E tests works by creating
both the UI and API applications and using a special WSGI middleware to
dispatch requests between both applications. Having two applications at the
same time, can however cause quite a lot of confusion so it is only recommended
for E2E tests.

Note, also in above example how all three applications are sharing the same
:py:data:`~fixtures.app_config` fixture.

.. note::

    You shouldn't feel bound to above structure. If you site grows large,
    you'll likely split tests into further subfolders. The important message
    from the recommended layout, is that you need **one folder per
    application**.

Application fixtures
--------------------
The package provides three different application fixtures:

* :py:data:`~fixtures.base_app`: Basic application fixture which creates the
  Flask application.
* :py:data:`~fixtures.appctx`: Same as the basic application fixture, but
  pushes an application context onto the stack (i.e. makes ``current_app``
  work).
* :py:data:`~fixtures.app`: Same as the basic application, but in addition it
  initializes the database and search indices.

All three fixtures depend on the same user-provided (i.e. you must define it)
fixture named ``create_app`` which must return an application factory (see
:ref:`quick-start`).

Customizing configuration
~~~~~~~~~~~~~~~~~~~~~~~~~
The application fixtures rely on fixtures such as
:py:data:`~fixtures.instance_path`, :py:data:`~fixtures.app_config`,
:py:data:`~fixtures.celery_config_ext`, :py:data:`~fixtures.db_uri`,
:py:data:`~fixtures.broker_uri` to inject configuration into the
application.

You can overwrite each of these fixtures at many different levels:

* **Global**: Override one or more of these fixtures in your global
  ``conftest.py`` to inject the same configuration in all applications.
* **Per-directory**: Override fixtures for a specific subdirectory by putting a
  ``conftest.py`` in the directory.
* **Per-file**: Fixtures can also be overwritten in specific modules. For
  instance you may want to customize the celery configuration only for a
  specific Python test file.

Injecting entry points
~~~~~~~~~~~~~~~~~~~~~~
Invenio relies heavily upon entry points for constructing a Flask application,
and it can be rather cumbersome to try to manually register database models,
mappings and other features afterwards.

You can therefore inject extra entry points if needed during testing via the
:py:data:`~fixtures.extra_entry_points` fixture and use it in your custom
``create_app()`` fixture:

.. code-block:: python

    @pytest.fixture(scope="module")
    def extra_entry_points():
        return {
            'invenio_db.models': [
                'mock_module = mock_module.models',
            ]
        }

    @pytest.fixture(scope="module")
    def create_app(entry_points):
        return _create_api

Note that ``create_app()`` depends on the :py:data:`~fixtures.entry_points`
fixture not the ``extra_entry_points()``.

.. _views-testing:

Views testing
-------------
Views can easily be testing using the Flask test clients. Two test clients are
provided for convenience: ``base_client`` and ``client``. The only difference
is which application fixture they depend on:

.. code-block:: python

    def test_view1(base_client):
        # Depends on 'base_app' fixture
        base_client.get(url_for(..))

    def test_view2(client):
        # Depends on 'app' fixture
        client.get(url_for(..))

JSON responses
~~~~~~~~~~~~~~
The default Flask test client does not have built-in support for decoding JSON
responses, which can make API testing a bit cumbersome. The test clients
are therefore patched to add a JSON property:

.. code-block:: python

    def test_api(base_client):
        res = base_client.get(...)
        assert res.json == { ... }

Database re-use
---------------
The default database is an SQLite database located in the application's
instance folder. This can easily be overwritten by setting the environment
variable ``SQLALCHEMY_DATABASE_URI`` (useful e.g. in CI systems to test
multiple databases).

Tests that make changes to the database should explicitly use the function
scoped :py:data:`~fixtures.db` fixture. This fixture wraps the changes in
a transaction and rollback any changes by the end of the test. For instance:

.. code-block:: python

    def test_db1(db):
        db.session.add(User(username='alice'))
        db.session.commit()
        assert User.query.count() == 1 # i.e. independent of test_db2

    def test_db2(db):
        db.session.add(User(username='bob'))
        db.session.commit()
        assert User.query.count() == 1  # i.e. independent of test_db1


.. note::

    Take care! The :py:data:`~fixtures.db` fixture does not rollback other
    changes. If data, in addition to being added to the database, is also
    indexed in the search cluster then you should clear the index explicitly using
    e.g. :py:data:`~fixtures.search_clear`.

Performance considerations
~~~~~~~~~~~~~~~~~~~~~~~~~~
The database is recreated (all tables dropped and recreated) for each test
file, because the database is a module scoped fixture. This adds a performance
overhead, thus be careful not to indirectly depend on the database fixtures in
a file unless it is really necessary (e.g. via the :py:data:`~fixtures.app`
fixture).

Search testing
---------------------
Pytest-Invenio depends on Invenio-Search and any mappings registered on
Invenio-Search will be created if you depend on the :py:data:`~fixtures.search`
fixture. The fixture is module scoped, meaning that any fixture you write to
e.g. load test data should likely also be module scoped.

Clearing changes
~~~~~~~~~~~~~~~~
Unlike the database fixture, which automatically rollback changes, you must
explicitly depend on the :py:data:`~fixtures.search_clear` fixture if you makes
changes to the indexes. This ensures that you leave the indexes in a clean
state for the next test. The :py:data:`~fixtures.search_clear` fixture will however
delete and recreate the indexes, and thus comes with a performance penalty if
used.

.. code-block:: python

    def test_search1(search_clear):
        # ...

Performance considerations
~~~~~~~~~~~~~~~~~~~~~~~~~~
As for the database fixtures, search indices are deleted and recreated
for each test file (due to module scoped fixture). Thus be careful not to
indirectly depend on the database fixtures in a file unless it is really
necessary (e.g. via the :py:data:`~fixtures.app` fixture).

CLI testing
-----------
Pytest-Invenio provides two quick short cuts for easier testing Click-based
commands that require an application context (i.e. most commands).

The shortest version is to use the :py:data:`~fixtures.cli_runner` fixture:

.. code-block:: python

    def test_cmd(cli_runner):
        result = cli_runner(mycmd)
        assert result.exit_code == 0

The downside is that the Click CLIRunner is recreated for each call. This is
not necessary, so an alternative is to use the :py:data:`~fixtures.script_info`
fixture, which however is more verbose:

.. code-block:: python

    def test_cmd(script_info):
        runner = CliRunner()
        result = runner.invoke(mycmd, obj=script_info)
        assert result.exit_code == 0

Mail testing
------------
If you have Invenio-Mail installed on your application, you can use the
:py:data:`~fixtures.mailbox` fixture to test email sending. Any message sent
by the application during the test will be captured and is inspectable in via
the fixture:

.. code-block:: python

    def test_mailbox(appctx, mailbox):
        assert len(mailbox) == 0
        appctx.extensions['mail'].send_message(
            sender='no-reply@localhost',
            subject='testing',
            body='test',
            recipients=['no-reply@localhost'],)
        assert len(mailbox) == 1


End-to-end testing
------------------
In addition to using the Flask test client for testing views (see
:ref:`views-testing`), you can use a real browser via the Selenium integration
for fully end-to-end testing. The tests works by starting the Flask application
in a separate process, and using Selenium to drive your favorite browser.
Writing the tests are very easy, simply depend on the ``live_server`` fixture
(defined by pytest-flask) and the :py:data:`~fixtures.browser` fixture:

.. code-block:: python

    def test_browser(live_server, browser):
        # Note the use of '_external=True'
        browser.get(url_for('index', _external=True))

Running E2E tests
~~~~~~~~~~~~~~~~~
By default, tests using the :py:data:`~fixtures.browser` fixture are skipped.
In order to run these tests, you must set an environment variable:

.. code-block:: console

    $ export E2E=yes

Also, by default Chrome is used. If you'd like to use Firefox, Safari or
another browser you must set another environment variable:

.. code-block:: console

    $ export E2E_WEBDRIVER_BROWSERS="Firefox"

.. note::

    You must have Selenium Client and the Chrome Webdriver installed on your
    system in order to run the E2E tests.


Screenshots
~~~~~~~~~~~
The :py:data:`~fixtures.browser` fixture will take a screenshot of in case of
test failures and store it in a folder ``.e2e_screenshots``. On CI systems you
can also have screenshot printed to the console by setting an environment
variable:

.. code-block:: console

    $ export E2E_OUTPUT=base64

TravisCI integration
~~~~~~~~~~~~~~~~~~~~
Following is an example of the needed changes (at time of writing) to your
``.travis.yml`` in case want to run E2E tests on Travis. Travis is likely
to evolve, so please refer to the Travis CI documentation for the latest
information.

.. code-block:: yaml

    # Install Chrome
    # - see https://docs.travis-ci.com/user/chrome
    addons:
      chrome: stable

    # Chrome driver fails if not trusty dist
    dist: trusty

    # Selenium webdriver for Chrome fails if not on sudo
    # - see https://github.com/travis-ci/travis-ci/issues/8836
    sudo: true

    # Define environment variables to enable E2E tests and outputing
    # screenshots to the console.
    env:
      global:
        # Print screenshots to console output
        - E2E_OUTPUT=base64
        # Enable end-to-end tests
        - E2E=yes

    # Install Chrome webdriver for Selenium
    before_install:
      - "PATH=$PATH:$HOME/webdrivers"
      - "if [ ! -f $HOME/webdrivers/chromedriver ]; then wget https://chromedriver.storage.googleapis.com/2.31/chromedriver_linux64.zip -P   $HOME/webdrivers; unzip -d $HOME/webdrivers $HOME/webdrivers/chromedriver_linux64.zip; fi"  # noqa

    # Start a virtual display
    # - https://docs.travis-ci.com/user/gui-and-headless-browsers/
    before_script:
      - "export DISPLAY=:99.0"
      - "sh -e /etc/init.d/xvfb start"
      - sleep 3 # give xvfb some time to start
"""

__version__ = "4.0.0"

__all__ = ("__version__",)
