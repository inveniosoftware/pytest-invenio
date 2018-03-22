..
    This file is part of pytest-invenio.
    Copyright (C) 2018 CERN.

    pytest-invenio is free software; you can redistribute it and/or modify it
    under the terms of the MIT License; see LICENSE file for more details.

Installation
============

pytest-invenio is on PyPI so all you need is:

.. code-block:: console

   $ pip install pytest-invenio

Normally, you would add it to your package's ``setup.py`` to have it
automatically installed:

.. code-block:: python

    setup(
        # ...
        setup_requires=[
            'pytest-runner>=3.0.0,<5',
        ],
        tests_require=[
            'pytest-invenio>=1.0.0,<1.1.0',
        ]
    )

**Tip**: Add the following alias to your ``setup.cfg``:

.. code-block:: ini

    [aliases]
    test = pytest

In this way, the standard Python way of executing test still works:

.. code-block:: console

   $ python setup.py test
