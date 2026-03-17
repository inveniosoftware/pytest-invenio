# -*- coding: utf-8 -*-
#
# This file is part of pytest-invenio.
# Copyright (C) 2026 CESNET z.s.p.o.
#
# pytest-invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Versioning manager for pytest-invenio.

Note: this module must be imported from within a fixture function, not on a top-level
as not all Invenio modules depend on invenio-db and thus SQLAlchemy and SQLAlchemy-Continuum.
"""

import sqlalchemy as sa
from sqlalchemy_continuum import UnitOfWork, VersioningManager


def is_joined_session(session):
    return session.join_transaction_mode == "create_savepoint"


class PytestInvenioUnitOfWork(UnitOfWork):
    def process_before_flush(self, session):
        """
        Before flush processor for given session.

        This method creates a version session which is later on used for the
        creation of version objects. It also creates Transaction object for the
        current transaction and invokes before_flush template method on all
        plugins.

        If the given session had no relevant modifications regarding versioned
        objects this method does nothing.

        :param session: SQLAlchemy session object
        """
        if session == self.version_session:
            return

        if not self.is_modified(session):
            return

        if not self.version_session:
            self.version_session = sa.orm.session.Session(bind=session.connection())
            self.version_session.join_transaction_mode = "control_fully"

        if not self.current_transaction:
            self.create_transaction(session)

        self.manager.plugins.before_flush(self, session)

    def process_after_flush(self, session):
        """
        After flush processor for given session.

        Creates version objects for all modified versioned parent objects that
        were affected during the flush phase.

        :param session: SQLAlchemy session object
        """
        if session == self.version_session:
            return

        if not self.current_transaction:
            return

        if not self.version_session:
            self.version_session = sa.orm.session.Session(bind=session.connection())
            self.version_session.join_transaction_mode = "control_fully"

        self.make_versions(session)

    def transaction_args(self, session):
        args = {}
        for plugin in self.manager.plugins:
            args.update(plugin.transaction_args(self, session))
        return args

    def create_transaction(self, session):
        """
        Create transaction object for given SQLAlchemy session.

        :param session: SQLAlchemy session object
        """
        args = self.transaction_args(session)

        Transaction = self.manager.transaction_cls
        self.current_transaction = Transaction()

        for key, value in args.items():
            setattr(self.current_transaction, key, value)
        if not self.version_session:
            self.version_session = sa.orm.session.Session(bind=session.connection())
            self.version_session.join_transaction_mode = "control_fully"
        self.version_session.add(self.current_transaction)
        self.version_session.flush()
        self.version_session.expunge(self.current_transaction)
        session.add(self.current_transaction)
        return self.current_transaction


class PytestInvenioVersioningManager(VersioningManager):
    def __init__(self):
        super().__init__(unit_of_work_cls=PytestInvenioUnitOfWork)

    # def clear(self, session):
    #     if not is_joined_session(session):
    #         return
    #     super().clear(session)


pytest_invenio_versioning_manager = PytestInvenioVersioningManager()
"""A versioning manager instance for all tests. Note that this must be a singleton instance."""
