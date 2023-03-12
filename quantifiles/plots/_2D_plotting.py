from __future__ import annotations

from PyQt5 import QtCore, QtGui, QtWidgets

from matplotlib.pyplot import get_cmap
import pyqtgraph as pg
import numpy as np
import logging

from quantifiles.plots.unit_management import return_unit_scaler, format_unit

logger = logging.getLogger(__name__)


class _2D_plot:
    def __init__(self, dataset, y_key: str = "y0", logmode: dict | None = None):
        """
        plot 2D plot

        Args:
            ds_descr (dataset_data_description) : description of the data
            logmode (dict) : logmode for the z axis -- not supported atm...

        Plotter can handle
            * only lineary/log spaced axis
            * flipping axis also supported
            (limitations due to image based implemenation in pyqtgraph)
        """
        if logmode is None:
            logmode = {}

        self.logmode = {"x": False, "y": False, "z": False}
        self.logmode.update(logmode)

        self.ds = dataset
        self.y_key = y_key

        self.x0_unit_scaler = return_unit_scaler(self.ds.x0.attrs["units"])
        self.x1_unit_scaler = return_unit_scaler(self.ds.x1.attrs["units"])
        self.value_unit_scaler = return_unit_scaler(self.ds[y_key].attrs["units"])

        pg.setConfigOption("background", None)
        pg.setConfigOption("foreground", "k")

        self.widget = QtWidgets.QWidget()
        self.layout = QtWidgets.QVBoxLayout()

        self.plot = pg.PlotItem()
        self.plot.setLabel("bottom", self.ds.x1.long_name, units=format_unit(self.ds.x1.attrs["units"]))
        self.plot.setLabel("left", self.ds.x0.long_name, units=format_unit(self.ds.x0.attrs["units"]))
        self.img = pg.ImageItem()
        # set some image data. This is required for pyqtgraph > 0.11
        self.img.setImage(np.zeros((1, 1)))

        self.img_view = pg.ImageView(view=self.plot, imageItem=self.img)
        self.img_view.setColorMap(get_color_map())
        self.img_view.ui.roiBtn.hide()
        self.img_view.ui.menuBtn.hide()
        self.img_view.ui.histogram.autoHistogramRange()

        self.label = QtWidgets.QLabel()
        self.label.setAlignment(QtCore.Qt.AlignRight)

        self.layout.addWidget(self.img_view)
        self.layout.addWidget(self.label)
        self.widget.setLayout(self.layout)

        self.update()
        self.plot.setAspectLocked(False)

        self.proxy = pg.SignalProxy(
            self.plot.scene().sigMouseMoved, rateLimit=60, slot=self.mouseMoved
        )

    def update(self):
        try:
            # logger.info(f'updating {self.ds.name} {self.ds.y.name} vs {self.ds.x0.name} ')
            x0 = np.unique(self.ds.x0.values * self.x0_unit_scaler)
            x1 = np.unique(self.ds.x1.values * self.x1_unit_scaler)

            if self.detect_log_mode(x0):
                self.logmode["y"] = True
                x0 = np.log10(x0)
            if self.detect_log_mode(x1):
                self.logmode["x"] = True
                x1 = np.log10(x1)

            x_args = np.argwhere(np.isfinite(x0)).T[0]
            if len(x_args) == 0:
                # No data yet. Nothing to update.
                return
            x_limit = [np.min(x_args), np.max(x_args)]
            x_limit_num = (x0[x_limit[0]], x0[x_limit[1]])
            y_args = np.argwhere(np.isfinite(x1)).T[0]
            y_limit = [np.min(y_args), np.max(y_args)]
            y_limit_num = (x1[y_limit[0]], x1[y_limit[1]])

            data = self.ds[self.y_key].values.reshape(-1, len(x1))

            data_cp = np.empty(data.shape)
            data_cp[:, :] = np.nan
            x_slice = slice(x_limit[0], x_limit[1] + 1)
            y_slice = slice(y_limit[0], y_limit[1] + 1)
            data_cp[x_slice, y_slice] = data[x_slice, y_slice]
            data = data_cp

            # X and Y seems to be swapped for image items (+ Y inverted)
            x_scale = abs(x_limit_num[1] - x_limit_num[0]) / (x_limit[1] - x_limit[0])
            y_scale = abs(y_limit_num[1] - y_limit_num[0]) / (y_limit[1] - y_limit[0])

            x_off_set = np.min(x0[x_args])
            y_off_set = np.min(x1[y_args])

            # flip axis is postive to negative scan
            if x_limit_num[0] > x_limit_num[1]:
                data = data[::-1, :]
            if y_limit_num[0] > y_limit_num[1]:
                data = data[:, ::-1]

            self.plot.invertY(False)
            self.img.setImage(data)

            if x_scale == 0 or np.isnan(x_scale):
                x_scale = 1
            else:
                x_off_set -= 0.5 * x_scale
            if y_scale == 0 or np.isnan(y_scale):
                y_scale = 1
            else:
                y_off_set -= 0.5 * y_scale
            tr = QtGui.QTransform()
            tr.translate(y_off_set, x_off_set)
            tr.scale(y_scale, x_scale)
            self.img.setTransform(tr)
            self.plot.setLogMode(x=self.logmode["x"], y=self.logmode["y"])
        except Exception:
            logger.error("Error in plot update", exc_info=True)

    def detect_log_mode(self, data):
        # TODO: This is not working properly. Needs to be fixed.
        # args = np.argwhere(np.isfinite(data)).T[0]
        #
        # if len(args) >= 3:
        #     log_diff_data = np.diff(np.log(np.abs(data[args] + 1e-90)))
        #     if np.isclose(log_diff_data[-1], log_diff_data[-2]):
        #         return True

        return False

    def mouseMoved(self, evt):
        try:
            vb = self.plot.vb
            pos = evt[0]  ## using signal proxy turns original arguments into a tuple
            if self.plot.sceneBoundingRect().contains(pos):
                mousePoint = vb.mapSceneToView(pos)
                x_val = mousePoint.x()
                if self.logmode["x"]:
                    x_val = 10**x_val
                y_val = mousePoint.y()
                if self.logmode["y"]:
                    y_val = 10**y_val

                # Note: x and y are mixed up... x_val = ds.x1, y_val = ds.x0
                # ds.y is plotted on x-axis and vice versa.
                y = x_val
                x = y_val

                ds = self.ds
                x_dist = np.abs(ds.x0 * self.x0_unit_scaler - x)
                y_dist = np.abs(ds.x1 * self.x1_unit_scaler - y)
                c = np.maximum(x_dist, y_dist)
                ([xloc,],) = np.where(c == np.min(c))

                point_ds = ds[self.y_key][xloc]

                value = point_ds.values
                value_formatted = (
                    str(value)
                    if not np.isnan(value)
                    else "NaN "
                )

                self.label.setText(
                    "x={}, y={}: {}".format(
                        x,
                        y,
                        value_formatted + format_unit(ds[self.y_key].attrs["units"]),
                    )
                )
        except:
            logger.error("Error mouse move", exc_info=True)


def get_color_map():
    numofLines = 5
    cMapType = "viridis"
    colorMap = get_cmap(cMapType)  # get_cmap is matplotlib object

    colorList = np.linspace(0, 1, numofLines)
    lineColors = colorMap(colorList)

    lineColors = lineColors * 255
    lineColors = lineColors.astype(int)
    return pg.ColorMap(pos=np.linspace(0.0, 1.0, numofLines), color=lineColors)
