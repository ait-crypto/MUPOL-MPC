from typing import List

import pytest

import profiler


@pytest.mark.asyncio
async def test_profiler(
    possible_orders_scalability: List[int],
    possible_trucks_scalability: List[int],
    possible_freighters_scalability: List[int],
    possible_max_order_volumes_scalability: List[int],
    num_experiments_scalability: int,
) -> None:
    await profiler.run_profiler(
        possible_orders_scalability,
        possible_trucks_scalability,
        possible_freighters_scalability,
        possible_max_order_volumes_scalability,
        num_experiments_scalability,
    )
