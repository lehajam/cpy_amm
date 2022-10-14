#!/usr/bin/env python

"""The setup script."""

from setuptools import setup, find_packages

with open('README.rst') as readme_file:
    readme = readme_file.read()

with open('HISTORY.rst') as history_file:
    history = history_file.read()

requirements = [ ]

test_requirements = ['pytest>=3', ]

setup(
    author="Lehajam Boujemaoui",
    author_email='cpyamm.lib@gmail.com',
    python_requires='>=3.6',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Natural Language :: English',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
    ],
    description="A package for quantitative analysis and easy data visualisation of constant product automated market makers (CP AMMs)",
    install_requires=requirements,
    license="Apache Software License 2.0",
    long_description=readme + '\n\n' + history,
    include_package_data=True,
    keywords='cpy_amm',
    name='cpy_amm',
    packages=find_packages(include=['cpy_amm', 'cpy_amm.*']),
    test_suite='tests',
    tests_require=test_requirements,
    url='https://github.com/lehajam/cpy_amm',
    version='0.1.0',
    zip_safe=False,
)
