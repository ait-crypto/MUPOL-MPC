"""
This module contains all classes and functions to solve a MUPOL problem instance with
MPyC.
"""

import logging
import time
from typing import List, Tuple

from mpyc.runtime import mpc
from mpyc.sectypes import SecureInteger
from mupol.plaintext.freighters_day_planning.freighter import Freighter
from mupol.plaintext.freighters_day_planning.map import Map
from mupol.plaintext.freighters_day_planning.order import Order
from mupol.plaintext.freighters_day_planning.problem import Problem
from mupol.plaintext.freighters_day_planning.truck import Truck

from mupol.mpc.utils.mpyc_vector_functions import (
    compute_indicator_vector,
    find_first_non_zero,
    real_or,
)


class EmptyDrive:
    """Data class for an MPC-style empty truck drive."""

    def __init__(
        self,
        freighter_id: SecureInteger,
        closest_position: SecureInteger,
        first_unprocessed_origin: SecureInteger,
    ):
        """Constructor method.

        :param freighter_id: ID of the freighter associated to truck drive
        :param closest_position: position of truck closest to order to be picked up
        :param first_unprocessed_origin: location of the first yet-to-be-processed
        order
        """
        self.freighter_id = freighter_id
        self.closest_position = closest_position
        self.first_unprocessed_origin = first_unprocessed_origin


