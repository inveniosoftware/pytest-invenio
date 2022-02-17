# -*- coding: utf-8 -*-
#
# This file is part of pytest-invenio.
# Copyright (C) 2017-2018 CERN.
#
# pytest-invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Module tests."""

import json
import os

import pytest


def test_version():
    """Test version import."""
    from pytest_invenio import __version__
    assert __version__


def test_instance_path(testdir):
    """Test instance path."""
    assert 'INVENIO_INSTANCE_PATH' not in os.environ
    testdir.makepyfile("""
        import os
        def test_instance_path(instance_path):
            assert os.environ['INVENIO_INSTANCE_PATH'] == instance_path
            assert os.path.exists(instance_path)
            assert os.path.isdir(instance_path)
    """)
    testdir.runpytest().assert_outcomes(passed=1)
    assert 'INVENIO_INSTANCE_PATH' not in os.environ


def test_db_uri(testdir):
    """Test default db uri."""
    testdir.makepyfile("""
        import os
        def test_db_uri(db_uri, instance_path):
            assert 'SQLALCHEMY_DATABASE_URI' not in os.environ
            assert db_uri.startswith('sqlite:///{}'.format(instance_path))
    """)
    testdir.runpytest().assert_outcomes(passed=1)


def test_db_uri_env(testdir, monkeypatch):
    """Test db uri defined in environment variable."""
    monkeypatch.setenv('SQLALCHEMY_DATABASE_URI', 'sqlite://')
    testdir.makepyfile("""
        def test_db_uri(db_uri):
            assert db_uri == 'sqlite://'
    """)
    testdir.runpytest().assert_outcomes(passed=1)
    monkeypatch.undo()


def test_broker_uri(testdir):
    """Test default broker uri."""
    testdir.makepyfile("""
        import os
        def test_broker_uri(broker_uri):
            assert 'BROKER_URL' not in os.environ
            assert broker_uri == 'amqp://guest:guest@localhost:5672//'
    """)
    testdir.runpytest().assert_outcomes(passed=1)


def test_broker_uri_env(testdir, monkeypatch):
    """Test default broker uri."""
    monkeypatch.setenv('BROKER_URL', 'env-value')
    testdir.makepyfile("""
        def test_broker_uri(broker_uri):
            assert broker_uri == 'env-value'
    """)
    testdir.runpytest().assert_outcomes(passed=1)
    monkeypatch.undo()


def test_app_config(testdir):
    """Test application and celery config."""
    testdir.makepyfile(test_app="""
        def test_app_config(app_config, db_uri, broker_uri):
            assert app_config['SQLALCHEMY_DATABASE_URI'] == db_uri
            assert app_config['BROKER_URL'] == broker_uri
            assert app_config['SECRET_KEY'] == 'test-secret-key'
            assert app_config['CELERY_TASK_ALWAYS_EAGER'] == True
    """)
    # Test that application fixture can be overwritten in each module.
    testdir.makepyfile(test_app_overwrite="""
        import pytest

        @pytest.fixture()
        def app_config(app_config):
            app_config.update({
                'MYSTUFF': True
            })
            return app_config

        def test_app_config(app_config, db_uri, broker_uri):
            assert app_config['SQLALCHEMY_DATABASE_URI'] == db_uri
            assert app_config['MYSTUFF']
    """)
    testdir.runpytest().assert_outcomes(passed=2)


def test_base_app(conftest_testdir):
    """Test application factories."""
    # `conftest_testdir` defines a create_app fixture which are used by
    # base_app fixture to create a Flask application and inject the
    # configuration into the application.
    conftest_testdir.makepyfile("""
        def test_base_app(base_app, db_uri):
            assert base_app.config['SQLALCHEMY_DATABASE_URI'] == db_uri
    """)
    conftest_testdir.runpytest().assert_outcomes(passed=1)


def test_base_client_jsonresponse(conftest_testdir):
    """Test the test client and json attribute on response object."""
    conftest_testdir.makepyfile("""
        def test_base_app(base_app, base_client):
            res = base_client.get('/api/')
            res.json == {'app_name': base_app.name}
    """)
    conftest_testdir.runpytest().assert_outcomes(passed=1)


