""" 
Act as server to recieve and process JSON strings to be interpreted as google calendar entries.
Add new entries to google calendar.
Note - This program is not secure. Intranet use only. Do not expose port to untrusted devices. Data transmitted in clear text.
Expects little endian byte order.
Clients should send a 2 byte message of the length of the json string prior to the json.
IPV4 only.
Dennis Marwood. dennismarwood@gmail.com
29-01-2022
TODO: test cases
TODO: update requirements.txt
"""

import logging
logging.getLogger("googleapicliet.discovery_cache").setLevel(logging.INFO)
logging.basicConfig(level=logging.DEBUG, format='%(levelname)-8s %(asctime)s Line: %(lineno)-4s %(filename)s - %(funcName)s - \
%(threadName)s - %(thread)d\n\t\t%(message)s\n', filename='calendar_writer.log', force=True)
logger = logging.getLogger(__name__)

import queue
import threading
import json
from sys import exit
from open_socket import open_socket
from queue import Queue
# from throttle import get_throttle
from process_client import process_client


try:
    with open('config.json', 'r') as conf:
        c = json.load(conf)
        PORT = c['PORT']
        LOG_LEVEL = c['LOG_LEVEL']
except (FileNotFoundError, KeyError) as e:
    logger.critical(f"Could not find the config file or expected value in file. Cannot proceed. Exiting \n{e} is not present in the file.")
    exit()
else:
    logger.setLevel(level=getattr(logging, LOG_LEVEL.upper(), 10))

from add_entry_to_calendar import add_entry_to_calendar

def main():
    q = Queue(maxsize=0)
    with open_socket(PORT) as socket:
        while True:
            # Main thread blocked here, waiting for a connection.
            (
                conn,
                addr,
            ) = socket.accept()
            logger.debug(f"A client has connected to this server. {conn} {addr}")
            process_client_thread = threading.Thread(target=process_client, args=(conn, addr, q))
            logger.debug(f"A new thread has been created to process client {addr}")
            process_client_thread.start()
            logger.debug(f"Active connections: {threading.activeCount() - 1}")
            
            try:
                assert q.empty() == False
                json = q.get(block=True)
                q.task_done()
            except (queue.Empty, AssertionError): #  The queue.Empty exception is only triggered if q.get is NOT blocking
                pass
            else:
                write_calendar_thread = threading.Thread(target=add_entry_to_calendar, args=(json,))
                write_calendar_thread.start()


if __name__ == "__main__":
    main()
