"""This module contains some useful MPyC functions to process secure integers and
vectors.
"""

from typing import List

from mpyc.runtime import mpc
from mpyc.sectypes import SecureInteger


async def real_or(a: SecureInteger, b: SecureInteger) -> SecureInteger:
    """
    The MPyC built-in OR function does not reduce modulo 2, it just computes
    a+b+(a AND b). Hence for MPyC, 1 OR 1 = 3. No bueno.
    I couldn't find anything better in MPyC itself, so coding it here with NAND
    gates.

    :param a: The first bit to be compared
    :type a: SecureInteger
    :param b: The second bit to be compared
    :type b: SecureInteger
    :returns: 0 if both a and b are equal to 0, 1 otherwise
    :rtype: SecureInteger
    """
    return 1 - ((1 - a) * (1 - b))


async def compute_indicator_vector(
    length: int, index: SecureInteger
) -> List[SecureInteger]:
    """
    Given a plaintext length and a secret-shared index, return the
    secret-shared vector (v_1, ..., v_length) where v_i = 1 if i = index, 0
    otherwise

    :param length: Desired length of the output vector
    :type length: int
    :param index: Location of the output vector to be set to 1
    :type index: SecureInteger
    :returns: secret-shared vector with index-position equal to 1, all other positions
    equal to 0
    :rtype: List[SecureInteger]
    """
    sec_type = type(index)
    indicator_vector = [mpc.input(sec_type(0), senders=0) for _ in range(length)]
    valid = mpc.input(sec_type(1), senders=0)
    for j in range(length):
        indicator_vector[j] = mpc.if_else(mpc.eq(j, index), valid, indicator_vector[j])
    return indicator_vector


async def find_first_non_zero(secret_list: List[SecureInteger]) -> List[SecureInteger]:
    """
    Given a binary vector secret_list, output a binary vector with 1 at the first
    non-zero position of secret_list, and 0 elsewhere

    :param secret_list: vector of secret-shared integers
    :returns: vector of the same length as the input, with 1 at the first non-zero
    position of the input vector, and 0 elsewhere
    """
    sec_type = type(secret_list[0])
    first_non_zero_list = [
        mpc.input(sec_type(0), senders=0) for _ in range(len(secret_list))
    ]
    already_set = mpc.input(sec_type(0), senders=0)
    for j in range(len(secret_list)):
        first_non_zero_list[j] = secret_list[j] * (1 - already_set)
        already_set = await real_or(already_set, secret_list[j])
    return first_non_zero_list
