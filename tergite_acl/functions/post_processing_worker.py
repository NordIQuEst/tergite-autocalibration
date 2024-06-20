'''Analyze the measured dataset and extract the qoi (quantity of interest)'''
import collections
from pathlib import Path

import matplotlib
# from quantify_core.analysis.calibration import rotate_to_calibrated_axis
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np
import xarray as xr

from tergite_acl.config import settings
from tergite_acl.config.coupler_config import qubit_types
from tergite_acl.lib.analysis.tof_analysis import analyze_tof
from tergite_acl.utils.enums import DataStatus

matplotlib.use(settings.PLOTTING_BACKEND)


def post_process(result_dataset: xr.Dataset, node, data_path: Path):
    # analysis = Multiplexed_Analysis(result_dataset, node, data_path)
    if node.name == 'tof':
        tof = analyze_tof(result_dataset, True)
        return

    n_vars = len(result_dataset.data_vars)
    n_coords = len(result_dataset.coords)

    fit_numpoints = 300
    column_grid = 5
    rows = int(np.ceil(n_vars / column_grid))
    rows = rows * node.plots_per_qubit

    # TODO What does this do, when the MSS is not connected?
    node_result = {}

    fig, axs = plt.subplots(
        nrows=rows,
        ncols=np.min((n_vars, n_coords, column_grid)),
        squeeze=False,
        figsize=(column_grid * 5, rows * 5)
    )

    qoi: list
    data_status: DataStatus

    data_vars_dict = collections.defaultdict(set)
    for var in result_dataset.data_vars:
        this_qubit = result_dataset[var].attrs['qubit']
        data_vars_dict[this_qubit].add(var)

    all_results = {}
    for indx, var in enumerate(result_dataset.data_vars):
        this_qubit = result_dataset[var].attrs['qubit']

        ds = xr.Dataset()
        for var in data_vars_dict[this_qubit]:
            ds = xr.merge([ds, result_dataset[var]])

        ds.attrs['qubit'] = this_qubit
        ds.attrs['node'] = node.name

        primary_plot_row = node.plots_per_qubit * (indx // column_grid)
        primary_axis = axs[primary_plot_row, indx % column_grid]

        redis_field = node.redis_field
        kw_args = getattr(node, "analysis_kwargs", dict())
        node_analysis = node.analysis_obj(ds, **kw_args)
        qoi = node_analysis.run_fitting()
        # TODO: This step should better happen inside the analysis function
        node_analysis.qoi = qoi

        if node.plots_per_qubit > 1:
            list_of_secondary_axes = []
            for plot_indx in range(1, node.plots_per_qubit):
                secondary_plot_row = primary_plot_row + plot_indx
                list_of_secondary_axes.append(
                    axs[secondary_plot_row, indx % column_grid]
                )
            node_analysis.plotter(primary_axis, secondary_axes=list_of_secondary_axes)
        else:
            node_analysis.plotter(primary_axis)

        # TODO temporary hack:
        if node.name in ['cz_calibration', 'cz_dynamic_phase',  'cz_dynamic_phase','cz_calibration_ssro','cz_calibration_swap_ssro', 'cz_optimize_chevron'] and \
                qubit_types[this_qubit] == 'Target':
            node_analysis.update_redis_trusted_values(node.name, node.coupler, redis_field)
            this_element = node.coupler
        elif node.name in ['cz_chevron','cz_chevron_amplitude','cz_calibration_swap', 'cz_dynamic_phase_swap'] and qubit_types[this_qubit] == 'Control':
            node_analysis.update_redis_trusted_values(node.name, node.coupler, redis_field)
            this_element = node.coupler
        elif node.name in ['coupler_spectroscopy','tqg_randomized_benchmarking','tqg_randomized_benchmarking_interleaved']:
            node_analysis.update_redis_trusted_values(node.name, node.coupler, redis_field)
            this_element = node.coupler
        else:
            node_analysis.update_redis_trusted_values(node.name, this_qubit, redis_field)
            this_element = this_qubit

        all_results[this_element] = dict(zip(redis_field, qoi))
        handles, labels = primary_axis.get_legend_handles_labels()

        patch = mpatches.Patch(color='red', label=f'{this_qubit}')
        handles.append(patch)
        primary_axis.legend(handles=handles, fontsize='small')
        if node.plots_per_qubit > 1:
            for secondary_ax in list_of_secondary_axes:
                secondary_ax.legend()

        # logger.info(f'Analysis for the {node} of {this_qubit} is done, saved at {self.data_path}')
    # figure_manager = plt.get_current_fig_manager()
    # figure_manager.window.showMaximized()
    fig = plt.gcf()
    fig.set_tight_layout(True)
    fig.savefig(f'{data_path}/{node.name}.png', bbox_inches='tight', dpi=600)
    # plt.show(block=True)
    plt.show(block=False)
    plt.pause(5)
    plt.close()

    if node != 'tof':
        all_results.update({'measurement_dataset': result_dataset.to_dict()})

    return all_results