class MPCSolver:
    """Class for MUPOL MPC solver."""

    def __init__(
        self,
        problem: Problem,
        dummy_freighter_id: int,
        dummy_node: int,
        truck_capacity: int,
        logger: logging.Logger,
    ):
        """Constructor method.

        :param problem: the MUPOL problem object to be solved
        :param dummy_freighter_id: the ID used for dummy freighters (i.e., to indicate
        a non-assigned order)
        :param dummy_node: the ID used for a dummy node (e.g., to indicate that a truck
        has no destination set yet)
        :param truck_capacity: the maximum capacity of the trucks
        :param logger: the logger, duh
        """
        self.trucks = problem.trucks
        self.orders = problem.orders
        self.freighters: Freighter = problem.freighters
        self.map: Map = problem.map
        self.empty_drives: List[EmptyDrive] = []
        self.dummy_freighter_id = dummy_freighter_id
        self.dummy_node = dummy_node
        self.truck_capacity = truck_capacity
        self.num_processed_orders: int = 0
        self.secure_node_type = type(self.orders[0].origin)
        self.logger = logger

    async def _fill_truck_with_order(self, truck: Truck, order: Order) -> None:
        """Assign a given order to a given truck, if the two are compatible.

        :param truck: the given truck object
        :param order: the given order object
        """
        equal_positions = mpc.eq(truck.position, order.origin)
        # Check that truck has no destination or same destination as order
        destinations_compatible = await real_or(
            mpc.eq(truck.destination, self.dummy_node),
            mpc.eq(truck.destination, order.destination),
        )
        # Check that truck still has enough space and that order is still open
        positive_capacity = mpc.ge(truck.capacity - order.volume, 0)
        order_is_open = 1 - order.processed
        # Put it all together
        compatible = (
            equal_positions
            * destinations_compatible
            * positive_capacity
            * order_is_open
        )

        # Update truck destination
        truck.destination = mpc.if_else(
            compatible, order.destination, truck.destination
        )
        # Update flags and variables
        order.processed = await real_or(compatible, order.processed)
        order.process_this_round = await real_or(compatible, order.process_this_round)
        order.freighter_id = mpc.if_else(
            compatible, truck.freighter_id, order.freighter_id
        )
        truck.capacity -= order.volume * compatible

    async def _fill_trucks(self) -> None:
        """Assign all orders to the compatible trucks."""
        start_time_filling = time.perf_counter()
        for truck in self.trucks:
            for order in self.orders:
                await self._fill_truck_with_order(truck, order)
            truck.capacity = self.truck_capacity
            truck.position = mpc.if_else(
                (1 - mpc.eq(truck.destination, self.dummy_node)),
                truck.destination,
                truck.position,
            )
            # Reset truck destination to dummy.
            # This could be plaintext, but due to an MPyC quirk it has to be
            # of secret-shared type (otherwise it might be compared with
            # another plaintext (dummy destination) with an mpc.eq method,
            # which throws an error
            truck.destination = mpc.input(
                self.secure_node_type(self.dummy_node), senders=0
            )
        end_time_filling = time.perf_counter()
        self.logger.debug(
            "Elapsed time for the filling of trucks: %s",
            end_time_filling - start_time_filling,
        )

    async def _locate_first_unprocessed_origin(
        self,
    ) -> Tuple[SecureInteger, List[SecureInteger]]:
        """
        Locate origin of first non-processed order.

        :return: the position of the first non-processed order, together with its
        indicator-vector representation
        """
        unprocessed_indexes = [1 - order.processed for order in self.orders]
        first_unprocessed_index = await find_first_non_zero(unprocessed_indexes)
        first_unprocessed_origin = mpc.in_prod(
            [order.origin for order in self.orders], first_unprocessed_index
        )
        first_unprocessed_origin_vec = await compute_indicator_vector(
            len(self.map.positions), first_unprocessed_origin
        )
        return first_unprocessed_origin, first_unprocessed_origin_vec

    async def _find_distances_to_order(
        self, node_indicator_vector: List[SecureInteger]
    ) -> None:
        """
        Perform a secure look-up to find distances (cost) all trucks from a given
        order.

        :param node_indicator_vector: the indicator vector of the desired node.
        """
        route_matrix = self.map.compute_route_matrix()
        # In theory, this matrix could be plaintext, but MPyC would then
        # be unable to properly handle matrix operations.
        # We assume that the cost of a route would have the same bit-size
        # of a node, which might not strictly be true, but works fine as
        # long as we don't keep the bit-length of the nodes too low.
        route_matrix = [
            [mpc.input(self.secure_node_type(entry), senders=0) for entry in row]
            for row in route_matrix
        ]
        for truck in self.trucks:
            await self._find_truck_dist_to_order(
                truck=truck,
                node_indicator_vector=node_indicator_vector,
                route_matrix=route_matrix,
            )

    async def _find_truck_dist_to_order(
        self,
        truck: Truck,
        node_indicator_vector: List[SecureInteger],
        route_matrix: List[List[SecureInteger]],
    ) -> None:
        """
        Perform a secure look-up to find distance (cost) of a given truck from a given
        order.

        :param truck: the truck object
        :param node_indicator_vector: the node, expressed as an indicator vector
        :param route_matrix: the matrix expressing the node graph
        """
        truck_position_vec = await compute_indicator_vector(
            len(self.map.positions), truck.position
        )

        # mpc.matrix_prod will return a 1-by-1 matrix, we only pick the value
        # of the only entry
        truck.dist_to_order = mpc.matrix_prod(
            [truck_position_vec],
            mpc.matrix_prod(route_matrix, [node_indicator_vector], tr=True),
        )[0][0]

    async def _find_truck_position(self, truck_index: SecureInteger) -> SecureInteger:
        """
        Finds the position of the i-th truck.

        :param truck_index: the index of the truck to be located
        :return: the position of the truck at the truck_index-position
        """
        position = self.dummy_node  # Initialization
        for other_truck_index in range(len(self.trucks)):
            position = mpc.if_else(
                mpc.eq(other_truck_index, truck_index),
                self.trucks[other_truck_index].position,
                position,
            )
        return position

    async def _move_truck(
        self, truck_index: SecureInteger, destination: SecureInteger
    ) -> None:
        """
        Set the destination method of a truck at a given index to a given node.

        :param truck_index: the index of the truck to be assigned
        :param destination: the desired node to be assigned as destination to the truck
        """
        for other_truck_index in range(len(self.trucks)):
            self.trucks[other_truck_index].position = mpc.if_else(
                mpc.eq(other_truck_index, truck_index),
                destination,
                self.trucks[other_truck_index].position,
            )

    async def _find_freighter_id(self, truck_index: SecureInteger) -> SecureInteger:
        """
        Return the freighter ID of a truck at a given index

        :param truck_index: the index of the desired truck
        :return: the freighter ID of the truck with index truck_index
        """
        freighter_id = self.dummy_freighter_id  # Initialization
        for other_truck_index in range(len(self.trucks)):
            freighter_id = mpc.if_else(
                mpc.eq(other_truck_index, truck_index),
                self.trucks[other_truck_index].freighter_id,
                freighter_id,
            )
        return freighter_id

    async def _create_empty_truck_drive(self) -> None:
        """Function to create an empty truck drive."""
        start_time_create_empty = time.perf_counter()

        # Locate origin of first non-processed order.
        self.logger.debug("Locating first unprocessed origin")
        first_unprocessed_origin, first_unprocessed_origin_vec = (
            await self._locate_first_unprocessed_origin()
        )

        # Perform a secure look-up to find distance (cost) of each truck to
        # first unprocessed order
        self.logger.debug("Finding distance of each truck to first unprocessed order")
        await self._find_distances_to_order(first_unprocessed_origin_vec)

        # Compute secure argmin to identify closest truck
        # It seems mpc.argmin actually returns both argmin and min as a tuple,
        # we are only interested in the argmin
        self.logger.debug("Identifying closest truck to first unprocessed order")
        closest_truck_index = mpc.argmin(
            [truck.dist_to_order for truck in self.trucks]
        )[0]

        # Identify position of closest truck and freigher ID
        self.logger.debug("Obtaining truck position of closest truck")
        closest_position = await self._find_truck_position(
            truck_index=closest_truck_index
        )
        self.logger.debug("Obtaining freigther ID of closest truck")
        freighter_id = await self._find_freighter_id(truck_index=closest_truck_index)

        # Update empty drive list accordingly
        self.logger.debug("Creating relevant truck drive")
        empty_drive = EmptyDrive(
            freighter_id, closest_position, first_unprocessed_origin
        )
        self.empty_drives.append(empty_drive)

        # Move truck
        self.logger.debug("Updating truck location")
        await self._move_truck(
            truck_index=closest_truck_index,
            destination=first_unprocessed_origin,
        )
        end_time_create_empty = time.perf_counter()
        self.logger.debug(
            "Elapsed time for creation of empty truck ride: %s",
            end_time_create_empty - start_time_create_empty,
        )

    async def solve_problem(self) -> None:
        """Solver function."""
        self.logger.debug(
            "Running solver for %s orders, %s trucks, %s freighters",
            len(self.orders),
            len(self.trucks),
            len(self.freighters),
        )
        start_time_solver = time.perf_counter()
        while self.num_processed_orders < len(self.orders):
            self.logger.info("Filling trucks...")
            self.logger.info(
                "Orders to go: %s", len(self.orders) - self.num_processed_orders
            )
            await self._fill_trucks()

            num_added_orders = sum(order.process_this_round for order in self.orders)
            num_added_orders = await mpc.output(num_added_orders)  # Revealed!
            self.logger.debug("Orders processed in this round: %s", num_added_orders)

            if num_added_orders == 0:
                self.logger.info("Creating empty truck drive...")
                await self._create_empty_truck_drive()

            # Reset order status for next round
            for order in self.orders:
                order.process_this_round = 0

            self.num_processed_orders += num_added_orders

        for order in self.orders:
            self.logger.info("Revealing order %s", order.id)
            freighter_id = await mpc.output(order.freighter_id)
            self.logger.info("Freighter: %s", freighter_id)
            # TODO: Reveal order info only to MPC party controlling relevant freighter
            await mpc.output(order.origin, receivers=0)
            await mpc.output(order.destination, receivers=0)
            await mpc.output(order.volume, receivers=0)
            # Test only!
            self.logger.debug("Origin: %s", await mpc.output(order.origin))
            self.logger.debug("Destination: %s", await mpc.output(order.destination))
            self.logger.debug("Volume: %s", await mpc.output(order.volume))

        for empty_drive in self.empty_drives:
            freighter_id = await mpc.output(empty_drive.freighter_id)
            # TODO: Reveal order info only to MPC party controlling relevant freighter
            await mpc.output(empty_drive.closest_position, receivers=0)
            await mpc.output(empty_drive.first_unprocessed_origin, receivers=0)
            # Test only!
            self.logger.debug(
                "Revealing empty drive: %s %s",
                await mpc.output(empty_drive.closest_position),
                await mpc.output(empty_drive.first_unprocessed_origin),
            )
        end_time_solver = time.perf_counter()
        self.logger.debug(
            "Total elapsed time for solving: %s", end_time_solver - start_time_solver
        )
