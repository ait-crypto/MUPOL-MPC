import copy
import random
from argparse import Namespace
from logging import Logger
from typing import Any, List

import pytest
import pytest_asyncio
from mpyc.runtime import mpc
from mpyc.sectypes import SecureInteger
from mupol.plaintext.freighters_day_planning.freighter import Freighter
from mupol.plaintext.freighters_day_planning.order import Order
from mupol.plaintext.freighters_day_planning.problem import Problem
from mupol.plaintext.freighters_day_planning.random_problem_generator import (
    RandomProblemGenerator,
)
from mupol.plaintext.freighters_day_planning.truck import Truck

from mupol.mpc.input_uploader import (
    initialize_order,
    initialize_truck,
    prepare_mpc_data,
    upload_order,
    upload_truck,
)
from mupol.mpc.solver import MPCSolver
from mupol.mpc.utils.args_handler import MPCArgsHandler
from mupol.mpc.utils.logger import setup_logger


@pytest.fixture(scope="module")
def args() -> Any:
    return MPCArgsHandler([]).args


@pytest.fixture(scope="module")
def secint(args: Namespace) -> Any:
    return mpc.SecInt(args.bit_length_sectypes)


@pytest.fixture
def plain_problem(args: Namespace) -> Problem:
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
    return problem


@pytest_asyncio.fixture
async def mpc_problem(args: Namespace, plain_problem: Problem) -> Problem:
    problem = copy.deepcopy(plain_problem)
    await prepare_mpc_data(
        problem, args.dummy_freighter_id, args.dummy_node, args.bit_length_sectypes
    )
    return problem


@pytest.fixture
def logger() -> Logger:
    return setup_logger("config/logger_config.ini")


@pytest.fixture
def possible_orders_scalability() -> List[int]:
    return [10, 15]


@pytest.fixture
def possible_trucks_scalability() -> List[int]:
    return [5, 10]


@pytest.fixture
def solver(args: Namespace, mpc_problem: Problem, logger: Logger) -> MPCSolver:
    return MPCSolver(
        mpc_problem,
        args.dummy_freighter_id,
        args.dummy_node,
        args.truck_capacity,
        logger,
    )


@pytest.fixture(scope="module")
def default_freighter() -> Freighter:
    return Freighter()


@pytest.fixture
def default_position(plain_problem: Problem) -> Any:
    return plain_problem.map.positions[0]


@pytest.fixture
def other_position(plain_problem: Problem) -> Any:
    return plain_problem.map.positions[1]


@pytest.fixture(scope="module")
def min_order_volume(args: Namespace) -> Any:
    return args.min_order_volume


@pytest.fixture(scope="module")
def max_capacity(args: Namespace) -> Any:
    return args.truck_capacity


@pytest_asyncio.fixture(scope="function")
async def empty_truck(
    args: Namespace,
    default_freighter: Freighter,
    max_capacity: int,
    default_position: int,
    secint: type,
) -> Truck:
    truck = Truck(
        freighter=default_freighter, capacity=max_capacity, position=default_position
    )
    await upload_truck(truck, secint)
    await initialize_truck(truck, args.dummy_node, secint)
    return truck


@pytest_asyncio.fixture
async def full_truck(empty_truck: Truck, secint: type) -> Truck:
    truck = empty_truck
    truck.capacity = mpc.input(secint(0), senders=0)
    return truck


@pytest_asyncio.fixture
async def small_order(
    args: Namespace,
    default_position: int,
    other_position: int,
    min_order_volume: int,
    secint: type,
) -> Order:
    order = Order(
        origin=default_position, destination=other_position, volume=min_order_volume
    )
    await upload_order(order, secint)
    await initialize_order(order, secint, args.dummy_freighter_id)
    return order


@pytest_asyncio.fixture
async def big_order(small_order: Order, secint: type, max_capacity: int) -> Order:
    order = small_order
    order.volume = mpc.input(secint(max_capacity + 1), senders=0)
    return order


@pytest_asyncio.fixture
async def random_truck_index(plain_problem: Problem, secint: type) -> SecureInteger:
    return mpc.input(secint(random.randrange(len(plain_problem.trucks))), senders=0)


@pytest_asyncio.fixture
async def random_map_position(plain_problem: Problem, secint: type) -> SecureInteger:
    return mpc.input(secint(random.choice(plain_problem.map.positions)), senders=0)


@pytest_asyncio.fixture
async def random_node_indicator_vector(
    plain_problem: Problem, secint: type
) -> List[SecureInteger]:
    plain_indicator_vector = [1] + [0] * (len(plain_problem.map.positions) - 1)
    random.shuffle(plain_indicator_vector)
    indicator_vector = [
        mpc.input(secint(value), senders=0) for value in plain_indicator_vector
    ]
    return indicator_vector
