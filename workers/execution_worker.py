'''Retrieve the compiled schedule and run it'''
from quantify_scheduler.instrument_coordinator.instrument_coordinator import CompiledSchedule
from quantify_scheduler.json_utils import pathlib
from logger.tac_logger import logger
from utilities.status import ClusterStatus
from workers.measurement_utils import MeasurementFactory
from calibration_schedules.time_of_flight import measure_time_of_flight
import redis

redis_connection = redis.Redis(decode_responses=True)

def measure_node(
    node,
    compiled_schedule: CompiledSchedule,
    lab_ic,
    data_path: pathlib.Path,
    cluster_status=ClusterStatus.real
    ):

    # the factory determines if the measurement is on single qubits or a coupler is involved
    factory = MeasurementFactory()
    measurement = factory.select(node)
    result_dataset = measurement.measure(node, compiled_schedule, lab_ic, data_path)

    logger.info('Finished measurement')
    return result_dataset
