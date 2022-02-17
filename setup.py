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
    'elasticsearch>=7.0.0,<7.14',
    'elasticsearch-dsl>=7.0.0,<8.0.0',
    'invenio-celery>=1.2.4',
    'invenio-db>=1.0.12,<1.1.0',
    'invenio-files-rest>=1.3.2',
    'invenio-mail>=1.0.2,<1.1.0',
    'invenio-search>=1.4.2,<1.5.0',
]

extras_require = {
    'docs': [
        'Sphinx>=4.2.0',
    ],
    'tests': tests_require,
}

extras_require['all'] = []
for reqs in extras_require.values():
    extras_require['all'].extend(reqs)

install_requires = [
    'check-manifest>=0.42',
    'coverage>=5.3,<6',
    'docker-services-cli>=0.4.0',
    'pytest-cov>=3.0.0',
    'pytest-flask>=1.2.0',
    'pytest-isort>=3.0.0',
    'pytest-pycodestyle>=2.2.0',
    'pytest-pydocstyle>=2.2.0',
    'pytest>=6,<7',
    'selenium>=3.7.0',
    # Keep importlib aligned with invenio-base.
    'importlib-metadata>=4.4',
    'importlib-resources>=5.0',
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
    tests_require=tests_require,
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Plugins',
        'Environment :: Web Environment',
        'Framework :: Pytest',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: Software Development :: Testing',
    ],
)
