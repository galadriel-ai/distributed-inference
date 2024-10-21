"""
Simple analytics script to grep through the logs file.
Prints out min, max and avg time for each logged function duration.
Usage:
```shell
PYTHONPATH=. python scripts/analyse_timer_logs.py
```
"""

import json
from typing import List
from datetime import datetime, timedelta

import settings


def main(last_minutes: int = 30):
    now = datetime.now()
    time_filter = now - timedelta(minutes=last_minutes)

    all_timer_results = _read_logs(time_filter)
    for name, durations in all_timer_results.items():
        _print_result(name, durations)


def _read_logs(time_filter):
    """
    Reads log file line by line:
    * filters out only timer logs
    * greps out the name and time
    * adds to dict for analytics
    """
    result = {}

    with open(settings.LOG_FILE_PATH, "r") as file:
        line = file.readline()
        while line:
            message, timestamp = _get_message_and_timestamp(line)
            if timestamp and timestamp > time_filter:
                if message and _is_timer_log(message):
                    name, duration = _get_name_and_duration(message)
                    if name in result:
                        result[name].append(duration)
                    else:
                        result[name] = [duration]
            line = file.readline()
    return result


def _get_message_and_timestamp(line: str) -> (str, datetime):
    try:
        line = line.strip()
        line = json.loads(line)
        date_obj = datetime.strptime(line["asctime"], "%Y-%m-%d %H:%M:%S,%f")
        return line["message"], date_obj
    except:
        return None, None


def _is_timer_log(message: str) -> bool:
    if message.startswith("Timer: "):
        return True
    return False


def _get_name_and_duration(message: str) -> (str, float):
    message = message.replace("Timer: ", "")
    name, duration = message.split(" took ")
    duration = duration.replace(" s", "")
    duration = float(duration.strip())
    return name, duration


def _print_result(name: str, durations: List[float]) -> None:
    print(name)
    print("  min:", min(durations))
    print("  max:", max(durations))
    print("  avg:", sum(durations) / len(durations))


if __name__ == "__main__":
    main(last_minutes=1440)
