## ❤️ Heartbeat Monitoring System
A simple service heartbeat monitoring system that:
1. Reads heartbeat events from a JSON file
2. Sorts and processes events per service
3. Detects consecutive missed heartbeats
4. Triggers an alert after a configurable number of misses
5. Handles malformed events gracefully
6. Includes complete unit tests (pytest)

## Requirements

Python 3.10+

pip

Virtual environment (recommended)

## Setup Instructions

1. Create and activate virtual environment
   
   `python -m venv venv`
   
   Windows
   
   `venv\Scripts\activate`
   
2. Install dependencies
   
   `pip install -r requirements.txt`
   
3. Run the main program
   
   `python main.py`

## Expected Output Example:
`[
  { "service": "email", "alert_at": "2025-08-04T10:05:00Z" }
]`

## Running Tests

We use pytest for unit testing.

Install pytest

`pip install pytest`

## Run the tests

`pytest -q`

## Configuration Parameters

These two parameters define alert logic:

`expected_interval_seconds = 60
allowed_misses = 3`

## Error Handling

The system gracefully handles:

Missing timestamp

Missing service

Invalid timestamp formats

Null values

Unrecognized fields
