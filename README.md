# Quantifiles

[![License](https://img.shields.io/badge/License-BSD_2--Clause-orange.svg)](https://opensource.org/licenses/BSD-2-Clause)
[![Code style](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

Welcome to Quantifiles, a simple PyQt5 application for viewing dataset files generated by [Quantify-core](https://gitlab.com/quantify-os/quantify-core/).

## Installation

### Install from PyPI

```bash
pip install quantifiles
```

### Install from source

```bash
git clone https://gitlab.com/dcrielaard/quantifiles.git
cd quantifiles
pip install -e .
```

## Usage

To start the application from the command line, run:

```bash
quantifiles
```

Alternatively, you can run the application from the generated executable located in the `Scripts` folder after installation.

To start the application from within Python, run:

```python
from quantifiles import quantifiles

quantifiles()  # This will start the application, optionally you can pass the data directory as an argument.
```

**Tip:** The plots can be copied to the clipboard by right-clicking on them.

## Contributing

Feel free to dive in! [Open an issue](https://gitlab.com/dcrielaard/quantifiles/issues/new) or submit PRs.

## License
This project is licensed under the terms of the BSD 2-Clause License. See the LICENSE file for more details.
