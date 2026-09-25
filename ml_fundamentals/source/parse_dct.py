import re
from typing import Dict


def parse_column_details(iabr23fl_dct_path: str)-> Dict:
    # Initialize an empty dictionary to store column names and lengths
    column_lengths = {}

    # Regular expression to match lines with column definitions
    pattern = r'\s*(\w+)\s+(\w+)\s+\d:\s+(\d+)-(\d+)'

    # Read and parse the .dct file
    with open(iabr23fl_dct_path, "r") as file:
        for line in file:
            line = re.sub(r'\s+', ' ', line.strip()).split(' ')
            if len(line) != 3 and len(line) != 4:
                continue
            if len(line) == 4:
                len_val = line[3]
            elif len(line) == 3:
                len_val = line[2].split(':')[1]

            # Extract column name, start, and end positions
            start, end = len_val.split('-')[0], len_val.split('-')[1]
            data_type, col_name = line[0], line[1], #match.groups()
            start, end = int(start), int(end)
    
            # Calculate column length
            length = (end - start) + 1
            # Store the column name and length in the dictionary
            column_lengths[col_name] = length
    return column_lengths

"""
if __name__ == "__main__":
    iabr23fl_dct_path = "data/food_health/NFHS_1/ALL INDIA FLAT/IABR23FL/IABR23FL.DCT"
    column_lengths = parse_column_details(iabr23fl_dct_path)
    print(len(column_lengths))
"""