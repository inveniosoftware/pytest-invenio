..
    This file is part of pytest-invenio.
    Copyright (C) 2018-2024 CERN.
    Copyright (C) 2024-2026 Graz University of Technology.

    pytest-invenio is free software; you can redistribute it and/or modify it
    under the terms of the MIT License; see LICENSE file for more details.

Changes
=======

Version v4.0.0 (released 2026-01-27)

- fix: use now instead of utcnow
- fix: replace SQLAlchemy pool with NullPool

Version v3.4.2 (released 2025-07-09)

- fix: use importlib_metadata <python3.10

Version v3.4.1 (released 2025-07-01)

- fix: importlib_metadata legacy

Version v3.4.0 (released 2025-06-27)

- fix: pkg_resources DeprecationWarning

Version v3.3.1 (released 2025-05-08)

- installation: pin snowballstemmer to <3.x
    * ``snowballstemmer`` is dependency of the deprecated/unmaintained
      ``pydocstyle`` module. The v3.0.0 release of ``snowballstemmer``
      introduces a breaking change.

Version v3.3.0 (released 2025-04-02)

- fixtures: add set_app_config_fn_scoped

Version v3.2.0 (released 2025-03-30)

- user: add `base_url` parameter for user auth client calls
    * Adds a `base_url` parameter to the UserFixtureBase constructor. This
      allows to make sure that auth calls like login and logout are
      explicitly associated with the correct domain when needed. This is
      avoid cookie domain inconsistencies intorduced by Flask v3 and
      Werkzeug's v2.3 new default behavior for cookie management in the test
      client.

Version v3.1.0 (released 2025-03-07)

- fixtures: add fixture for ``cache_uri``

Version 3.0.0 (released 2024-12-02)

- setup: remove pytest pin
- global: add compatibility to sqlalchemy >= 2.0
- fixtures: apply new sqlalchemy session rollback handling

Version 2.2.1 (released 2024-06-27)

- installation: pin importlib-metadata ``<8.0.0``

Version 2.2.0 (released 2024-02-28)

- setup: bump coverage package
- installation: add GitHub action annotations

Version 2.1.7 (released 2024-01-29)

- fixtures: use unlogged tables for PostgreSQL

Version 2.1.6 (released 2023-10-31)

- Add ``db_session_options`` fixture.

Version 2.1.5 (released 2023-10-02)

- installation: pin Flask ``<2.3.0``.

Version 2.1.4 (released 2023-06-02)

- user fixture: use identity ID as int

Version 2.1.3 (released 2023-04-13)

- yanked, because of an incompatibility with Flask-SQLAlchemy v3.

Version 2.1.2 (released 2023-03-20)

- disable request rate-limiting

Version 2.1.1 (released 2022-10-25)

- pin pytest version

Version 1.4.15 (released 2022-10-04)

- Pin docker-services-cli<0.5.0, which drops Elasticsearch v6.

Version 1.4.14 (yanked)

Version 2.1.0 (released 2022-10-03)

- Adds support for OpenSearch v2

Version 2.0.0 (released 2022-09-23)

- Use invenio-search v2 and replaces Elasticsearch with OpenSearch, including
  fixture names.
- Deprecate previous fixtures named with `es` prefix.
- Remove upper pin of pytest.

Version 1.4.13 (released 2022-08-09)

- Fix pycodestyle dependency

Version 1.4.12 (released 2022-08-08)

- Fix flask-login dependency

Version 1.4.11 (released 2022-05-05)

- Upper pin Selenium dependency, v4 drops support for Python 3.7.

Version 1.4.10 (released 2022-05-04)

- Fixes an issue with the user id in the UserFixture being None before the
  db session is flushed.

Version 1.4.9 (released 2022-05-02)

- Mark users as changed and commit through datastore (outside of context
  manager).

Version 1.4.8 (yanked 2022-05-02 due to UserFixture session close issues)

- Commit users through the datastore in the UserFixture.

Version 1.4.7 (released 2022-04-04)

- Adds support for Flask v2.1

Version 1.4.6 (released 2022-02-29)

