import logging

logger = logging.getLogger(__name__)

import json
from datetime import datetime, timedelta


def process_json(m):
    """
    Expects Json with one of the following formats
    {"date":"2022-02-24","day_type":"ADay"}
    {"date":"2022-02-25","day_type":{"Work":"2022-02-25T14:00:00"}}
    {"date":"2022-02-26","day_type":"Off"}
    {"date":"2022-02-15","day_type":"Vacation"}

    Returns either a dict of values correctly formated for insertion into calendar or None.
    """

    if m is None:
        logger.error(
            f"The JSON string from the client is empty.\nCould not process this record into the calendar."
        )
        return

    try:
        m_dict = json.loads(m)  # json string to dict
    except json.JSONDecodeError as e:
        logger.error(
            f"The JSON string '{m}' from the client is invalid.\nCould not process this record into the calendar.\n {e}"
        )
        return

    try:
        summary = m_dict["day_type"]
        start_date = datetime.fromisoformat(m_dict["date"])
    except KeyError as e:
        logger.warning(
            f"The client provided json data is missing a key: {e}\nCould not process: {m}"
        )
        return
    except ValueError as e:
        logger.warning(
            f"The client provided value for the event date is not valid: {e}\nCould not process: {m}"
        )
        return

    end_date = start_date + timedelta(
        days=1
    )  # For all day events to appear in the android calendar the end date must be incremented.

    if type(summary) is str and summary not in (
        ("ADay")
    ):  # Don't add entries for Off or Vacation
        logger.info(f"Day type is '{summary}' and won't be processed.")
        return

    if summary == "ADay":
        summary = "'A' day"
    else:
        try:
            assert (
                type(summary) is dict
            ) == True, f"Expected type {type(dict)} but received {type(summary)}. Failed to add entry."
        except AssertionError as e:
            logger.warning(f"{e}")
            return
        summary = m_dict["day_type"]["Work"]  # Date and Time of shift
        summary = datetime.fromisoformat(summary).strftime(
            "%H:%M"
        )  # Reduce date to just time of shift

    json_message_for_api = {
        "summary": summary,
        "description": summary,
        "start": {"date": str(start_date.date())},
        "end": {"date": str(end_date.date())},
    }

    return json_message_for_api
