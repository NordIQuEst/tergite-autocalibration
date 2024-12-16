# Quantifiles

[![pipeline status](https://gitlab.com/dcrielaard/quantifiles/badges/main/pipeline.svg)](https://gitlab.com/dcrielaard/quantifiles/-/commits/main) 
[![PyPi](https://img.shields.io/pypi/v/quantifiles.svg)](https://pypi.org/pypi/quantifiles)
[![License](https://img.shields.io/badge/License-BSD_2--Clause-blue.svg)](https://opensource.org/licenses/BSD-2-Clause)
[![Code style](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

**Note: This is forked from [quantifiles](https://gitlab.com/dcrielaard/quantifiles/).
We are maintaining this modified version of quantifiles as a supplementary tool to browse calibration plots.
This README.md file is just kept as documentation to clarify the origins of the quantifiles browser.**

Welcome to Quantifiles, a PyQt5 application designed for viewing dataset files generated by [Quantify-core](https://gitlab.com/quantify-os/quantify-core/). With Quantifiles, you can easily browse and visualize the contents of your data directory, including the ability to view a plot of the data and browse snapshots.

## Usage

You can launch the application by running the following command in your terminal:

```bash
acli browser [--datadir DATADIR] [--liveplotting] [--loglevel LOGLEVEL]
```

If you don't specify the data directory, you can still access it by selecting File->Open in the application.

Alternatively, you can also use the executable file located in the Scripts folder, which will be generated upon installation.

To start the application from within Python, run:

```python
from tergite_autocalibration.tools.quantifiles import quantifiles

quantifiles()  # This will start the application, optionally you can pass the data directory as an argument.
```

**Tip:** The plots can be copied to the clipboard by right-clicking on them.

## License
This project is licensed under the terms of the BSD 2-Clause License. See the LICENSE file for more details.