- Adds support for Invenio-Accounts 2.0 in the UserFixture.

Version 1.4.5 (released 2022-02-23)

- Fixes an import so that pytest-invenio is now usable without
  Invenio-Accounts installed.

Version 1.4.4 (released 2022-02-21)

- Adds new UserFixture for easier test user creation.

Version 1.4.3 (released 2022-02-18)

- Adds support for using importlib_metadata to read the patched entry points.

Version 1.4.2 (released 2021-05-11)

- Add APP_THEME and THEME_ICONS in default app config, often needed when testing
  invenio packages that will render templates.

Version 1.4.1 (released 2020-12-17)

- Remove pytest-celery because it's still an alpha release.

Version 1.4.0 (released 2020-09-16)

- BACKWARD INCOMPATIBLE: Changes to use isort, pycodestyle and pydocstyle via
  pytest plugins. You need to update `pytest.ini` and remove the ``--pep8``
  from the addopts and instead add ``--isort --pydocstyle --pycodestyle``:

  .. code-block:: ini

      addopts = --isort --pydocstyle --pycodestyle ...

  In `./run-tests.sh` script you should also remove calls to pydocstyle and
  isort as both are now integrated with pytest.

- BACKWARD INCOMPATIBLE: Upgrade dependencies: coverage, pytest-flask,
  check-manifest, pytest. You need to set the pytest-flask live server
  fixture scope in your pytest config:

  .. code-block:: ini

     [pytest]
     live_server_scope = function

- Decommission pytest-pep8 (last release in 2014) in favour of pycodestyle.

Version 1.3.4 (released 2020-09-15)

- Add `entrypoints` fixture to allow injecting extra entry points during
  testing so that you avoid manual registration of e.g. mappings and schemas.

Version 1.3.3 (released 2020-08-27)

- Add `docker-services-cli` as dependency to enable Invenio modules to
  perform reproducible tests.

Version 1.3.2 (released 2020-05-19)

- Move check-manifest, coverage, isort, pydocstyle, pytest-flask and
  pytest-pep8 from test to install requirements to provide them as centrally
  managed dependencies.

Version 1.3.1 (released 2020-05-12)

- Uninstalls numpy in Travis due to incompatibilities with
  elasticsearch-py.

Version 1.3.0 (released 2020-03-19)

- Removes support for Python 2.7.

Version 1.2.2 (released 2020-05-07)

- Uninstalls numpy in Travis due to incompatibilities with
  elasticsearch-py.
- Deprecated Python versions lower than 3.6.0. Now supporting 3.6.0.
- Set maximum version of Werkzeug to 1.0.0 due to incompatible imports.
- Set maximum version of Flask to 1.1.0 due to incompatible imports.
- Set maximum version of Pytest-Flask to 1.0.0 due to breaking changes.
- Set minimum version of Invenio-Search to 1.2.3 and maximum to 1.3.0.

Version 1.2.1 (released 2019-11-13)

- Fixes instance path fixture to also set the static folder.

Version 1.2.0 (released 2019-07-31)

- Adds fixture for creating default Location.
- Adds fixture for creating Bucket from directory with files.

Version 1.1.1 (released 2019-05-21)

- Adds pytest-cov as install dependency.

Version 1.1.0 (released 2019-02-15)

- Changes name of fixture from celery_config to celery_config_ext due to
  unreliable overwriting of celery_config fixture name.

Version 1.0.6 (released 2018-12-03)

- Fixes overwriting of celery_config fixture

Version 1.0.5 (released 2018-10-08)

- Adds default Content Security Policy header to the app configuration.
- Fixes issue with default tests scope.

Version 1.0.4 (released 2018-08-14)

- Bumps pytest minimun version to 3.8.0.

Version 1.0.3 (released 2018-09-05)

- Moves module dependent imports inside the fixture functions in order to
  decouple dependencies for Invenio apps or modules that might not be using
  them.

Version 1.0.2 (released 2018-05-25)

Version 1.0.1 (released 2018-04-17)

Version 1.0.0 (released 2018-03-22)
