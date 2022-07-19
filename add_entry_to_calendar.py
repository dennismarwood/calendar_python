import logging

logger = logging.getLogger(__name__)

import json
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
# https://github.com/googleapis/google-api-python-client
# https://google-auth.readthedocs.io/en/master/reference/google.oauth2.service_account.html
from google.oauth2 import service_account 
from sys import exit
from random import randint
from time import sleep

SCOPES = ["https://www.googleapis.com/auth/calendar"]
SERVICE_ACCOUNT_FILE = "service-account.json"
MAXIMUM_BACKOFF_TIME = 33 #https://cloud.google.com/storage/docs/retry-strategy

try:
    with open(SERVICE_ACCOUNT_FILE, "r") as saf, open(
        "target_calendar.json", "r"
    ) as tc:
        service_file = json.load(saf)
        target_calendar = json.load(tc)
        SUBJECT = service_file["client_email"]
        TARGET_CALENDAR_ID = target_calendar["target_calendar_id"]
        target_calendar_desc = target_calendar["description"]
except (FileNotFoundError, KeyError) as e:
    logger.critical(
        f"Could not find the service account file or expected value in file. Cannot proceed. Exiting \n{e}"
    )
    exit()
finally:
    logger.info(f"Target calendar described as: {target_calendar_desc}")


credentials = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES
)
delegated_credentials = credentials.with_subject(SUBJECT)

# cannot mock embeded functions
def backoff(entry, response_string, delay=1):
        if MAXIMUM_BACKOFF_TIME > delay:
            delay += randint(1, 1000) / 1000.0
            logger.error(f"Executing exponential backoff delay for:\n{entry}\nWill try again in {delay} seconds")
            sleep(delay)
            add_entry_to_calendar(entry, TARGET_CALENDAR_ID, int(delay))
        else:
            logger.error(f"Failed to add entry to calendar after exponential back off attempts.\n{entry}\n{response_string}")

def add_entry_to_calendar(entry, calendarID=TARGET_CALENDAR_ID, delay=.5):

    try:
        assert (
            type(entry) is dict
        ) == True, f"Expected 'entry' parameter to be of type dict. Received '{entry}'. Failed to add entry."
    except AssertionError as e:
        logger.error(f"{e}")
        return entry

    try:
        service = build("calendar", "v3", credentials=delegated_credentials)
        event = service.events().insert(calendarId=calendarID, body=entry).execute()

    #https://developers.google.com/calendar/api/guides/errors
    #Note- this is the Google HttpError, not HTTPError
    except HttpError as google_e:
        response = json.loads(google_e.content)
        
        response_header_code = response.get("error").get("code")
        response_header_message = response.get("error").get("message")
        response_string = f"{response_header_code} {response_header_message} {response.get('error').get('errors')[0]}"

        response_reason = response.get("error").get("errors")[0]["reason"]
        response_message = response.get("error").get("errors")[0]["message"]


        if response_header_code == 400:
            logger.warning(f"Failed to add entry to calendar. Missing or invalid field parameter in the request. {response_string}")
        elif response_header_code == 401:
            logger.error(f"The access token you are using is expired or invalid. {response_string}")
        elif response_header_code == 403 and response_reason == "userRateLimitExceeded":
            logger.warning(f"Per-user limit reached. {response_message}")
            backoff(entry, response_string, int(delay + delay))
        elif response_header_code == 403 and response_reason == "rateLimitExceeded":
            logger.warning(f"The user has reached Google Calendar API's maximum request rate per calendar or per authenticated user. {response_message}")
            backoff(entry, response_string, int(delay + delay))
        elif response_header_code == 403 and response_reason == "quotaExceeded":
            logger.warning(f"The user reached one of the Google Calendar limits in place to protect Google users and infrastructure from abusive behavior. {response_message}")
            backoff(entry, response_string, int(delay + delay))
        elif response_header_code == 403 and response_reason == "forbiddenForNonOrganizer":
            logger.error(f"This user lacks permission to change a shared calendar field. {response_message}")
        elif response_header_code == 404:
            logger.warning(f"Could not find a calendar entry / resource or requests are too rapid. {response_message}")
            backoff(entry, response_string, int(delay + delay))
        elif response_header_code == 409:
            logger.warning(f"An instance with the ginven ID already exists {response_message}")
        elif response_header_code == 410 and response_reason == "fullSyncRequired":
            logger.error(f"A resync is required  {response_message}")
        elif response_header_code == 410 and response_reason == "updatedMinTooLongAgo":
            logger.error(f"A resync is required {response_message}")
        elif response_header_code == 410 and response_reason == "deleted":
            logger.warning(f"Resource was already deleted {response_message}")
        elif response_header_code == 412:
            logger.warning(f"Precondition Failed. {response_message}")
            backoff(entry, response_string, int(delay + delay))
        elif response_header_code == 429:
            logger.warning(f"Too many requests. {response_message}")
            backoff(entry, response_string, int(delay + delay))
        elif response_header_code == 500:
            logger.warning(f"Backend Error. {response_message}")
            backoff(entry, response_string, int(delay + delay))
        else:
            logger.error(f"An unhandled HttpError has occured - {response_header_code} {response_header_message}")

        return response_header_code

    except Exception as e:
        logger.warning(f"Could not add entry to calender:\n{entry}\n{e}")
        return e
    
    else:
        logger.info(f"Insertion status: '{event.get('status')}' at '{event.get('created')}'\n'{event.get('htmlLink')}'\n{event}")
        return 200