import logging

logger = logging.getLogger(__name__)

import threading
from process_json import process_json


def process_client(conn, addr, q):
    # A client will send two things.
    # Thing 1 is 2 bytes. They specify the length of thing 2.
    # Thing 2 is a json string.
    logger.debug(f"Begin process_client {conn} : {addr}")

    with conn:
        try:
            json_length = conn.recv(2)
            logger.debug(f"json_length : {json_length}")

            json_length = int.from_bytes(json_length, "little", signed=False)
            logger.debug(f"json_length : {json_length}")

            json_message = conn.recv(int(json_length)).decode("utf-8")
            entry = process_json(json_message)
            if entry:
                q.put(entry, block=False, timeout=None)
            else:
                return
        except Exception as e:
            logger.warning(f"Could not process client into calender. Entry lost: {e}")

    logger.info(
        f"Closed a connection. Remaining connections / threads: {threading.activeCount() - 1}"
    )
