import sys
from unittest.mock import patch

import pytest

import example


@pytest.mark.asyncio
async def test_example() -> None:
    testargs = [""]
    with patch.object(sys, "argv", testargs):
        await example.main()
