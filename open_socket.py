import logging

logger = logging.getLogger(__name__)

import socket
import sys


def open_socket(port=5050):
    try:
        IP = socket.gethostbyname(socket.gethostname())  # This machine's ip
        ADDR = (IP, port)
    except:
        logger.critical(f"Could not determine this machines IP address. Exiting.")
        sys.exit()

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # IPV 4, TCP
        sock.bind(ADDR)
        sock.listen(100)
        logger.info(f"sock created a listening socket: {sock}")
    except socket.error as e:
        logger.critical(
            f"There was a problem configuring the socket, cannot proceed. Exiting. {ADDR} - {e}"
        )
        sys.exit()
    else:
        return sock
