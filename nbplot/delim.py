# This file is part of nbplot. See LICENSE for details.

import io
import logging
from logging import debug


def guess_delimiter(input: io.IOBase):
    """
    Guess the delimiter of csv-file files.

    The algorithm tries various delimiters, and for each it finds out
    the number of numerical columns found on a subset of the rows of
    the file. To be accepted, a delimiter has to have the same number
    of columns for all the rows. Then the accepted delimiter with more
    columns is returned. If in doubt, return space.
    """

    # Read the first 32 lines
    first_lines = []
    for line in input:
        first_lines.append(line)
        if len(first_lines) >= 32:
            break

    # Try to skip the first 8 lines, but only if there are enough to still
    # read 8 lines after.
    first_line_index = min(len(first_lines) // 2, 8)

    delimiters = [' ', ',', ';', ':']
    num_cols_per_delimiter = {}
    for delim in delimiters:
        num_cols_per_delimiter[delim] = {}

    def can_convert_to_float(s):
        try:
            float(s)
            return True
        except ValueError:
            return False

    for line in first_lines[first_line_index:first_line_index + 16]:
        for delim in delimiters:
            # Special case for space as the default split will ignore multiple spaces.
            cols = line.split(delim) if delim != ' ' else line.split()
            cols = list(filter(can_convert_to_float, cols))
            ncols = len(cols)
            if ncols not in num_cols_per_delimiter[delim]:
                num_cols_per_delimiter[delim][ncols] = 0
            num_cols_per_delimiter[delim][ncols] += 1

    debug(f'num_cols_per_delimiter: {num_cols_per_delimiter}')

    delims_with_consistent_ncols = []
    for delim in delimiters:
        if len(num_cols_per_delimiter[delim]) == 1:
            delims_with_consistent_ncols.append(delim)

    if len(delims_with_consistent_ncols) == 0:
        debug('No delimiter with a consistent number of columns')
        return ' '

    highest_count_for_delimiter = {}
    for delim in delims_with_consistent_ncols:
        assert len(num_cols_per_delimiter[delim]) == 1  # we filtered right before.
        ncols = next(iter(num_cols_per_delimiter[delim]))  # first key
        highest_count_for_delimiter[delim] = ncols

    best_delim = sorted(highest_count_for_delimiter, key=highest_count_for_delimiter.get, reverse=True)[0]

    # In case of equality (e.g. one column), give an edge to ' ' as it's safer.
    if highest_count_for_delimiter.get(' ', 0) == highest_count_for_delimiter[best_delim]:
        best_delim = ' '

    return best_delim

# Unit tests.
if __name__ == '__main__':
    import unittest
    from pathlib import Path

    here_path = Path(__file__).parent
    test_files = here_path / '..' / 'tests'

    class TestDelimMethods(unittest.TestCase):

        def test_comma_csv(self):
            with open(test_files / 'test_comma.csv', 'r') as f:
                self.assertEqual(guess_delimiter(f), ',')

        def test_space_csv(self):
            with open(test_files / 'test_space.csv', 'r') as f:
                self.assertEqual(guess_delimiter(f), ' ')

        def test_semicolon_csv(self):
            with open(test_files / 'test_semicolon.csv', 'r') as f:
                self.assertEqual(guess_delimiter(f), ';')

        def test_space_3cols_csv(self):
            with open(test_files / 'test_space_3cols.csv', 'r') as f:
                self.assertEqual(guess_delimiter(f), ' ')

    logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')
    unittest.main()
