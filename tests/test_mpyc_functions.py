import pytest
from mpyc.runtime import mpc
from mpyc.sectypes import SecureInteger

from mupol.mpc.utils.mpyc_vector_functions import real_or

secint: SecureInteger = mpc.SecInt(10)


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
