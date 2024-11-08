# This code is part of Tergite
#
# (C) Copyright Chalmers Next Labs 2024
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

import re
from typing import List


def parse_input_qubit(qubit_str: str) -> List[str]:
    # Split by commas or spaces while allowing for ranges
    tokens = re.split(r",\s*|\s+", qubit_str.strip())

    result = []

    for token in tokens:
        if "-" in token:
            # Handle ranges
            start, end = token.split("-")
            prefix = re.match(r"[a-zA-Z]+", start).group()
            start_num = int(re.search(r"\d+", start).group())
            end_num = int(re.search(r"\d+", end).group())

            # Adjust if start is greater than end
            if start_num > end_num:
                start_num, end_num = end_num, start_num

            result.extend([f"{prefix}{i:02}" for i in range(start_num, end_num + 1)])
        elif len(token) > 0:
            # Handle individual items
            result.append(token.strip())

    # Ensure unique values and return in sorted order
    return sorted(set(result), key=lambda x: (x[:2], int(x[2:])))
