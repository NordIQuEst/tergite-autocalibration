from setuptools import setup, find_packages

from quantifiles import __version__ as version

with open("README.md") as f:
    readme = f.read()

with open("LICENSE") as f:
    license = f.read()

setup(
    name="quantifiles",
    version=version,
    description="Simple databrowser for quantify datasets.",
    long_description=readme,
    long_description_content_type="text/markdown",
    author="Damien Crielaard",
    author_email="damiencrielaard@gmail.com",
    url="https://gitlab.com/dcrielaard/quantifiles",
    license=license,
    packages=find_packages(exclude=("test_data",)),
    entry_points={"gui_scripts": ["quantifiles=quantifiles.__init__:entry_point"]},
    install_requires=[
        "numpy",
        "matplotlib",
        "scipy",
        "pandas",
        "xarray",
        "filelock",
        "qcodes",
        "pyqtgraph",
        "pyqt5",
        "quantify-core",
    ],
    extras_require={"test": ["black", "pytest"]},
    python_requires=">=3.7",
)
