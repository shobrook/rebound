try: from setuptools import setup
except ImportError: from distutils.core import setup
from codecs import open
import sys

if sys.version_info[:3] < (2, 0, 0):
    sys.stdout.write("Python 1 is not supported.")
    sys.exit(1)

with open("README.rst", encoding="utf-8") as file:
    readme = file.read()

setup(
    name="rebound-cli",
    version="1.1.4a1",
    description="Automatically displays Stack Overflow results when you get a compiler error",
    long_description=readme,
    url="https://github.com/shobrook/rebound",
    author="shobrook",
    author_email="shobrookj@gmail.com",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "Topic :: Software Development",
        "Topic :: Software Development :: Debuggers",
        "Natural Language :: English",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python"
    ],
    keywords="stackoverflow stack overflow debug debugging error-handling compile errors error message cli",
    include_package_data=True,
    packages=["rebound"],
    #data_files=["demo.gif"],
    entry_points={"console_scripts": ["rebound = rebound.rebound:main"]},
    install_requires=["BeautifulSoup4", "requests", "urllib3", "urwid"],
    requires=["BeautifulSoup4", "requests", "urllib3", "urwid"],
    python_requires=">=3", # NOTE: This will change
    license="MIT"
)
