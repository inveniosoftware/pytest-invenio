# -*- coding: utf-8 -*-
#
# This file is part of pytest-invenio.
# Copyright (C) 2022 CERN.
#
# pytest-invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
#

"""Helper class for creating and using user fixtures."""

from copy import deepcopy

from flask_principal import Identity, identity_changed


class UserFixtureBase:
    """A user fixture for easy test user creation."""

    def __init__(self, email=None, password=None, active=True):
        """Constructor."""
        self._email = email
        self._active = active
        self._password = password
        self._identity = None
        self._user = None
        self._client = None

    #
    # Creation
    #
    def create(self, app, db):
        """Create the user."""
        from flask_security.utils import hash_password
        with db.session.begin_nested():
            datastore = app.extensions["security"].datastore
            user = datastore.create_user(
                email=self.email,
                password=hash_password(self.password),
                active=self._active,
            )
        db.session.commit()
        self._user = user
        self._app = app
        return self

    #
    # Properties
    #
    @property
    def user(self):
        """Get the user."""
        return self._user

    @property
    def id(self):
        """Get the user id as a string."""
        return str(self._user.id)

    @property
    def email(self):
        """Get the user."""
        return self._email

    @property
    def password(self):
        """Get the user."""
        return self._password

    #
    # App context helpers
    #
    def refresh(self):
        """Refresh the identity."""
        del self.identity
        self.identity

    @property
    def identity(self):
        """Create identity for the user."""
        if self._identity is None:
            with self._app.test_request_context():
                # Simulate a full login -  we do not use flask-security's
                # login_user because it adds login ips/timestamps on every
                # login
                from flask_login import login_user
                from flask_security import logout_user
                login_user(self.user)
                identity = Identity(self.id)
                identity_changed.send(self._app, identity=identity)
                self._identity = deepcopy(identity)
                # Clean up - we just want the identity object.
                logout_user()
        return self._identity

    @identity.deleter
    def identity(self):
        """Delete the user."""
        self._identity = None

    def app_login(self):
        """Create identity for the user."""
        from flask_security import login_user
        assert login_user(self.user)

    def app_logout(self):
        """Create identity for the user."""
        from flask_security import logout_user
        assert logout_user()

    #
    # Test client helpers
    #
    def login(self, client, logout_first=False):
        """Login the given client."""
        return self._login(client, '/', logout_first)

    def api_login(self, client, logout_first=False):
        """Login the given client."""
        return self._login(client, '/api/', logout_first)

    def logout(self, client):
        """Logout the given client."""
        return self._logout(client, '/')

    def api_logout(self, client):
        """Logout the given client."""
        return self._logout(client, '/api/')

    def _login(self, client, base_path, logout):
        """Login the given client."""
        if logout:
            self._logout(client, base_path)
        res = client.post(
            f'{base_path}login',
            data=dict(email=self.email, password=self.password),
            environ_base={'REMOTE_ADDR': '127.0.0.1'},
            follow_redirects=True,
        )
        assert res.status_code == 200
        return client

    def _logout(self, client, base_path):
        """Logout the client."""
        res = client.get(f'{base_path}logout')
        assert res.status_code < 400
        return client