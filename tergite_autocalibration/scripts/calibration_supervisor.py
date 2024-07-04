# This code is part of Tergite
from ipaddress import IPv4Address
from typing import Union, List

import toml
from colorama import Fore
from colorama import Style
from colorama import init as colorama_init
from qblox_instruments import Cluster
from quantify_scheduler.instrument_coordinator import InstrumentCoordinator
from quantify_scheduler.instrument_coordinator.components.qblox import ClusterComponent

from tergite_autocalibration.config import settings
from tergite_autocalibration.config.settings import (
    CLUSTER_IP,
    REDIS_CONNECTION,
    CLUSTER_NAME,
)
from tergite_autocalibration.functions.monitor_worker import monitor_node_calibration
from tergite_autocalibration.lib.node_factory import NodeFactory
from tergite_autocalibration.lib.nodes.graph import filtered_topological_order
from tergite_autocalibration.utils.dataset_utils import create_node_data_path
from tergite_autocalibration.utils.enums import MeasurementMode
from tergite_autocalibration.utils.enums import DataStatus
from tergite_autocalibration.utils.errors import ClusterNotFoundError
from tergite_autocalibration.utils.hardware_utils import SpiDAC
from tergite_autocalibration.utils.logger.tac_logger import logger
from tergite_autocalibration.utils.redis_utils import (
    populate_initial_parameters,
    populate_node_parameters,
    populate_quantities_of_interest,
)
from tergite_autocalibration.utils.user_input import (
    user_requested_calibration,
    attenuation_setting,
)
from tergite_autocalibration.utils.visuals import draw_arrow_chart
from tergite_autocalibration.config import settings
from tergite_autocalibration.config.settings import CLUSTER_IP, REDIS_CONNECTION
from tergite_autocalibration.lib.node_base import BaseNode
from tergite_autocalibration.lib.nodes.graph import filtered_topological_order
from tergite_autocalibration.lib.node_factory import NodeFactory
from tergite_autocalibration.utils.logger.tac_logger import logger
from tergite_autocalibration.utils.enums import MeasurementMode
from tergite_autocalibration.utils.enums import DataStatus
from tergite_autocalibration.utils.user_input import user_requested_calibration
from tergite_autocalibration.utils.visuals import draw_arrow_chart
from tergite_autocalibration.utils.dataset_utils import create_node_data_path
from tergite_autocalibration.utils.hardware_utils import SpiDAC, set_qubit_attenuation
from tergite_autocalibration.functions.node_supervisor import monitor_node_calibration
from tergite_autocalibration.utils.redis_utils import (
    populate_initial_parameters,
    populate_node_parameters,
    populate_quantities_of_interest,
)

from tergite_autocalibration.utils.dummy_setup import dummy_setup

colorama_init()


def update_to_user_samplespace(node: BaseNode, user_samplespace: dict):
    node_user_samplespace = user_samplespace[node.name]
    for settable, element_samplespace in node_user_samplespace.items():
        if settable in node.schedule_samplespace:
            node.schedule_samplespace[settable] = element_samplespace
        elif settable in node.external_samplespace:
            node.external_samplespace[settable] = element_samplespace
        else:
            raise KeyError(f"{settable} not in any samplespace")
    return


