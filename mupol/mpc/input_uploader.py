"""
This module contains the functions to upload the input data to the MPyC framework.
"""

from mpyc.runtime import mpc
from mupol.plaintext.freighters_day_planning.order import Order
from mupol.plaintext.freighters_day_planning.problem import Problem
from mupol.plaintext.freighters_day_planning.truck import Truck


async def upload_order(order: Order, secint: type) -> None:
    """Function to secret-share a single order object.

    :param order: the order to be secret-shared
    :param secint: the desired type of MPyC secret sharing
    """
    async with mpc:
        order.origin = mpc.input(secint(order.origin), senders=mpc.pid)
        order.destination = mpc.input(secint(order.destination), senders=mpc.pid)
        order.volume = mpc.input(secint(order.volume), senders=mpc.pid)


async def initialize_order(order: Order, secint: type, dummy_freighter_id: int) -> None:
    """Set initial order variables.

    :param order: the relevant order object
    :param secint: the desired type of the MPyC secret-shared values
    :param dummy_freighter_id: which value to use for order with no freighter assigned
    """
    async with mpc:
        order.processed = mpc.input(secint(0), senders=mpc.pid)
        order.process_this_round = mpc.input(secint(0), senders=mpc.pid)
        order.freighter_id = mpc.input(secint(dummy_freighter_id), senders=mpc.pid)


async def upload_truck(truck: Truck, secint: type) -> None:
    """Function to secret-share a single truck object.

    :param truck: the truck to be secret-shared
    :param secint: the desired type of MPyC secret sharing
    """
    async with mpc:
        truck.capacity = mpc.input(secint(truck.capacity), senders=mpc.pid)
        truck.position = mpc.input(secint(truck.position), senders=mpc.pid)
        truck.freighter_id = mpc.input(secint(truck.freighter.id), senders=mpc.pid)


async def initialize_truck(truck: Truck, dummy_node: int, secint: type) -> None:
    """Set initial truck variables.

    :param truck: the relevant truck object
    :param dummy_node: which value to use for truck with no destination assigned
    :param secint: the desired type of the MPyC secret-shared values
    """
    async with mpc:
        truck.destination = mpc.input(secint(dummy_node), senders=mpc.pid)


async def prepare_mpc_data(
    problem: Problem, dummy_freighter_id: int, dummy_node: int, bit_length: int
) -> None:
    """Secret-share the input data in MPyC.

    :param problem: the Problem object
    :param dummy_freighter_id: which value to use for order with no freighter assigned
    :param dummy_node: which value to use for truck with no destination assigned
    :bit_length: the maximum bit length of the values to be secret-shared
    """
    secint = mpc.SecInt(bit_length)
    async with mpc:
        for order in problem.orders:
            await upload_order(order, secint)
            await initialize_order(order, secint, dummy_freighter_id)
        for truck in problem.trucks:
            await upload_truck(truck, secint)
            await initialize_truck(truck, dummy_node, secint)
