# -*- coding: utf-8 -*-
#
# This file is part of pytest-invenio.
# Copyright (C) 2025 CESNET i.l.e.
#
# pytest-invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
"""Database tools for test cleanup."""
import logging

from sqlalchemy import MetaData, String, and_, func, select

logger = logging.getLogger(__name__)


class InconsistentDatabaseError(Exception):
    """Raised when the database is found to be inconsistent after test cleanup."""

    pass


def store_database_values(engine, conn):
    """Introspect the session, get all the tables and store their primary key values.

    The result is a dict[table_name, list[pk_tuple]]
    """
    metadata = MetaData()
    metadata.reflect(engine)

    dump = {}
    for table_name, table in metadata.tables.items():
        # Get primary key columns and foreign key columns
        pk_columns = [
            column
            for column in table.columns
            if column.primary_key or len(column.foreign_keys) > 0
        ]

        if not pk_columns:
            # Skip tables without primary keys
            continue

        # Select only primary key columns, cast to string at database level
        pk_columns_as_string = [func.cast(col, String) for col in pk_columns]
        result = conn.execute(select(*pk_columns_as_string))
        try:
            dump[table_name] = [tuple(row) for row in result.fetchall()]
        except Exception as ex:
            raise RuntimeError(f"Could not fetch rows from table {table_name}") from ex

    return dump


def purge_database_values(engine, conn, stored_values):
    """Delete rows that are not in the stored values."""
    metadata = MetaData()
    metadata.reflect(engine)

    # Build a list of (table_name, delete_condition) tuples
    to_be_deleted = []

    for table_name, table in metadata.tables.items():
        stored_rows = stored_values.get(table_name, [])

        # Get primary key columns and foreign key columns
        pk_columns = [
            column
            for column in table.columns
            if column.primary_key or len(column.foreign_keys) > 0
        ]

        if not pk_columns:
            logger.warning(f"Table {table_name} has no primary key. Skipping.")
            continue

        # Convert stored rows to a set of primary key tuples for fast lookup
        stored_pk_set = set(stored_rows)

        # create a select statement that would include only rows that are not present
        # in the stored values. It will be not (pk1 == val1 and pk2 == val2 and ...) and not (...)
        row_matcher_conditions = []
        for stored_pk in stored_pk_set:
            # Cast columns to string at database level for comparison
            condition = and_(
                *(
                    func.cast(pk_col, String) == pk_val
                    for pk_col, pk_val in zip(pk_columns, stored_pk)
                )
            )
            # negate the condition to match rows that are not equal
            row_matcher_conditions.append(~condition)

        if row_matcher_conditions:
            non_matching_condition = and_(*row_matcher_conditions)
            to_be_deleted.append(
                (table_name, table, non_matching_condition, len(stored_pk_set))
            )
        else:
            # delete everything
            to_be_deleted.append((table_name, table, None, len(stored_pk_set)))

    # Try to delete rows with retry mechanism for foreign key constraints
    while to_be_deleted:
        failed_deletions = []

        for table_name, table, where_condition, expected_count in to_be_deleted:
            # Execute deletion in a transaction so that we can rollback on failure
            with conn.begin():
                try:
                    delete_stmt = table.delete()
                    if where_condition is not None:
                        delete_stmt = delete_stmt.where(where_condition)

                    conn.execute(delete_stmt)

                    existing_count = conn.execute(
                        select(func.count()).select_from(table)
                    ).scalar()
                    conn.commit()
                    if expected_count > existing_count:

                        where_str = where_condition.compile(
                            dialect=conn.dialect,
                            compile_kwargs={"literal_binds": True},
                        )

                        raise InconsistentDatabaseError(
                            f"Expected to have {expected_count} rows in table {table_name} "
                            f"in test cleanup but only {existing_count} remain after the test. "
                            f"The test must have removed rows from module-level fixtures, "
                            f"thus making the database inconsistent for subsequent tests."
                            f"The conditions for rows: {where_str}"
                        )
                    logger.debug(
                        "Deleted rows from table: %s, expected: %s, remaining: %s",
                        table_name,
                        expected_count,
                        existing_count,
                    )
                    if existing_count != expected_count:
                        logger.warning(
                            "Not all rows deleted as expected, will try again."
                        )
                        failed_deletions.append(
                            (table_name, table, where_condition, expected_count)
                        )
                except InconsistentDatabaseError:
                    # Reraise as the database is in an inconsistent state which can not be fixed
                    raise
                except Exception:
                    # Rollback on failure and retry in next iteration
                    conn.rollback()
                    failed_deletions.append(
                        (table_name, table, where_condition, expected_count)
                    )

        if len(failed_deletions) == len(to_be_deleted):
            table_names = [table_name for table_name, _, _, _ in failed_deletions]
            raise RuntimeError(
                f"Could not delete the remaining rows due to foreign key cycles in tables: {table_names}"
            )
        else:
            # Update the list with failed deletions for next iteration
            to_be_deleted = failed_deletions
