# -*- coding: utf-8 -*-
#
# This file is part of pytest-invenio.
# Copyright (C) 2017-2018 CERN.
# Copyright (C) 2018 Esteban J. G. Garbancho.
# Copyright (C) 2018 Northwestern University, Feinberg School of Medicine,
# Galter Health Sciences Library.
#
# pytest-invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Pytest fixtures for Invenio."""

import os

from setuptools import find_packages, setup

readme = open('README.rst').read()
history = open('CHANGES.rst').read()

tests_require = [
    'check-manifest>=0.25',
    # coverage pinned because of https://github.com/nedbat/coveragepy/issues/716
    'coverage>=4.0,<5.0.0',
    'elasticsearch-dsl>=6.0.0,<7.0.0',
    'elasticsearch>=6.0.0,<7.0.0',
    'invenio-celery>=1.2.0',
    'invenio-db>=1.0.4,<1.1.0',
    'invenio-files-rest>=1.1.1',
    'invenio-mail>=1.0.0,<1.1.0',
    'invenio-search>=1.2.3,<1.3.0',
    'isort>=4.3',
    'pydocstyle>=2.0.0',
    'pytest-pep8>=1.0.6',
    'six>=1.12.0',
    'urllib3>=1.23'
]

extras_require = {
    'docs': [
        'Sphinx>=1.8.0',
    ],
    'tests': tests_require,
}

extras_require['all'] = []
for reqs in extras_require.values():
    extras_require['all'].extend(reqs)

setup_requires = [
    'pytest-runner>=3.0.0,<5',
]

install_requires = [
    # pinned because of change of fixture scope in pytest-flask v1.0.0
    # live_server
    'pytest-flask>=0.15.1,<1.0.0',
    'pytest>=4.6.1',
    'pytest-cov>=2.5.1',
    'selenium>=3.7.0',
]

packages = find_packages()


# Get the version string. Cannot be done with import!
g = {}
with open(os.path.join('pytest_invenio', 'version.py'), 'rt') as fp:
    exec(fp.read(), g)
    version = g['__version__']

setup(
    name='pytest-invenio',
    version=version,
    description=__doc__,
    long_description=readme + '\n\n' + history,
    keywords='invenio pytest',
    license='MIT',
    author='CERN',
    author_email='info@inveniosoftware.org',
    url='https://github.com/inveniosoftware/pytest-invenio',
    packages=packages,
    zip_safe=False,
    include_package_data=True,
    platforms='any',
    entry_points={
        'pytest11': [
            'invenio = pytest_invenio.plugin',
        ],
    },
    extras_require=extras_require,
    install_requires=install_requires,
    setup_requires=setup_requires,
    tests_require=tests_require,
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Plugins',
        'Environment :: Web Environment',
        'Framework :: Pytest',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: Software Development :: Testing',
    ],
)
