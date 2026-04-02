#!/usr/bin/env python3
"""
Generate a text file with all dates between two specified dates in descending order.
Each date is formatted as YYYY-MM-DD and written on a separate line.
"""

from datetime import datetime, timedelta


def generate_date_file(start_date, end_date, filename="datestofetch.txt"):
    """
    Generate a text file with dates from start_date to end_date in descending order.
    
    Args:
        start_date (str): Start date in YYYY-MM-DD format (most recent)
        end_date (str): End date in YYYY-MM-DD format (earliest)
        filename (str): Output filename
    """
    # Parse the date strings
    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")
    
    # Ensure start is after end for descending order
    if start < end:
        start, end = end, start
    
    # Generate all dates and write to file
    with open(filename, 'w') as f:
        current_date = start
        while current_date >= end:
            f.write(current_date.strftime("%Y-%m-%d") + "\n")
            current_date -= timedelta(days=1)
    
    # Calculate and display statistics
    total_days = (start - end).days + 1
    print(f"Generated {filename} with {total_days} dates")
    print(f"Date range: {start.strftime('%Y-%m-%d')} to {end.strftime('%Y-%m-%d')} (descending)")


if __name__ == "__main__":
    # Generate the requested date file
    generate_date_file("2024-06-19", "2013-03-27", "datestofetch.txt")
