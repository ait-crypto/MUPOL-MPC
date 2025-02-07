"""This module contains a utility function for MPyC.
"""

from mpyc.sectypes import SecureInteger


async def real_or(a: SecureInteger, b: SecureInteger) -> SecureInteger:
    """
    The MPyC built-in OR function does not reduce modulo 2, it just computes
    a+b+(a AND b). Hence for MPyC, 1 OR 1 = 3. No bueno.
    There are probably better and more elegant ways to address this problem,
    but for now a quick fix: just place here a custom function with NAND gates.

    :param a: The first bit to be compared
    :type a: SecureInteger
    :param b: The second bit to be compared
    :type b: SecureInteger
    :returns: 0 if both a and b are equal to 0, 1 otherwise
    :rtype: SecureInteger
    """
    return 1 - ((1 - a) * (1 - b))