def test_appctx(conftest_testdir):
    """Test application factories."""
    conftest_testdir.makepyfile("""
        from flask import current_app

        def test_appctx(base_app, appctx):
            assert base_app.name == current_app.name
    """)
    conftest_testdir.runpytest().assert_outcomes(passed=1)


def test_script_info(conftest_testdir):
    """Test script info command."""
    conftest_testdir.makepyfile("""
        import click
        from click.testing import CliRunner
        from flask import current_app
        from flask.cli import with_appcontext

        # Define a command which requires app context
        @click.command()
        @with_appcontext
        def mycmd():
            click.echo(current_app.name)

        # Run test on just defined CLI command.
        def test_cli(script_info, base_app):
            runner = CliRunner()
            result = runner.invoke(mycmd, obj=script_info)
            assert result.exit_code == 0
            assert result.output.startswith(base_app.name)
    """)
    conftest_testdir.runpytest().assert_outcomes(passed=1)


def test_clirunner(conftest_testdir):
    """Test script info command."""
    conftest_testdir.makepyfile("""
        import click
        from flask import current_app
        from flask.cli import with_appcontext

        # Define a command which requires app context
        @click.command()
        @with_appcontext
        def mycmd():
            click.echo(current_app.name)

        # Run test on just defined CLI command.
        def test_cli(cli_runner):
            assert cli_runner(mycmd).exit_code == 0
    """)
    conftest_testdir.runpytest().assert_outcomes(passed=1)


def test_clirunner_output(conftest_testdir):
    """Test script info command."""
    conftest_testdir.makepyfile("""
        import click
        from flask import current_app
        from flask.cli import with_appcontext

        # Define a command which logs to the application logger
        @click.command()
        @with_appcontext
        def mycmd():
            current_app.logger.error('My error')

        # Run test that output is captured
        def test_cli(cli_runner):
            res = cli_runner(mycmd)
            assert 'My error' in res.output
    """)
    conftest_testdir.runpytest().assert_outcomes(passed=1)


def test_es(conftest_testdir):
    """Test Elasticsearch initialization."""
    conftest_testdir.makepyfile("""
        def test_es(es):
            assert es.ping()
    """)
    conftest_testdir.runpytest().assert_outcomes(passed=1)


def test_es_clear(conftest_testdir):
    """Test Elasticsearch clearing."""
    # Create an Elasticsearch mapping for Invenio-Search
    conftest_testdir.mkpydir('data')
    conftest_testdir.mkpydir('data/v7')
    conftest_testdir.mkdir('data/v7/demo')
    with open('data/v7/demo/default-v1.0.0.json', 'w') as fp:
        fp.write(json.dumps({"mappings": {"properties": {
            "title": {"type": "text", "fielddata": True}}}}))
    # Create test
    conftest_testdir.makepyfile("""
        import pytest
        from elasticsearch.exceptions import NotFoundError
        from invenio_search import current_search_client, current_search

        # Just a UUID
        doc_id = 'deadbeef-dae9-4c19-9b7c-49056374bc6c'

        @pytest.fixture(scope='module')
        def base_app(base_app):
            # Registers the Elasticsearch mapping on the application
            search = base_app.extensions['invenio-search']
            search.register_mappings('demo', 'data')
            return base_app

        def test_es1(es, es_clear):
            # Index a document
            current_search_client.index(
                index='demo-default-v1.0.0',
                id=doc_id,
                body={'title': 'Test'},
                op_type='create',
                doc_type='_doc',
            )
            # Wait for document to be available
            current_search.flush_and_refresh('demo-default-v1.0.0')
            # Get the document (will raise exception if not found)
            current_search_client.get(
                index='demo-default-v1.0.0',
                id=doc_id,
                doc_type='_doc',
            )

        def test_es2(es):
            # Get the document create in test above (should not be possible)
            pytest.raises(
                NotFoundError,
                current_search_client.get,
                index='demo-default-v1.0.0',
                id=doc_id,
                doc_type='_doc',
            )
            # But the index should exist
            assert current_search_client.indices.exists(
                index='demo-default-v1.0.0')
    """)
    conftest_testdir.runpytest().assert_outcomes(passed=2)


