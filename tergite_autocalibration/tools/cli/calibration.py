# This code is part of Tergite
#
# (C) Copyright Stefan Hill 2024
# (C) Copyright Michele Faucci Giannelli 2024
# (C) Copyright Chalmers Next Labs 2024
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

from pathlib import Path
from typing import Annotated

import typer

from tergite_autocalibration.utils.dto.enums import MeasurementMode

calibration_cli = typer.Typer()


@calibration_cli.command(help="Start the calibration supervisor.")
def start(
    c: Annotated[
        str,
        typer.Option(
            "-c",
            help="Takes the cluster ip address as argument. If not set, it will try take CLUSTER_IP in the .env file.",
        ),
    ] = None,
    r: Annotated[
        str,
        typer.Option(
            "-r",
            help="Use -r if you want to use rerun an analysis, give the path to the dataset folder (plots will be overwritten), you also need to specify the name of the node using -n",
        ),
    ] = None,
    name: Annotated[
        str,
        typer.Option(
            "--name",
            "-n",
            help="Use to specify the node type to rerun, only works with -r option",
        ),
    ] = None,
    push: Annotated[
        bool,
        typer.Option(
            "--push",
            is_flag=True,
            help="If --push the a backend will pushed to an MSS specified in MSS_MACHINE_ROOT_URL in the .env file.",
        ),
    ] = False,
):
    from ipaddress import ip_address, IPv4Address

    from tergite_autocalibration.config.settings import CLUSTER_IP
    from tergite_autocalibration.scripts.calibration_supervisor import (
        CalibrationSupervisor,
    )
    from tergite_autocalibration.scripts.db_backend_update import update_mss

    cluster_mode: "MeasurementMode" = MeasurementMode.real
    parsed_cluster_ip: "IPv4Address" = CLUSTER_IP
    node_name = ""
    data_path = ""

    if r:
        folder_path = Path(r)

        # Check if the folder exists
        if not folder_path.is_dir():
            print(f"Error: The specified folder '{folder_path}' does not exist.")
            exit(1)  # Exit with an error code

        if not name:
            typer.echo(
                "You are trying to re-run the analysis on a specific node but you did not specify it."
                "Please specify the node using -n or --name."
            )
            exit(1)  # Exit with an error exit

        cluster_mode = MeasurementMode.re_analyse
        data_path = folder_path
        node_name = name

    # Check whether the ip address of the cluster is set correctly
    if c:
        if len(c) >= 0:
            cluster_mode = MeasurementMode.real
            parsed_cluster_ip = ip_address(c)
        else:
            typer.echo(
                "Cluster argument requires the ip address of the cluster as parameter. "
                "Trying to start the calibration supervisor with default cluster configuration."
            )

    supervisor = CalibrationSupervisor(
        cluster_mode=cluster_mode,
        cluster_ip=parsed_cluster_ip,
        node_name=node_name,
        data_path=data_path,
    )
    supervisor.calibrate_system()
    if push:
        update_mss()