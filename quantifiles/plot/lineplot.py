from __future__ import annotations

from itertools import cycle
from typing import Sequence

from PyQt5 import QtWidgets
import pyqtgraph

import xarray as xr

_OPTIONS = [
    {
        "pen": (0, 114, 189),
        "symbolBrush": (0, 114, 189),
        "symbolPen": "w",
        "symbol": "p",
        "symbolSize": 12,
    },
    {
        "pen": (217, 83, 25),
        "symbolBrush": (217, 83, 25),
        "symbolPen": "w",
        "symbol": "h",
        "symbolSize": 12,
    },
    {
        "pen": (250, 194, 5),
        "symbolBrush": (250, 194, 5),
        "symbolPen": "w",
        "symbol": "t3",
        "symbolSize": 12,
    },
    {
        "pen": (54, 55, 55),
        "symbolBrush": (55, 55, 55),
        "symbolPen": "w",
        "symbol": "s",
        "symbolSize": 12,
    },
    {
        "pen": (119, 172, 48),
        "symbolBrush": (119, 172, 48),
        "symbolPen": "w",
        "symbol": "d",
        "symbolSize": 12,
    },
    {
        "pen": (19, 234, 201),
        "symbolBrush": (19, 234, 201),
        "symbolPen": "w",
        "symbol": "t1",
        "symbolSize": 12,
    },
    {
        "pen": (0, 0, 200),
        "symbolBrush": (0, 0, 200),
        "symbolPen": "w",
        "symbol": "o",
        "symbolSize": 12,
    },
    {
        "pen": (0, 128, 0),
        "symbolBrush": (0, 128, 0),
        "symbolPen": "w",
        "symbol": "t",
        "symbolSize": 12,
    },
    {
        "pen": (195, 46, 212),
        "symbolBrush": (195, 46, 212),
        "symbolPen": "w",
        "symbol": "t2",
        "symbolSize": 12,
    },
    {
        "pen": (237, 177, 32),
        "symbolBrush": (237, 177, 32),
        "symbolPen": "w",
        "symbol": "star",
        "symbolSize": 12,
    },
    {
        "pen": (126, 47, 142),
        "symbolBrush": (126, 47, 142),
        "symbolPen": "w",
        "symbol": "+",
        "symbolSize": 12,
    },
]


class LinePlot(QtWidgets.QWidget):
    def __init__(
        self,
        dataset: xr.Dataset,
        x_key: str,
        y_keys: Sequence[str] | str,
        parent=None,
    ):
        super().__init__(parent)
        self.y_keys = [y_keys] if isinstance(y_keys, str) else y_keys
        self.x_key = x_key

        self.parent = parent
        self.dataset = dataset

        pyqtgraph.setConfigOption("background", None)
        pyqtgraph.setConfigOption("foreground", "k")

        layout = QtWidgets.QVBoxLayout()

        self.plot = pyqtgraph.PlotWidget()
        self.plot.addLegend()
        self.curves = self.create_curves()

        self.plot.setLabel(
            "left",
            self.dataset[self.y_keys[0]].long_name,
            units=self.dataset[self.y_keys[0]].attrs["units"],
        )
        self.plot.setLabel(
            "bottom",
            self.dataset[x_key].long_name,
            units=self.dataset[x_key].attrs["units"],
        )

        self.plot.showGrid(x=True, y=True)
        if self.dataset[self.y_keys[0]].attrs["units"] == "%" and len(y_keys) == 1:
            self.plot.setYRange(0, 1)

        layout.addWidget(self.plot)
        self.setLayout(layout)

    def create_curves(self):
        options_generator = cycle(_OPTIONS)
        curves = []
        for y_var in self.y_keys:
            curve_name = f"{self.dataset[y_var].name}: {self.dataset[y_var].long_name}"
            curve = self.plot.plot(
                self.dataset[self.x_key].values,
                self.dataset[y_var].values,
                **next(options_generator),
                name=curve_name,
                connect="finite",
            )
            curves.append(curve)
        return curves
