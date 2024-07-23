from typing import List

import pytest

import profiler


@pytest.mark.asyncio
async def test_profiler(
    possible_orders_scalability: List[int], possible_trucks_scalability: List[int]
) -> None:
    await profiler.run_profiler(
        possible_orders_scalability, possible_trucks_scalability
    )
