# -*- coding: utf-8 -*-
#
# This file is part of pytest-invenio.
# Copyright (C) 2022-2025 CERN.
# Copyright (C) 2025 Graz University of Technology.
#
# pytest-invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
#

"""Helper class for creating and using user fixtures."""

from copy import deepcopy
from datetime import datetime, timezone


class UserFixtureBase:
    """A user fixture for easy test user creation."""

    def __init__(
        self,
        email=None,
        password=None,
        username=None,
        active=True,
        confirmed=True,
        user_profile=None,
        preferences=None,
        base_url="",
    ):
        """Constructor."""
        self._username = username
        self._user_profile = user_profile
        self._preferences = preferences
        self._email = email
        self._active = active
        self._confirmed = datetime.now(timezone.utc) if confirmed else None
        self._password = password
        self._identity = None
        self._user = None
        self._client = None
        self._base_url = base_url

    #
    # Creation
    #
    def create(self, app, db):
        """Create the user."""
        from flask_security.utils import hash_password

        with db.session.begin_nested():
            datastore = app.extensions["security"].datastore
            data = dict(
                email=self.email,
                password=hash_password(self.password),
                active=self._active,
                confirmed_at=self._confirmed,
            )
            # Support both Invenio-Accounts 1.4 and 2.0
            if self.username is not None:
                data["username"] = self.username
            user = datastore.create_user(**data)
            if self._user_profile is not None:
                user.user_profile = self._user_profile
            if self._preferences is not None:
                user.preferences = self._preferences
            db.session.add(user)
        datastore.mark_changed(id(db.session), uid=user.id)
        datastore.commit()
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
    def username(self):
        """Get the user."""
        return self._username

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
            from flask_principal import Identity, identity_changed

            with self._app.test_request_context():
                # Simulate a full login - we do not use flask-security's
                # login_user because it adds login ips/timestamps on every
                # login
                from flask_login import login_user
                from flask_security import logout_user

                login_user(self.user)
                identity = Identity(self._user.id)
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
        return self._login(client, "/", logout_first)

    def api_login(self, client, logout_first=False):
        """Login the given client."""
        return self._login(client, "/api/", logout_first)

    def logout(self, client):
        """Logout the given client."""
        return self._logout(client, "/")

    def api_logout(self, client):
        """Logout the given client."""
        return self._logout(client, "/api/")

    def _login(self, client, base_path, logout):
        """Login the given client."""
        if logout:
            self._logout(client, base_path)
        res = client.post(
            f"{self._base_url}{base_path}login",
            data=dict(email=self.email, password=self.password),
            follow_redirects=True,
        )
        assert res.status_code == 200
        return client

    def _logout(self, client, base_path):
        """Logout the client."""
        res = client.get(f"{self._base_url}{base_path}logout")
        assert res.status_code < 400
        return client
