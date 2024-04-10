import numpy as np

def calc_moving_average(last_spot_value, last_ema_value, averaging_window, interval):
    alpha = exp(-(interval * 10**18 // averaging_window))
    return (last_spot_value * (10**18 - alpha) + last_ema_value * alpha) // 10**18


def exp(x):
    """
    @dev Calculates the natural exponential function of a signed integer with
         a precision of 1e18.
    @notice Note that this function consumes about 810 gas units. The implementation
            is inspired by Remco Bloemen's implementation under the MIT license here:
            https://xn--2-umb.com/22/exp-ln.
    @dev This implementation is derived from Snekmate, which is authored
         by pcaversaccio (Snekmate), distributed under the AGPL-3.0 license.
         https://github.com/pcaversaccio/snekmate
    @param x The 32-byte variable.
    @return int256 The 32-byte calculation result.
    """
    value = x

    # If the result is `< 0.5`, we return zero. This happens when we have the following:
    # "x <= floor(log(0.5e18) * 1e18) ~ -42e18".
    if (x <= -41446531673892822313):
        return 0

    # When the result is "> (2 ** 255 - 1) / 1e18" we cannot represent it as a signed integer.
    # This happens when "x >= floor(log((2 ** 255 - 1) / 1e18) * 1e18) ~ 135".
    assert x < 135305999368893231589, "wad_exp overflow"

    # `x` is now in the range "(-42, 136) * 1e18". Convert to "(-42, 136) * 2 ** 96" for higher
    # intermediate precision and a binary base. This base conversion is a multiplication with
    # "1e18 / 2 ** 96 = 5 ** 18 / 2 ** 78".
    value = (x << 78) // 5 ** 18

    # Reduce the range of `x` to "(-½ ln 2, ½ ln 2) * 2 ** 96" by factoring out powers of two
    # so that "exp(x) = exp(x') * 2 ** k", where `k` is a signer integer. Solving this gives
    # "k = round(x / log(2))" and "x' = x - k * log(2)". Thus, `k` is in the range "[-61, 195]".
    k = ((value << 96) // 54916777467707473351141471128 + 2 ** 95) >> 96
    value = value - k * 54916777467707473351141471128

    # Evaluate using a "(6, 7)"-term rational approximation. Since `p` is monic,
    # we will multiply by a scaling factor later.
    y = (((value + 1346386616545796478920950773328) * value) >> 96) + 57155421227552351082224309758442
    p = (((((((y + value) - 94201549194550492254356042504812) * y) >> 96) + 28719021644029726153956944680412240) * value) + (4385272521454847904659076985693276 << 96))

    # We leave `p` in the "2 ** 192" base so that we do not have to scale it up
    # again for the division.
    q = (((value - 2855989394907223263936484059900) * value) >> 96) + 50020603652535783019961831881945
    q = ((q * value) >> 96) - 533845033583426703283633433725380
    q = ((q * value) >> 96) + 3604857256930695427073651918091429
    q = ((q * value) >> 96) - 14423608567350463180887372962807573
    q = ((q * value) >> 96) + 26449188498355588339934803723976023

    # The polynomial `q` has no zeros in the range because all its roots are complex.
    # No scaling is required, as `p` is already "2 ** 96" too large. Also,
    # `r` is in the range "(0.09, 0.25) * 2**96" after the division.
    r = p//q

    # To finalise the calculation, we have to multiply `r` by:
    #   - the scale factor "s = ~6.031367120",
    #   - the factor "2 ** k" from the range reduction, and
    #   - the factor "1e18 / 2 ** 96" for the base conversion.
    # We do this all at once, with an intermediate result in "2**213" base,
    # so that the final right shift always gives a positive value.

    # Note that to circumvent Vyper's safecast feature for the potentially
    # negative parameter value `r`, we first convert `r` to `bytes32` and
    # subsequently to `uint256`. Remember that the EVM default behaviour is
    # to use two's complement representation to handle signed integers.
    return (r * 3822833074963236453042738258902158003155416615667) >> (195-k)