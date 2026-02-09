# CARLA Scenarios

This directory contains Python-based CARLA scenarios.

## Requirements

- CARLA server running on localhost:2000
- Python 3.12+ with carla package installed

## Running a Scenario

```bash
# Run the example scenario
uv run python scenarios/example_scenario.py
```

## Creating a New Scenario

1. Create a new Python file in this directory
2. Import carla module
3. Connect to CARLA server: `client = carla.Client('localhost', 2000)`
4. Implement your scenario logic
5. Run with: `uv run python scenarios/your_scenario.py`

## Scenario Template

```python
#!/usr/bin/env python3
import carla
import time
import sys

def main():
    """Your scenario description"""
    try:
        # Connect to CARLA
        client = carla.Client('localhost', 2000)
        client.set_timeout(10.0)
        world = client.get_world()

        # Your scenario logic here

        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    sys.exit(main())
```
