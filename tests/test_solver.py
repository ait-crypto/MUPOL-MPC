from argparse import Namespace
from typing import List

import pytest
from mpyc.runtime import mpc
from mpyc.sectypes import SecureInteger
from mupol.plaintext.freighters_day_planning.order import Order
from mupol.plaintext.freighters_day_planning.problem import Problem
from mupol.plaintext.freighters_day_planning.truck import Truck

from mupol.mpc.solver import EmptyDrive, MPCSolver


@pytest.mark.asyncio
async def test_empty_drive(plain_problem: Problem, mpc_problem: Problem) -> None:
    """
    Simply instantiate an EmptyDrive object by picking the first freighter and
    first and last nodes of the map, first with plaintext and then with
    secret-shared data
    """
    EmptyDrive(
        plain_problem.freighters[0],
        plain_problem.map.positions[0],
        plain_problem.map.positions[-1],
    )
    EmptyDrive(
        mpc_problem.freighters[0],
        mpc_problem.map.positions[0],
        mpc_problem.map.positions[-1],
    )


@pytest.mark.asyncio
async def test_create_empty_truck_drive(solver: MPCSolver) -> None:
    await solver._create_empty_truck_drive()


@pytest.mark.asyncio
async def test_fill_truck_with_compatible_order(
    empty_truck: Truck, small_order: Order, solver: MPCSolver
) -> None:
    """
    Fill empty truck with compatible order
    """
    await solver._fill_truck_with_order(empty_truck, small_order)
    assert await mpc.output(empty_truck.destination) == await mpc.output(
        small_order.destination
    )
    assert await mpc.output(small_order.freighter_id) == await mpc.output(
        empty_truck.freighter_id
    )


@pytest.mark.asyncio
async def test_fill_truck_with_incompatible_order(
    args: Namespace,
    empty_truck: Truck,
    small_order: Order,
    other_position: int,
    solver: MPCSolver,
    secint: type,
) -> None:
    """
    Fill empty truck with incompatible order
    """
    small_order.origin = mpc.input(secint(other_position), senders=0)
    await solver._fill_truck_with_order(empty_truck, small_order)
    assert await mpc.output(small_order.freighter_id) == args.dummy_freighter_id


@pytest.mark.asyncio
async def test_fill_full_truck_with_order(
    args: Namespace, full_truck: Truck, small_order: Order, solver: MPCSolver
) -> None:
    """
    Fill full truck with order
    """
    await solver._fill_truck_with_order(full_truck, small_order)
    assert await mpc.output(small_order.freighter_id) == args.dummy_freighter_id


@pytest.mark.asyncio
async def test_fill_truck_with_big_order(
    args: Namespace, full_truck: Truck, big_order: Order, solver: MPCSolver
) -> None:
    """
    Fill full truck with order
    """
    await solver._fill_truck_with_order(full_truck, big_order)
    assert await mpc.output(big_order.freighter_id) == args.dummy_freighter_id


@pytest.mark.asyncio
async def test_fill_trucks(solver: MPCSolver) -> None:
    await solver._fill_trucks()


@pytest.mark.asyncio
async def test_find_distances_to_order(
    mpc_problem: Problem,
    random_node_indicator_vector: List[SecureInteger],
    solver: MPCSolver,
) -> None:
    """
    Find distance of trucks from random node
    """
    await solver._find_distances_to_order(random_node_indicator_vector)


@pytest.mark.asyncio
async def test_find_freighter_id(
    random_truck_index: SecureInteger, solver: MPCSolver
) -> None:
    """
    Find freighter ID of random truck
    """
    freighter_id = await solver._find_freighter_id(random_truck_index)
    plain_index = await mpc.output(random_truck_index)
    assert await mpc.output(
        solver.trucks[plain_index].freighter_id
    ) == await mpc.output(freighter_id)


@pytest.mark.asyncio
async def test_find_truck_dist_to_order(
    mpc_problem: Problem,
    random_node_indicator_vector: List[SecureInteger],
    empty_truck: Truck,
    solver: MPCSolver,
    secint: type,
) -> None:
    """
    Find distance of default truck to random node
    """
    route_matrix = mpc_problem.map.compute_route_matrix()
    route_matrix = [
        [mpc.input(secint(entry), senders=0) for entry in row] for row in route_matrix
    ]
    await solver._find_truck_dist_to_order(
        empty_truck, random_node_indicator_vector, route_matrix
    )


@pytest.mark.asyncio
async def test_find_truck_position(
    random_truck_index: SecureInteger, solver: MPCSolver
) -> None:
    """
    Find position of random truck
    """
    await solver._find_truck_position(random_truck_index)


@pytest.mark.asyncio
async def test_locate_first_unprocessed_origin(solver: MPCSolver) -> None:
    """
    Check that function returns unprocessed origin
    """
    first_unprocessed_origin, first_unprocessed_origin_vec = (
        await solver._locate_first_unprocessed_origin()
    )
    first_unprocessed_origin = await mpc.output(first_unprocessed_origin)


@pytest.mark.asyncio
async def test_move_truck(
    random_truck_index: SecureInteger,
    random_map_position: SecureInteger,
    solver: MPCSolver,
) -> None:
    """
    Move random truck to random map position
    """
    await solver._move_truck(random_truck_index, random_map_position)
    random_truck_index = await mpc.output(random_truck_index)
    assert await mpc.output(
        solver.trucks[random_truck_index].position
    ) == await mpc.output(random_map_position)


@pytest.mark.asyncio
async def test_solve(solver: MPCSolver) -> None:
    await solver.solve_problem()
