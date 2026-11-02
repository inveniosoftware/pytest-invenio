# -*- coding: utf-8 -*-
#
# This file is part of pytest-invenio.
# Copyright (C) 2026 CESNET z.s.p.o.
#
# pytest-invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Versioning support for pytest-invenio.

Note: import this module from inside a fixture, not at module level, because not
all Invenio modules depend on invenio-db, SQLAlchemy, and SQLAlchemy-Continuum.
"""

from unittest.mock import patch

import sqlalchemy as sa
from sqlalchemy_continuum import UnitOfWork, VersioningManager


class NonNestingSession(sa.orm.session.Session):
    """Session subclass used by sqlalchemy-continuum in tests.

    The main test session created by the `db` fixture uses savepoints
    (via `create_savepoint` join transaction mode) to isolate tests.
    SQLAlchemy-Continuum opens another session on the same connection to
    flush its `Transaction` row and obtain its id::

        +----------------------------------------------+
        |  db connection (sa.base.Connection)          |
        +----------------------------------------------+
        | Savepoint                                    |
        +----------------------------------------------+
                 ^                          ^
                 |                          |
        +---------------------+    +-------------------+
        | test session        |    | continuum session |
        +---------------------+    +-------------------+
        | nested transaction  |
        +---------------------+

    Using a regular `Session` here would create an extra nested transaction
    and savepoint on the shared connection. The two sessions would then manage
    different savepoints, which leads to transaction-state warnings.

    This subclass sets `join_transaction_mode="control_fully"` so the temporary
    continuum session reuses the connection without creating its own savepoint.
    That is safe here because continuum uses this session only for `flush()`;
    commit and rollback still happen on the original test session.

    Example of how sqlalchemy-continuum's `UnitOfWork` uses this session:

        .. code-block:: python

                self.version_session = NonNestingSession(bind=session.connection())
                self.version_session.add(self.current_transaction)
                self.version_session.flush()
                self.version_session.expunge(self.current_transaction)
                session.add(self.current_transaction)
                # <-- note: no commit was called on the version_session
    """

    def __init__(self, *args, **kwargs):
        """Initialize the session with `join_transaction_mode="control_fully"`."""
        kwargs["join_transaction_mode"] = "control_fully"
        super().__init__(*args, **kwargs)


class PytestInvenioUnitOfWork(UnitOfWork):
    """Unit of work class that enables using sqlalchemy-continuum with create-savepoint mode."""

    def process_before_flush(self, session):
        """Temporarily replace continuum's session class and call the parent."""
        with patch("sqlalchemy.orm.session.Session", NonNestingSession):
            super().process_before_flush(session)

    def process_after_flush(self, session):
        """Temporarily replace continuum's session class and call the parent."""
        with patch("sqlalchemy.orm.session.Session", NonNestingSession):
            super().process_after_flush(session)

    def create_transaction(self, session):
        """Temporarily replace continuum's session class and call the parent."""
        with patch("sqlalchemy.orm.session.Session", NonNestingSession):
            return super().create_transaction(session)


pytest_invenio_versioning_manager = VersioningManager(
    unit_of_work_cls=PytestInvenioUnitOfWork
)
"""Singleton versioning manager shared by all tests."""