def test_database(conftest_testdir):
    """Test database creation and initialization."""
    conftest_testdir.makepyfile("""
        def test_database(database, db_uri):
            assert str(database.engine.url) == db_uri
    """)
    conftest_testdir.runpytest().assert_outcomes(passed=1)


def test_db(conftest_testdir):
    """Test database creation and initialization."""
    conftest_testdir.makepyfile("""
        from invenio_db import db

        class User(db.Model):
            id = db.Column(db.Integer, primary_key=True)
            username = db.Column(db.String(80), unique=True)

        def test_db1(db):
            assert User.query.count() == 0
            db.session.add(User(username='alice'))
            db.session.commit()
            assert User.query.count() == 1

        def test_db2(db):
            assert User.query.count() == 0
            db.session.add(User(username='alice'))
            db.session.add(User(username='bob'))
            db.session.commit()
            assert User.query.count() == 2
    """)
    conftest_testdir.runpytest().assert_outcomes(passed=2)


def test_app(conftest_testdir):
    """Test database creation and initialization."""
    conftest_testdir.makepyfile("""
        from invenio_db import db
        from invenio_search import current_search_client

        class Place(db.Model):
            id = db.Column(db.Integer, primary_key=True)

        def test_app(app):
            assert Place.query.count() == 0
            assert current_search_client.ping()
    """)
    conftest_testdir.runpytest().assert_outcomes(passed=1)


def test_mailbox(conftest_testdir):
    """Test database creation and initialization."""
    conftest_testdir.makepyfile(test_mailbox="""
        def test_mailbox(appctx, mailbox):
            assert len(mailbox) == 0
            appctx.extensions['mail'].send_message(
                sender='no-reply@localhost',
                subject='testing',
                body='test',
                recipients=['no-reply@localhost'],)
            assert len(mailbox) == 1
    """)
    # Test what happens if Invenio-Mail is not installed.
    conftest_testdir.makepyfile(test_mailbox_fail="""
        import pytest

        @pytest.fixture(scope='module')
        def base_app(base_app):
            del base_app.extensions['mail']
            return base_app

        def test_mailbox(appctx, mailbox):
            pass  # Will never reach here.
    """)
    conftest_testdir.runpytest().assert_outcomes(passed=1, errors=1)


def test_browser_skipped(conftest_testdir):
    """Test that end-to-end tests are skipped unless E2E env var is set."""
    conftest_testdir.makepyfile("""
        def test_browser(live_server, browser):
            browser.get(url_for('index', _external=True))
    """)
    conftest_testdir.runpytest().assert_outcomes(skipped=1)


def test_browser(conftest_testdir, monkeypatch):
    """Test live server and selenium."""
    monkeypatch.setenv('E2E', 'yes')
    monkeypatch.setenv('E2E_OUTPUT', 'file')
    conftest_testdir.makepyfile(test_browsers="""
        from flask import url_for

        def test_browser(live_server, browser):
            browser.get(url_for('index', _external=True))
            assert browser.title == 'pytest-invenio'

        def test_browser_fail(live_server, browser):
            browser.get(url_for('index', _external=True))
            assert browser.title != 'pytest-invenio'
    """)
    conftest_testdir.runpytest().assert_outcomes(passed=1, failed=1)
    assert os.path.exists(
        os.path.join(str(conftest_testdir.tmpdir), '.e2e_screenshots'))
    monkeypatch.undo()


def test_celery_config_ext(testdir):
    """Test celery config."""
    testdir.makepyfile(test_app="""
        def test_celery_config_with_celery(celery_config_ext):
            assert celery_config_ext['CELERY_TASK_ALWAYS_EAGER'] == True
            assert celery_config_ext['CELERY_CACHE_BACKEND'] == 'memory'
            assert celery_config_ext[
            'CELERY_TASK_EAGER_PROPAGATES_EXCEPTIONS'] == True
            assert celery_config_ext['CELERY_RESULT_BACKEND'] == 'cache'
    """)
    testdir.runpytest().assert_outcomes(passed=1)


