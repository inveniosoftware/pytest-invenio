================
 pytest-invenio
================

.. image:: https://img.shields.io/travis/inveniosoftware/pytest-invenio.svg
        :target: https://travis-ci.org/inveniosoftware/pytest-invenio

.. image:: https://img.shields.io/coveralls/inveniosoftware/pytest-invenio.svg
        :target: https://coveralls.io/r/inveniosoftware/pytest-invenio

.. image:: https://img.shields.io/github/tag/inveniosoftware/pytest-invenio.svg
        :target: https://github.com/inveniosoftware/pytest-invenio/releases

.. image:: https://img.shields.io/pypi/dm/pytest-invenio.svg
        :target: https://pypi.python.org/pypi/pytest-invenio

.. image:: https://img.shields.io/github/license/inveniosoftware/pytest-invenio.svg
        :target: https://github.com/inveniosoftware/pytest-invenio/blob/master/LICENSE

Pytest fixtures for Invenio.

The package offers a number of features to help test Invenio based
applications:

- Less boilerplate: Using the fixtures you can keep your ``conftest.py`` short
  and focused.
- Database re-use: database tests are running inside a transaction which is
  rolled back after the test.
- End-to-end testing: Selenium tests can easily be switched on/off, and in case
  of test failures a screenshot is taken (with possibility to output in the
  console in base64-encoding - useful on e.g. TravisCI).
- Application configuration for testing (e.g. disable CSRF protection in forms
  and HTTPS requirement).
- JSON decoding support in Flask test client for easier API testing.
- Batteries included: further fixtures help with e.g. mail sending and CLI
  tests.

Further documentation is available on https://pytest-invenio.readthedocs.io/.
