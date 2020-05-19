..
    This file is part of pytest-invenio.
    Copyright (C) 2018-2020 CERN.

    pytest-invenio is free software; you can redistribute it and/or modify it
    under the terms of the MIT License; see LICENSE file for more details.

Changes
=======

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
