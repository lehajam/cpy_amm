#!/usr/bin/env python

"""The setup script."""

from setuptools import find_packages, setup

with open("README.rst") as readme_file:
    readme = readme_file.read()

with open("HISTORY.rst") as history_file:
    history = history_file.read()

requirements = [
    "bokeh==2.4.3",
    "loguru==0.6.0",
    "numpy==1.23.1",
    "terra-sdk==2.0.6",
    "terra-proto==1.0.1",
]

test_requirements = [
    "pytest>=3",
]

setup(
    author="cpyamm.lib@gmail.com",
    author_email="cpyamm.lib@gmail.com",
    python_requires=">=3.10",
    classifiers=[
        "Development Status :: 2 - Pre-Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: Apache Software License",
        "Natural Language :: English",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
    ],
    description="A package for quantitative analysis and easy data visualisation of constant product automated market makers (CP AMMs)",  # noqa
    install_requires=requirements,
    license="Apache Software License 2.0",
    long_description=readme + "\n\n" + history,
    include_package_data=True,
    keywords="cpy_amm",
    name="cpy_amm",
    packages=find_packages(include=["cpy_amm", "cpy_amm.*"]),
    test_suite="tests",
    tests_require=test_requirements,
    url="https://github.com/lehajam/cpy_amm",
    version="0.2.0",
    zip_safe=False,
)