class CalibrationSupervisor:
    def __init__(
        self,
        cluster_mode: "MeasurementMode" = MeasurementMode.real,
        cluster_ip: Union[str, "IPv4Address"] = CLUSTER_IP,
        cluster_timeout: int = 222,
    ) -> None:

        # Read hardware related configuration steps
        self.cluster_mode: "MeasurementMode" = cluster_mode
        self.cluster_ip: Union[str, "IPv4Address"] = cluster_ip
        self.cluster_timeout: int = cluster_timeout

        # Create objects to communicate with the hardware
        self.cluster: "Cluster" = self._create_cluster()
        self.lab_ic: "InstrumentCoordinator" = self._create_lab_ic(self.cluster)

        # TODO: user configuration could be a toml file
        # Read the calibration specific parameters
        self.qubits = user_requested_calibration["all_qubits"]
        self.couplers = user_requested_calibration["couplers"]
        self.target_node = user_requested_calibration["target_node"]
        self.user_samplespace = user_requested_calibration["user_samplespace"]
        self.measurement_mode = self.cluster_mode

        # Read the device configuration
        self.transmon_configuration = toml.load(settings.DEVICE_CONFIG)

        # Initialize the node structure
        self.node_factory = NodeFactory()
        self.topo_order = filtered_topological_order(self.target_node)

        # TODO MERGE-CZ-GATE: Here, we could have a more general check or .env variable whether to use the spi rack
        # if self.target_node == 'cz_chevron':
        #     self.dacs = {}
        #     self.spi = SpiDAC()
        #     for coupler in self.couplers:
        #         self.dacs[coupler] = self.spi.create_spi_dac(coupler)

    def _create_cluster(self) -> "Cluster":
        cluster_: "Cluster"
        if self.cluster_mode == MeasurementMode.real:
            Cluster.close_all()
            cluster_ = Cluster(CLUSTER_NAME, str(self.cluster_ip))
            cluster_.reset()
            logger.info(f"Reseting Cluster at IP *{str(self.cluster_ip)[-3:]}")
            return cluster_
        else:
            raise ClusterNotFoundError(
                f"Cannot create cluster object from {self.cluster_ip}"
            )

    def _create_lab_ic(self, clusters: Union["Cluster", List["Cluster"]]):

        ic_ = InstrumentCoordinator("lab_ic")
        if isinstance(clusters, Cluster):
            clusters = [clusters]
        for cluster in clusters:
            # Set the attenuation values for the modules
            for module in cluster.modules:
                try:
                    if module.is_qcm_type and module.is_rf_type:
                        module.out0_att(attenuation_setting["qubit"])  # Control lines
                        # print(f'Attenuation setting for {module.name} is {attenuation_setting["qubit"]}')
                        module.out1_att(attenuation_setting["coupler"])  # Flux lines
                        # print(f'Attenuation setting for {module.name} is {attenuation_setting["coupler"]}')
                    elif module.is_qrm_type and module.is_rf_type:
                        module.out0_att(attenuation_setting["readout"])  # Readout lines
                        print(
                            f'Attenuation setting for {module.name} is {attenuation_setting["readout"]}'
                        )
                except:
                    pass
            ic_.add_component(ClusterComponent(cluster))
            ic_.timeout(self.cluster_timeout)
        return ic_

    def calibrate_system(self):
        # TODO: everything which is not in the inspect or calibrate function should go here
        logger.info("Starting System Calibration")
        number_of_qubits = len(self.qubits)
        draw_arrow_chart(f"Qubits: {number_of_qubits}", self.topo_order)

        populate_quantities_of_interest(
            self.transmon_configuration, self.qubits, self.couplers, REDIS_CONNECTION
        )

        for calibration_node in self.topo_order:
            self.inspect_node(calibration_node)
            logger.info(f"{calibration_node} node is completed")

    def inspect_node(self, node_name: str):
        # TODO: the inspect node function could be part of the node
        logger.info(f"Inspecting node {node_name}")

        node: BaseNode = self.node_factory.create_node(
            node_name, self.qubits, couplers=self.couplers
        )

        if node.name in self.user_samplespace:
            update_to_user_samplespace(node, self.user_samplespace)

        # some nodes e.g. cw spectroscopy needs access to the instruments
        node.lab_instr_coordinator = self.cluster_ip

        populate_initial_parameters(
            self.transmon_configuration, self.qubits, self.couplers, REDIS_CONNECTION
        )
        # print(f'{node_name = }')
        # print(f'{self.couplers = }')
        if node_name in [
            "coupler_spectroscopy",
            "cz_chevron",
            "cz_chevron_amplitude",
            "cz_calibration",
            "cz_calibration_ssro",
            "cz_calibration_swap_ssro",
            "cz_dynamic_phase",
            "cz_dynamic_phase_swap",
            "tqg_randomized_benchmarking",
            "tqg_randomized_benchmarking_interleaved",
        ]:
            coupler_statuses = [
                REDIS_CONNECTION.hget(f"cs:{coupler}", node_name) == "calibrated"
                for coupler in self.couplers
            ]
            # print(f'{coupler_statuses=}')
            # node is calibrated only when all couplers have the node calibrated:
            is_node_calibrated = all(coupler_statuses)
        else:
            qubits_statuses = [
                REDIS_CONNECTION.hget(f"cs:{qubit}", node_name) == "calibrated"
                for qubit in self.qubits
            ]
            # node is calibrated only when all qubits have the node calibrated:
            is_node_calibrated = all(qubits_statuses)

        populate_node_parameters(
            node_name,
            is_node_calibrated,
            self.transmon_configuration,
            self.qubits,
            self.couplers,
            REDIS_CONNECTION,
        )

        # Check Redis if node is calibrated
        status = DataStatus.undefined

        if node_name in [
            "coupler_spectroscopy",
            "cz_chevron",
            "cz_optimize_chevron",
            "cz_chevron_amplitude",
            "cz_calibration",
            "cz_calibration_ssro",
            "cz_calibration_swap_ssro",
            "cz_dynamic_phase",
            "cz_dynamic_phase_swap",
            "tqg_randomized_benchmarking",
            "tqg_randomized_benchmarking_interleaved",
        ]:
            for coupler in self.couplers:
                # the calibrated, not_calibrated flags may be not necessary,
                # just store the DataStatus on Redis
                is_calibrated = REDIS_CONNECTION.hget(f"cs:{coupler}", node_name)
                if is_calibrated == "not_calibrated":
                    status = DataStatus.out_of_spec
                    break  # even if a single qubit is not_calibrated mark as out_of_spec
                elif is_calibrated == "calibrated":
                    status = DataStatus.in_spec
                else:
                    raise ValueError(f"status: {status}")
        else:
            for qubit in self.qubits:
                # the calibrated, not_calibrated flags may be not necessary,
                # just store the DataStatus on Redis
                is_calibrated = REDIS_CONNECTION.hget(f"cs:{qubit}", node_name)
                if is_calibrated == "not_calibrated":
                    status = DataStatus.out_of_spec
                    break  # even if a single qubit is not_calibrated mark as out_of_spec
                elif is_calibrated == "calibrated":
                    status = DataStatus.in_spec
                else:
                    raise ValueError(f"status: {status}")

        if status == DataStatus.in_spec:
            print(
                f" \u2714  {Fore.GREEN}{Style.BRIGHT}Node {node_name} in spec{Style.RESET_ALL}"
            )
            return

        elif status == DataStatus.out_of_spec:
            print(
                "\u2691\u2691\u2691 "
                + f"{Fore.RED}{Style.BRIGHT}Calibration required for Node {node_name}{Style.RESET_ALL}"
            )
            node_calibration_status = self.calibrate_node(node)

            # TODO : develop failure strategies ->
            # if node_calibration_status == DataStatus.out_of_spec:
            #     node_expand()
            #     node_calibration_status = self.calibrate_node(node)

    def calibrate_node(self, node, **static_parameters) -> DataStatus:
        if type(node) == str:
            node = self.node_factory.create_node(
                node, self.qubits, couplers=self.couplers, **static_parameters
            )
        logger.info(f"Calibrating node {node.name}")

        # TODO MERGE-CZ-GATE: We should discuss the information flow here - what values are set and for which component?
        """
        if node_label in transmon_configuration:
        write_calibrate_paras(node_label)
        # node_dictionary = user_requested_calibration['node_dictionary']
        if couplers is not None and len(couplers):
            static_parameters["couplers"] = couplers
        bin_mode = static_parameters.pop("bin_mode", None)
        repetitions = static_parameters.pop("repetitions", None)
        node = node_factory.create_node(node_label, qubits, **static_parameters)
        """

        # TODO: This should be in the node initializer
        data_path = create_node_data_path(node)
        # TODO: This should be the refactored such that the node can be run like node.calibrate()
        measurement_result = monitor_node_calibration(
            node, data_path, self.lab_ic, self.measurement_mode
        )

        # TODO MERGE-CZ-GATE: We should discuss the information flow here and see where these return args are used
        return [str(data_path), measurement_result]