def test_default_location(conftest_testdir):
    conftest_testdir.makepyfile("""
        from invenio_files_rest.models import Bucket

        def test_default_location_create(location):
            new_bucket = Bucket.create(location)
            assert location.name == "pytest-location"
            assert location.uri is not None
            assert new_bucket.location == location
    """)
    conftest_testdir.runpytest().assert_outcomes(passed=1)


def test_bucket_from_dir(conftest_testdir):
    conftest_testdir.makepyfile("""
        import tempfile, os
        from invenio_files_rest.models import ObjectVersion

        def test_creating_location_and_use_bucket_from_dir(bucket_from_dir):
            # Create dir with a file
            dir_for_files = tempfile.mkdtemp()
            with open(
                os.path.join(dir_for_files, 'output_file'),
                'wb'
            ) as file_out:
                file_out.write(('a'*1024).encode('utf8'))
            # load file to bucket
            bucket = bucket_from_dir(dir_for_files)

            # Get all files from bucket
            files_from_bucket = ObjectVersion.get_by_bucket(bucket)
            # Check if there is only one file
            assert files_from_bucket.count() == 1
            # And check if this file has proper key
            assert files_from_bucket.one().key == "output_file"
    """)
    conftest_testdir.runpytest().assert_outcomes(passed=1)


def test_entrypoint_pkg_resources(testdir):
    """Test database creation and initialization."""
    testdir.makeconftest("""
        import pytest

        from flask import Flask
        from functools import partial
        from invenio_db import InvenioDB

        def _factory(name, **config):
            app_ = Flask(name)
            app_.config.update(**config)
            InvenioDB(app_)
            return app_

        @pytest.fixture(scope='module')
        def create_app(entry_points):
            return partial(_factory, 'app')
    """)
    testdir.makepyfile(mock_module="""
        from invenio_db import db
        from pkg_resources import iter_entry_points

        class Place(db.Model):
            id = db.Column(db.Integer, primary_key=True)

        def db_entry_points():
            return iter_entry_points('invenio_db.models')
    """)
    testdir.makepyfile(test_ep="""
        import pytest
        # By importing we get a reference to iter_entry_points before it
        # has been mocked (to test that this case also works).
        from mock_module import db_entry_points


        @pytest.fixture(scope='module')
        def extra_entry_points():
            return {
                'invenio_db.models': [
                    'mock_module = mock_module',
                ],
            }

        def test_app(base_app, db):
            from mock_module import Place
            assert Place.query.count() == 0

        def test_extras(base_app, db):
            for ep in db_entry_points():
                if ep.name == 'mock_module':
                    return
            assert False, "mock_module not found in entry points"
    """)
    testdir.runpytest("-s").assert_outcomes(passed=2)


def test_entrypoint_importlib(testdir):
    """Test database creation and initialization."""
    testdir.makeconftest("""
        import pytest

        from flask import Flask
        from functools import partial
        from invenio_db import InvenioDB

        def _factory(name, **config):
            app_ = Flask(name)
            app_.config.update(**config)
            InvenioDB(app_)
            return app_

        @pytest.fixture(scope='module')
        def create_app(entry_points):
            return partial(_factory, 'app')
    """)
    testdir.makepyfile(mock_module="""
        from invenio_db import db
        from importlib_metadata import entry_points

        class Place(db.Model):
            id = db.Column(db.Integer, primary_key=True)

        def db_entry_points():
            return entry_points(group='invenio_db.models')
    """)
    testdir.makepyfile(test_ep="""
        import pytest
        # By importing we get a reference to entry_points before it
        # has been mocked (to test that this case also works).
        from mock_module import db_entry_points


        @pytest.fixture(scope='module')
        def extra_entry_points():
            return {
                'invenio_db.models': [
                    'mock_module = mock_module',
                ],
            }

        def test_app(base_app, db):
            from mock_module import Place
            assert Place.query.count() == 0

        def test_extras(base_app, db):
            for ep in db_entry_points():
                if ep.name == 'mock_module':
                    return
            assert False, "mock_module not found in entry points"
    """)
    testdir.runpytest("-s").assert_outcomes(passed=2)
