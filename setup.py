import os
from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))

# Get the long description from the README file
with open(os.path.join(here, "README.md")) as f:
    long_description = f.read()

setup(
    name="openag_cloud",
    version="0.0.1",
    description="Central repository for storing grow data",
    long_description=long_description,
    url="https://github.com/OpenAgInitiative/openag_cloud",
    author="Open Agriculture Initiative",
    licence="GPL",
    classifiers=[
        "Development Status :: 2 - Pre-Alpha",
        "Environment :: Console",
        "Framework :: Flask",
        "Intended Audience :: Developers,",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Natural Language :: English",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python :: 2.7",
    ],
    packages=find_packages(),
    install_requires=[
        "CouchDB>=1.0.1",
        "Flask>=0.11",
        "Flask-WTF>=0.12",
        "gevent>=1.1.1",
        "requests>=2.10",
    ],
    entry_points={
        "console_scripts": [
            "openag_cloud = openag_cloud:main"
        ]
    },
    package_data={"openag_cloud": ["couchdb.ini"]}
)
