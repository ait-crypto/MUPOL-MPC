from argparse import Namespace

import pytest
from mupol.plaintext.freighters_day_planning.order import Order
from mupol.plaintext.freighters_day_planning.problem import Problem
from mupol.plaintext.freighters_day_planning.truck import Truck

from mupol.mpc.input_uploader import prepare_mpc_data


@pytest.mark.asyncio
async def test_upload_and_initialize_order(small_order: Order) -> None:
    """
    Initializing this fixture already calls the relevant function
    """
    pass


@pytest.mark.asyncio
async def test_upload_and_initialize_truck(empty_truck: Truck) -> None:
    """
    Initializing this fixture already calls the relevant function
    """
    pass


@pytest.mark.asyncio
async def test_prepare_mpc_data(plain_problem: Problem, args: Namespace) -> None:
    await prepare_mpc_data(
        plain_problem,
        args.dummy_freighter_id,
        args.dummy_node,
        args.bit_length_sectypes,
    )
