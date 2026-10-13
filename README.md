
# Baseball Pitch Analysis Tool

A Python project that uses MLB Statcast data to analyze pitcher tendencies, pitch performance, and pitch sequencing.

## Features

- Pitch selection by count
- Pitch usage against left-handed and right-handed batters
- Average pitch velocity
- Whiff rate and CSW%
- Expected and actual offensive outcomes
- Batting average and slugging percentage against each pitch
- Hard-hit and estimated barrel rates
- Pitch sequencing and follow-up pitch tendencies

## Built With

- Python
- Pandas
- pybaseball
- MLB Statcast data

## Setup

Install the required packages:

```bash
python -m pip install pandas pybaseball
```

## How to Run

1. Install Python.
2. Install the required packages.
3. Open `main.py`.
4. Set the pitcher name and date range in the settings section.
5. Run the script.

## Notes

Results depend on the selected date range and available Statcast data. Small samples can produce misleading performance statistics.

This project is a work in progress and my first ever coding project.
