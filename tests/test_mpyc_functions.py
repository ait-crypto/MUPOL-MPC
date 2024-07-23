from typing import List

import pytest
from mpyc.runtime import mpc
from mpyc.sectypes import SecureInteger

from mupol.mpc.utils.mpyc_vector_functions import (
    compute_indicator_vector,
    find_first_non_zero,
    real_or,
)

secint: SecureInteger = mpc.SecInt(10)

LENGTH: int = 5
INDEX: SecureInteger = mpc.input(secint(2), senders=0)
INDICATOR_VECTOR: List[int] = [0, 0, 1, 0, 0]

VECTOR: List[SecureInteger] = [
    mpc.input(secint(1), senders=0),
    mpc.input(secint(0), senders=0),
    mpc.input(secint(1), senders=0),
]

FIRST_NON_ZERO_ARRAY: List[int] = [1, 0, 0]


@pytest.mark.asyncio
async def test_real_or() -> None:
    zero = mpc.input(secint(0), senders=0)
    one = mpc.input(secint(1), senders=0)

    assert all(
        [
            await mpc.output(await real_or(zero, zero)) == 0,
            await mpc.output(await real_or(zero, one)) == 1,
            await mpc.output(await real_or(one, zero)) == 1,
            await mpc.output(await real_or(one, one)) == 1,
        ]
    )


@pytest.mark.asyncio
async def test_compute_indicator_vector() -> None:
    indicator_vector = await compute_indicator_vector(length=LENGTH, index=INDEX)
    indicator_vector = await mpc.output(indicator_vector)

    assert indicator_vector == INDICATOR_VECTOR


@pytest.mark.asyncio
async def test_find_first_non_zero() -> None:
    first_non_zero_array = await find_first_non_zero(VECTOR)
    first_non_zero_array = await mpc.output(first_non_zero_array)

    assert first_non_zero_array == FIRST_NON_ZERO_ARRAY
