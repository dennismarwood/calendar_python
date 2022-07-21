from ast import Add
import logging
from unittest import mock
from urllib.error import HTTPError

from add_entry_to_calendar import add_entry_to_calendar
logger = logging.getLogger(__name__)

import unittest
from unittest.mock import patch
from googleapiclient.discovery import build
from googleapiclient.http import HttpMock, HttpMockSequence
from googleapiclient.errors import HttpError

#TODO All the errors that could be resoleved with exponential back should be tested with a 200 response.
# However I am not sure how to get that working with the backoff mock being defined in SetUp() to keep code dry.

@patch("add_entry_to_calendar.build")
class TestAddEntry(unittest.TestCase):

    """  def test_invoke_json_bad_request(self):
        print("WARNING - HITTING GOOGLE API FOR TESTING")
        #{'summary': '13:00', 'description': '13:00', 'start': {'date': '2022-06-20'}, 'end': {'date': '2022-06-21'}}
        bad_entry = {
            "summary": "Invoke 400 bad request",
            "description": "Description",
            "start": {"date": "2022-06-20"},
            "end": {"date": "2022-06-19"}, #invalid end date
        }
        add_entry_to_calendar(bad_entry) """

    #
    #def test_json_401(self, mock_build):

        #pass
       
    def test_add_entry_to_calendar_200(self, _):
        self.assertEqual(add_entry_to_calendar({"Mock": "200"}), 200)

    # https://developers.google.com/calendar/api/guides/errors
    # Mock the build library of add_entry_to_calendar.py
    
    def test_add_entry_to_calendar_400(self, mock_build): #mock_build is a MagicMock
        # The mock will be substituted whenever add_entry_to_calendar calls the "build" library
        self.e = None

        #google's mock https://googleapis.github.io/google-api-python-client/docs/mocks.html
        # Build mock response from google with a 400 error code
        http = HttpMock('tests/google_errors/calendar_400.json', {'status' : '400'})
        service = build("calendar", "v3", http=http)

        try:
            service.events().insert(calendarId='primary').execute(http=http)
        except HttpError as e:
            self.e = e

        # Now we will have the mock throw this error when a calender event is added.
        #https://het.as.utexas.edu/HET/Software/mock/examples.html
        mock_build.return_value.events.return_value.insert.return_value.execute.side_effect = self.e
        self.assertEqual(add_entry_to_calendar({"Mock":"400"}), 400)
        #<HttpError 400 when requesting https://www.googleapis.com/calendar/v3/calendars/primary/events?alt=json returned "Ok">

    def test_add_entry_to_calendar_401(self, mock_build):
        self.e = None
        http = HttpMock('tests/google_errors/calendar_401.json', {'status': '401'})
        service = build("calendar", "v3", http=http)

        try:
            service.events().insert(calendarId='primary').execute(http=http)
        except HttpError as e:
            self.e = e

        mock_build.return_value.events.return_value.insert.return_value.execute.side_effect = self.e
        self.assertEqual(add_entry_to_calendar({"Mock":"401"}), 401)
    
    @patch("add_entry_to_calendar.sleep", return_value=None)
    def test_add_entry_to_calendar_403_userRateLimitExceeded(self, _, mock_build):
        self.e = None
        http = HttpMock('tests/google_errors/calendar_403_userRateLimitExceeded.json', {'status' : '403'})
        service = build("calendar", "v3", http=http)

        try:
            service.events().insert(calendarId='primary').execute(http=http)
        except HttpError as e:
            self.e = e

        mock_build.return_value.events.return_value.insert.return_value.execute.side_effect = [self.e, self.e, self.e, self.e, self.e]
        self.assertEqual(add_entry_to_calendar({"Mock":"403_userRateLimitExceeded"}), 403)

    @patch("add_entry_to_calendar.sleep", return_value=None)
    def test_add_entry_to_calendar_403_rateLimitExceeded(self, _, mock_build):
        self.e = None
        http = HttpMock('tests/google_errors/calendar_403_rateLimitExceeded.json', {'status' : '403'})
        service = build("calendar", "v3", http=http)

        try:
            service.events().insert(calendarId='primary').execute(http=http)
        except HttpError as e:
            self.e = e

        mock_build.return_value.events.return_value.insert.return_value.execute.side_effect = self.e
        self.assertEqual(add_entry_to_calendar({"Mock":"403_rateLimitExceeded"}), 403)
    
    @patch("add_entry_to_calendar.backoff")
    def test_add_entry_to_calendar_200_after_rateLimitExceeded(self, mock_backoff, mock_build):
        #We will save the deepest stack return value
        self.ok = None

        def side_effect(_, __, delay):
            data = f"backoff called with delay of {delay}. This is call count: {mock_backoff.call_count}"
            if delay < 10:
                #print(data)
                add_entry_to_calendar({"Mock":data}, _,  delay)
            else:
                mock_build.return_value.events.return_value.insert.return_value.execute.side_effect = None
                self.ok = add_entry_to_calendar({"Mock":"200"})
            
        self.e = None
        http = HttpMock('tests/google_errors/calendar_403_rateLimitExceeded.json', {'status' : '403'})
        service = build("calendar", "v3", http=http)
        try:
            service.events().insert(calendarId='primary').execute(http=http)
        except HttpError as e:
            self.e = e
        
        mock_backoff.side_effect = side_effect
        mock_build.return_value.events.return_value.insert.return_value.execute.side_effect = self.e
        add_entry_to_calendar({"Mock":"403_rateLimitExceeded"})
        with self.subTest():
            self.assertEqual(mock_backoff.call_count, 5)
            # After numerous reattempts we should get a 200
            self.assertEqual(self.ok, 200)
    
    @patch("add_entry_to_calendar.sleep", return_value=None)
    def test_add_entry_to_calendar_403_quotaExceeded(self, _, mock_build):
        self.e = None
        http = HttpMock('tests/google_errors/calendar_403_quotaExceeded.json', {'status' : '403'})
        service = build("calendar", "v3", http=http)

        try:
            service.events().insert(calendarId='primary').execute(http=http)
        except HttpError as e:
            self.e = e

        mock_build.return_value.events.return_value.insert.return_value.execute.side_effect = self.e
        self.assertEqual(add_entry_to_calendar({"Mock":"403_quotaExceeded"}), 403)

    def test_add_entry_to_calendar_403_forbiddenForNonOrganizer(self, mock_build):
        self.e = None
        http = HttpMock('tests/google_errors/calendar_403_forbiddenForNonOrganizer.json', {'status' : '403'})
        service = build("calendar", "v3", http=http)

        try:
            service.events().insert(calendarId='primary').execute(http=http)
        except HttpError as e:
            self.e = e

        mock_build.return_value.events.return_value.insert.return_value.execute.side_effect = self.e
        self.assertEqual(add_entry_to_calendar({"Mock":"403_forbiddenForNonOrganizer"}), 403)

    @patch("add_entry_to_calendar.sleep", return_value=None)
    def test_add_entry_to_calendar_404_notFound(self, _, mock_build):
        self.e = None
        http = HttpMock('tests/google_errors/calendar_404.json', {'status' : '404'})
        service = build("calendar", "v3", http=http)

        try:
            service.events().insert(calendarId='primary').execute(http=http)
        except HttpError as e:
            self.e = e

        mock_build.return_value.events.return_value.insert.return_value.execute.side_effect = self.e
        self.assertEqual(add_entry_to_calendar({"Mock":"404"}), 404)

    def test_add_entry_to_calendar_409(self, mock_build):
        self.e = None
        http = HttpMock('tests/google_errors/calendar_409.json', {'status' : '409'})
        service = build("calendar", "v3", http=http)

        try:
            service.events().insert(calendarId='primary').execute(http=http)
        except HttpError as e:
            self.e = e

        mock_build.return_value.events.return_value.insert.return_value.execute.side_effect = self.e
        self.assertEqual(add_entry_to_calendar({"Mock":"409"}), 409)

    def test_add_entry_to_calendar_410_fullSyncRequired(self, mock_build):
        self.e = None
        http = HttpMock('tests/google_errors/calendar_410_fullSyncRequired.json', {'status' : '409'})
        service = build("calendar", "v3", http=http)

        try:
            service.events().insert(calendarId='primary').execute(http=http)
        except HttpError as e:
            self.e = e

        mock_build.return_value.events.return_value.insert.return_value.execute.side_effect = self.e
        self.assertEqual(add_entry_to_calendar({"Mock":"410_fullSyncRequired"}), 410)

    def test_add_entry_to_calendar_410_updatedMinTooLongAgo(self, mock_build):
        self.e = None
        http = HttpMock('tests/google_errors/calendar_410_updatedMinTooLongAgo.json', {'status' : '410'})
        service = build("calendar", "v3", http=http)

        try:
            service.events().insert(calendarId='primary').execute(http=http)
        except HttpError as e:
            self.e = e

        mock_build.return_value.events.return_value.insert.return_value.execute.side_effect = self.e
        self.assertEqual(add_entry_to_calendar({"Mock":"410"}), 410)

    def test_add_entry_to_calendar_410_deleted(self, mock_build):
        self.e = None
        http = HttpMock('tests/google_errors/calendar_410_deleted.json', {'status' : '410'})
        service = build("calendar", "v3", http=http)

        try:
            service.events().insert(calendarId='primary').execute(http=http)
        except HttpError as e:
            self.e = e

        mock_build.return_value.events.return_value.insert.return_value.execute.side_effect = self.e
        self.assertEqual(add_entry_to_calendar({"Mock":"410"}), 410)

    @patch("add_entry_to_calendar.sleep", return_value=None)
    def test_add_entry_to_calendar_412(self, _, mock_build):
        self.e = None
        http = HttpMock('tests/google_errors/calendar_412.json', {'status' : '412'})
        service = build("calendar", "v3", http=http)

        try:
            service.events().insert(calendarId='primary').execute(http=http)
        except HttpError as e:
            self.e = e

        mock_build.return_value.events.return_value.insert.return_value.execute.side_effect = self.e
        self.assertEqual(add_entry_to_calendar({"Mock":"412"}), 412)

    @patch("add_entry_to_calendar.sleep", return_value=None)
    def test_add_entry_to_calendar_429(self, _, mock_build):
        self.e = None
        http = HttpMock('tests/google_errors/calendar_429.json', {'status' : '429'})
        service = build("calendar", "v3", http=http)

        try:
            service.events().insert(calendarId='primary').execute(http=http)
        except HttpError as e:
            self.e = e

        mock_build.return_value.events.return_value.insert.return_value.execute.side_effect = self.e
        self.assertEqual(add_entry_to_calendar({"Mock":"429"}), 429)

    @patch("add_entry_to_calendar.sleep", return_value=None)
    def test_add_entry_to_calendar_500(self, _, mock_build):
        self.e = None
        http = HttpMock('tests/google_errors/calendar_500.json', {'status' : '500'})
        service = build("calendar", "v3", http=http)

        try:
            service.events().insert(calendarId='primary').execute(http=http)
        except HttpError as e:
            self.e = e

        mock_build.return_value.events.return_value.insert.return_value.execute.side_effect = self.e
        self.assertEqual(add_entry_to_calendar({"Mock":"500"}), 500)
 
    def test_add_entry_to_calendar_any_exception(self, mock_build):
        mock_build.return_value.events.return_value\
        .insert.return_value.execute.side_effect = Exception()
        self.assertRaises(Exception, add_entry_to_calendar({"Mock":"any exception"}))

if __name__ == '__main__':
    unittest.main()