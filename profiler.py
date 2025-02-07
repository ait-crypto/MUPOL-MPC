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

POSSIBLE_ORDERS = [500]
POSSIBLE_TRUCKS = [1, 2, 3, 4, 5]
POSSIBLE_FREIGHTERS = [1]
POSSIBLE_MAX_ORDER_VOLUMES = [10, 20, 32]
NUM_EXPERIMENTS = 1


async def run_profiler(
    possible_orders: List[int],
    possible_trucks: List[int],
    possible_freighters: List[int],
    possible_max_order_volumes: List[int],
    num_experiments: int,
) -> None:
    combined_parameters = itertools.product(
        possible_orders,
        possible_trucks,
        possible_freighters,
        possible_max_order_volumes,
    )
    args = MPCArgsHandler(["--config=config_scalability.ini"]).args
    logger = setup_logger(args.logger_config)

    logger.debug(f"Number of experiments: {num_experiments}")
    for num_orders, num_trucks, num_freighters, max_order_volume in combined_parameters:
        i = 0
        for i in range(num_experiments):
            generator = RandomProblemGenerator(
                num_freighters=num_freighters,
                min_num_trucks=num_trucks,
                max_num_trucks=num_trucks,
                truck_capacity=args.truck_capacity,
                num_orders=num_orders,
                min_order_volume=args.min_order_volume,
                max_order_volume=max_order_volume,
                random_seed=args.random_seed,
            )
            problem: Problem = generator.get_problem()

            logger.debug("----------------------------------------------------------")
            logger.debug(
                f"Profiling code for {num_orders} orders and "
                f"{args.num_freighters * num_trucks} trucks (total)"
            )
            logger.debug(f"Iteration number {i}")

            start_time = time.perf_counter()
            await mpc.start()
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
                args.use_priorities,
                args.test_mode,
                logger,
                args.norm_weight,
            )
            await solver.solve_problem()
            logger.debug("----------------------------------------------------------")
            i += 1
            time.sleep(5)  # Some buffer to ensure MPyC shuts down correctly
            await mpc.shutdown()
        logger.debug("==========================================================")


if __name__ == "__main__":
    mpc.run(
        run_profiler(
            possible_orders=POSSIBLE_ORDERS,
            possible_trucks=POSSIBLE_TRUCKS,
            possible_freighters=POSSIBLE_FREIGHTERS,
            possible_max_order_volumes=POSSIBLE_MAX_ORDER_VOLUMES,
            num_experiments=NUM_EXPERIMENTS,
        )
    )
