"""
This module contains the classes and functions to solve a MUPOL problem instance with
MPyC.
"""

import logging
import time
from typing import List, Optional, Tuple

from mpyc.runtime import mpc
from mpyc.sectypes import SecureInteger
from mupol.plaintext.freighters_day_planning.freighter import Freighter
from mupol.plaintext.freighters_day_planning.map import Map
from mupol.plaintext.freighters_day_planning.order import Order
from mupol.plaintext.freighters_day_planning.problem import Problem
from mupol.plaintext.freighters_day_planning.simple_solver import SimpleSolver
from mupol.plaintext.freighters_day_planning.truck import Truck

from mupol.mpc.utils.mpyc_vector_functions import real_or


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
        use_priorities: int,
        test_mode: int,
        logger: logging.Logger,
        norm_weight: Optional[float] = None,
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
        self.problem = problem
        self.trucks = problem.trucks
        self.orders = problem.orders
        self.freighters: Freighter = problem.freighters
        self.map: Map = problem.map
        self.dummy_freighter_id = dummy_freighter_id
        self.dummy_node = dummy_node
        self.truck_capacity = truck_capacity
        self.num_processed_orders: int = 0
        self.secure_node_type = type(self.orders[0].origin)
        self.logger = logger

        :param truck_drive: a TruckDrive object, possibly containing secret-shared
        objects
        """
        # TODO: write test for this
        if not isinstance(truck_drive.origin, int):
            truck_drive.origin = await mpc.output(truck_drive.origin)
        if not isinstance(truck_drive.destination, int):
            truck_drive.destination = await mpc.output(truck_drive.destination)
        if not isinstance(truck_drive.truck.capacity, int):
            truck_drive.truck.capacity = await mpc.output(truck_drive.truck.capacity)
        for order in truck_drive.orders:
            if not isinstance(order.volume, int):
                order.volume = await mpc.output(order.volume)
            if not isinstance(order.priority, int):
                order.priority = await mpc.output(order.priority)

    async def _fill_truck_with_order(
        self, truck: Truck, order: Order, truck_drive: Optional[TruckDrive] = None
    ) -> None:
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

        # In test mode, reveal whether order is compatible with truck and, if so, add
        # it to the truck drive
        if self.test_mode == 1 and truck_drive is not None:
            compatible_plain = await mpc.output(compatible)
            if compatible_plain == 1:
                truck_drive.orders.append(order)
                self.logger.debug(
                    "Order with ID %s assigned to truck drive",
                    await mpc.output(order.id),
                )

    async def _fill_trucks(self) -> None:
        """Assign all orders to the compatible trucks."""
        start_time_filling = time.perf_counter()
        for truck in self.trucks:
            # self.logger.debug("Filling truck with compatible orders...")
            if self.test_mode == 1:
                # Truck drives are created for validation and computation of quality
                # metrics.
                truck_drive = TruckDrive(truck, None, None, 0, 0)
            else:
                truck_drive = None
            for order in self.orders:
                await self._fill_truck_with_order(truck, order, truck_drive)

            if self.test_mode == 1:
                # We reveal the truck capacity to check whether this truck is able to
                # pick up orders or not.
                # If so, we update the truck drive with the relevant fields and add it
                # to the solution
                current_truck_capacity = await mpc.output(truck.capacity)
                if current_truck_capacity < self.truck_capacity:
                    current_truck_position = await mpc.output(truck.position)
                    current_truck_destination = await mpc.output(truck.destination)
                    truck_drive.origin = current_truck_position
                    truck_drive.destination = current_truck_destination
                    truck_drive.end = self.problem.map.get_costs(
                        current_truck_position, current_truck_destination
                    )
                    self.solution.append(truck_drive)

            # Reset truck position
            truck.position = mpc.if_else(
                (1 - mpc.eq(truck.destination, self.dummy_node)),
                truck.destination,
                truck.position,
            )

            # Reset truck destination to dummy.
            # This could be plaintext, but due to an MPyC quirk it has to be
            # of secret-shared type (otherwise it might be compared with
            # another plaintext (dummy destination) with an mpc.eq method,
            # which throws an error)
            truck.destination = mpc.input(
                self.secure_node_type(self.dummy_node), senders=0
            )

            # Reset truck capacity
            truck.capacity = self.truck_capacity

            # MPC barrier to avoid out-of-bound memory usage
            # Notice: for smaller problem instances (dozens of trucks/orders), this
            # barrier is probably not needed, and might slow down the solution.
            # Unfortunately, user will need trial-and-error to see if this line is
            # necessary.
            await mpc.barrier()

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
        first_unprocessed_index = mpc.unit_vector(
            mpc.find(unprocessed_indexes, 1), len(unprocessed_indexes)
        )
        first_unprocessed_origin = mpc.in_prod(
            [order.origin for order in self.orders], first_unprocessed_index
        )
        first_unprocessed_origin_vec = mpc.unit_vector(
            first_unprocessed_origin, len(self.map.positions)
        )
        return first_unprocessed_origin, first_unprocessed_origin_vec

    async def _find_distances_to_order(
        self, node_indicator_vector: List[SecureInteger]
    ) -> None:
        """
        Perform a secure look-up to find distances (cost) of all trucks from a
        given order.

        :param node_indicator_vector: the indicator vector of the desired node.
        """
        if self._route_matrix is None:
            self._route_matrix = self.map.compute_route_matrix()

            # In theory, this matrix could be plaintext, but MPyC would then
            # be unable to properly handle matrix operations.
            # We assume that the cost of a route would have the same bit-size
            # of a node, which might not strictly be true, but works fine as
            # long as we don't keep the bit-length of the nodes too low.
            self._route_matrix = [
                [mpc.input(self.secure_node_type(entry), senders=0) for entry in row]
                for row in self._route_matrix
            ]
        for truck in self.trucks:
            await self._find_truck_dist_to_order(
                truck=truck,
                node_indicator_vector=node_indicator_vector,
            )

    async def _find_truck_dist_to_order(
        self,
        truck: Truck,
        node_indicator_vector: List[SecureInteger],
    ) -> None:
        """
        Perform a secure look-up to find distance (cost) of a given truck from a given
        order.

        :param truck: the truck object
        :param node_indicator_vector: the node, expressed as an indicator vector
        """
        truck_position_vec = await compute_indicator_vector(
            len(self.map.positions), truck.position
        )

        # mpc.matrix_prod will return a 1-by-1 matrix, we only pick the value
        # of the only entry
        truck.dist_to_order = mpc.matrix_prod(
            [truck_position_vec],
            mpc.matrix_prod(self._route_matrix, [node_indicator_vector], tr=True),
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

        if self.test_mode == 1:
            closest_truck_index_plain = await mpc.output(closest_truck_index)
            self.solution.append(
                TruckDrive(
                    self.trucks[closest_truck_index_plain],
                    self.trucks[closest_truck_index_plain].position,
                    await mpc.output(first_unprocessed_origin),
                    0,
                    self.problem.map.get_costs(
                        await mpc.output(
                            self.trucks[closest_truck_index_plain].position
                        ),
                        await mpc.output(first_unprocessed_origin),
                    ),
                )
            )

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

    def _get_priority(self, order: List[SecureInteger]) -> SecureInteger:
        """Return last item of a list of secret-shared integers (assumes that priority
        is stored in last position)
        """
        return order[-1]

    async def _sort_orders(self) -> None:
        """Securely sort the orders by priority, using MPyC built-in method"""
        start_time_sorting = time.perf_counter()

        # Convert order objects to lists, so that we can use the MPyC sorting method
        # Step 1: convert to dictionary
        dict_orders = [order.__dict__ for order in self.orders]
        for dict_order in dict_orders:
            # When sorting a list, MPyC does not like None values.
            # In our case, since freighters will be unassigned at this point,
            # we therefore remove the 'freighter' key (which has value equal
            # to None)
            del dict_order["freighter"]

        # Step 2: now that we have removed None entries, convert to list of values
        listed_orders = [list(dict_order.values()) for dict_order in dict_orders]

        # Step 3: sort according to priorities using MPyC built-in method
        sorted_orders = mpc.sorted(listed_orders, self._get_priority, reverse=True)

        # Step 4: rewrite order list.
        for index in range(len(self.orders)):
            self.orders[index].id = sorted_orders[index][0]
            self.orders[index].volume = sorted_orders[index][1]
            self.orders[index].origin = sorted_orders[index][2]
            self.orders[index].destination = sorted_orders[index][3]
            self.orders[index].freighter_id = sorted_orders[index][4]
            self.orders[index].processed = sorted_orders[index][5]
            self.orders[index].process_this_round = sorted_orders[index][6]
            self.orders[index].priority = sorted_orders[index][7]

        end_time_sorting = time.perf_counter()
        self.logger.debug(
            "Time elapsed for sorting the orders: %s",
            end_time_sorting - start_time_sorting,
        )

    async def _reveal_solution_quality(self) -> None:
        """Compute and log some information on the quality of the MPC solution."""
        # TODO: write tests for this method
        self.logger.info("Truck drives:")
        # Produce relevant information
        index = 0
        for truck_drive in self.solution:
            await self._reveal_truck_drive_details(truck_drive)
            self.logger.info("Truck drive %s: %s", index, str(truck_drive))
            index += 1
        # Compute some metrics
        plain_solver = SimpleSolver()
        alpha = self.norm_weight

        if alpha != 0:
            empty_km_norm = plain_solver.get_empty_km_norm(self.solution)
            self.logger.info("Empty-kilometer norm: %s", empty_km_norm)
            if alpha != 1:
                # Unfortunately, the get_swap_norm function might attempt a
                # division by 0. We check here to avoid errors
                if plain_solver.get_swaps_max(self.solution) != 0:
                    swap_norm = plain_solver.get_swap_norm(self.solution)
                else:
                    swap_norm = 1
                    self.logger.info("Perfect priority ordering")
                self.logger.info("Swap norm: %s", swap_norm)
                weighted_sum = alpha * empty_km_norm + (1 - alpha) * swap_norm
            else:
                weighted_sum = empty_km_norm
        else:
            # Unfortunately, the get_swap_norm function might attempt a
            # division by 0. We check here to avoid errors
            if plain_solver.get_swaps_max(self.solution) != 0:
                swap_norm = plain_solver.get_swap_norm(self.solution)
            else:
                swap_norm = 1
                self.logger.info("Perfect priority ordering")
            self.logger.info("Swap norm: %s", swap_norm)
            weighted_sum = swap_norm

        self.logger.info("Weighted sum with weight %s: %s", alpha, weighted_sum)

    async def _reveal_order_publicly(self, order: Order) -> None:
        """Function to reveal order details to all parties. Output is saved in logger

        :param order: the order to be revealed.
        """
        # TODO: write tests for this method
        self.logger.debug("Origin: %s", await mpc.output(order.origin))
        self.logger.debug("Destination: %s", await mpc.output(order.destination))
        self.logger.debug("Volume: %s", await mpc.output(order.volume))
        self.logger.debug("Priority: %s", order.priority)

    async def _reveal_order_to_party(self, order: Order, party_index: int = 0) -> None:
        """Function to reveal order details to a specific party only.
        Output is saved in logger.

        :param order: the order object to be revealed.
        :param party_index: the index of the party that will obtain the information.
        """
        # TODO: write tests for this method
        await mpc.output(order.origin, receivers=party_index)
        await mpc.output(order.destination, receivers=party_index)
        # await mpc.output(order.priority, receivers=party_index)

    async def _reveal_empty_drive_publicly(self, empty_drive: EmptyDrive) -> None:
        """Reveal details of an empty truck ride to all parties.

        :param empty_drive: the empty truck drive object to be revealed.
        """
        # TODO: write tests for this method
        self.logger.debug(
            "Empty drive: %s %s",
            await mpc.output(empty_drive.closest_position),
            await mpc.output(empty_drive.first_unprocessed_origin),
        )

    async def _reveal_empty_drive_to_party(
        self, empty_drive: EmptyDrive, party_index: int = 0
    ) -> None:
        """Reveal details of an empty truck ride to a single party.

        :param empty_drive: the empty truck drive object to be revealed.
        :param party_index: the index of the party who will get the information.
        """
        # TODO: write tests for this method
        await mpc.output(empty_drive.closest_position, receivers=party_index)
        await mpc.output(empty_drive.first_unprocessed_origin, receivers=party_index)

    async def _reveal_solution(self) -> None:
        """Reveal the solution, either a) only to the parties that are supposed to
        lear it, or b) to all parties for debugging and validation purposes.
        Notice that in its current state, in case a) we actually always reveal the
        solution to the first party. This is sufficient for the purposes of this
        proof-of-concept, but will of course need to be modified for higher TRL or more
        realistic experiments.
        """
        # TODO: write tests for this method
        index = 0
        for order in self.orders:
            self.logger.info("Revealing order number %s (not order id!)", index)
            freighter_id = await mpc.output(order.freighter_id)
            self.logger.info("Freighter: %s", freighter_id)
            if self.test_mode == 1:
                await self._reveal_order_publicly(order)
            else:
                # Currently, we reveal this information to the first party
                await self._reveal_order_to_party(order, 0)
            index += 1
        index = 0
        for empty_drive in self.empty_drives:
            self.logger.info("Revealing empty drive %s", index)
            freighter_id = await mpc.output(empty_drive.freighter_id)
            if self.test_mode == 1:
                await self._reveal_empty_drive_publicly(empty_drive)
            else:
                # Currently, we reveal this information to the first party
                await self._reveal_empty_drive_to_party(empty_drive, 0)
            index += 1
        if self.test_mode == 1:
            await self._reveal_solution_quality()

    async def solve_problem(self) -> None:
        """Solver function."""
        self.logger.debug(
            "Running solver for %s orders, %s trucks, %s freighters",
            len(self.orders),
            len(self.trucks),
            len(self.freighters),
        )
        start_time_solver = time.perf_counter()
        if self.use_priorities == 1:
            self.logger.info("Sorting orders according to priority...")
            await self._sort_orders()
        while self.num_processed_orders < len(self.orders):
            self.logger.info(
                "Orders to go: %s", len(self.orders) - self.num_processed_orders
            )
            await self._fill_trucks()
            await mpc.barrier()

            num_added_orders = sum(order.process_this_round for order in self.orders)
            num_added_orders = await mpc.output(num_added_orders)  # Revealed!
            self.logger.debug("Orders processed in this round: %s", num_added_orders)

            if num_added_orders == 0:
                self.logger.info("Creating empty truck drive...")
                await self._create_empty_truck_drive()
                await mpc.barrier()

            # Reset order status for next round
            for order in self.orders:
                order.process_this_round = 0

            self.num_processed_orders += num_orders_processed_this_round

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

        end_time_solver = time.perf_counter()
        self.logger.debug(
            "Total elapsed time for solving: %s", end_time_solver - start_time_solver
        )
