import sys

from mpyc.runtime import mpc
from mupol.plaintext.freighters_day_planning.problem import Problem
from mupol.plaintext.freighters_day_planning.random_problem_generator import (
    RandomProblemGenerator,
)

from mupol.mpc.input_uploader import prepare_mpc_data
from mupol.mpc.solver import MPCSolver
from mupol.mpc.utils.args_handler import MPCArgsHandler
from mupol.mpc.utils.logger import setup_logger


async def main() -> None:
    args = MPCArgsHandler(sys.argv[1:]).args
    logger = setup_logger(args.logger_config)
    await mpc.start()
    generator = RandomProblemGenerator(
        args.num_freighters,
        args.min_num_trucks,
        args.max_num_trucks,
        args.truck_capacity,
        args.num_orders,
        args.min_order_volume,
        args.max_order_volume,
        args.random_seed,
    )
    problem: Problem = generator.get_problem()

    logger.debug("Uploading data in MPC")
    await prepare_mpc_data(
        problem, args.dummy_freighter_id, args.dummy_node, args.bit_length_sectypes
    )

    logger.debug("Running solver")
    solver = MPCSolver(
        problem, args.dummy_freighter_id, args.dummy_node, args.truck_capacity, logger
    )
    await solver.solve_problem()

    await mpc.shutdown()


if __name__ == "__main__":
    mpc.run(main())
