"""
Code profiler to evaluate efficiency of the MPC solution.
"""

import itertools
import time
from typing import List

from mpyc.runtime import mpc
from mupol.plaintext.freighters_day_planning.problem import Problem
from mupol.plaintext.freighters_day_planning.random_problem_generator import (
    RandomProblemGenerator,
)

from mupol.mpc.input_uploader import prepare_mpc_data
from mupol.mpc.solver import MPCSolver
from mupol.mpc.utils.args_handler import MPCArgsHandler
from mupol.mpc.utils.logger import setup_logger

POSSIBLE_ORDERS = [10, 100, 1000]
POSSIBLE_TRUCKS = [5, 50, 500]


async def run_profiler(possible_orders: List[int], possible_trucks: List[int]) -> None:
    combined_parameters = itertools.product(possible_orders, possible_trucks)
    args = MPCArgsHandler(["--config=config_scalability.ini"]).args
    logger = setup_logger(args.logger_config)
    await mpc.start()
    for num_orders, num_trucks in combined_parameters:
        generator = RandomProblemGenerator(
            num_freighters=args.num_freighters,
            min_num_trucks=num_trucks,
            max_num_trucks=num_trucks,
            truck_capacity=args.truck_capacity,
            num_orders=num_orders,
            min_order_volume=args.min_order_volume,
            max_order_volume=args.max_order_volume,
            random_seed=args.random_seed,
        )
        problem: Problem = generator.get_problem()

        logger.debug("----------------------------------------------------------")
        logger.debug(f"Profiling code for {num_orders} orders and {num_trucks} trucks")

        start_time = time.perf_counter()
        await prepare_mpc_data(
            problem,
            args.dummy_freighter_id,
            args.dummy_node,
            args.bit_length_sectypes,
        )
        stop_time = time.perf_counter()
        logger.debug("Time for uploading MPC data: %s", stop_time - start_time)

        solver = MPCSolver(
            problem,
            args.dummy_freighter_id,
            args.dummy_node,
            args.truck_capacity,
            logger,
        )
        await solver.solve_problem()
        logger.debug("----------------------------------------------------------")
    await mpc.shutdown()


if __name__ == "__main__":
    mpc.run(
        run_profiler(possible_orders=POSSIBLE_ORDERS, possible_trucks=POSSIBLE_TRUCKS)
    )
