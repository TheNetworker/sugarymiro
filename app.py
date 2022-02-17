#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = "Bassem Aly"
__email__ = "basim.alyy@gmail.com"
__company__ = "TheNetworker"
__version__ = 0.1

# -----

import requests
from requests.utils import requote_uri
import urllib3
import os
import hashlib
from errors import *
from pprint import pprint
import datetime
import pytz
import time

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class api_client(object):
    def __init__(self, url,
                 username="",
                 password="",
                 api_key="",
                 headers={'Accept': 'application/json', "Content-Type": "application/json", },
                 params={},
                 verify=False):


        _ = requote_uri("https://" + url if not url.startswith("https://") else url)

        self.url = _.strip() + "/" if _[-1] != '/' else self.url.strip()
        self.username = username
        self.password = password
        self.api_key = api_key
        self.headers = headers
        self.params = params
        self.verify = verify

    def get(self, expected_data_is_in_json=True, **kwargs, ):
        '''

        :param expected_data_is_in_json: check whether the data payload or the response is in json format or not
        :param kwargs: accept the `api_endpoint` and `payload` as parameters
        :return: return the response
        '''
        self._ = requests.get(url=self.url + kwargs.get("api_endpoint"),
                              headers=self.headers,
                              params=self.params,
                              verify=self.verify,
                              )

        if self._.status_code == requests.codes.ok:

            if expected_data_is_in_json:
                response = {}
                try:
                    self.data = self._.json()
                    response["data"] = self.data
                    response["status_code"] = self._.status_code
                    response["error_message"] = 0
                    return response
                except Exception as e:  # we will try to avoid exceptions to not halt the program
                    response["data"] = []
                    response["error_message"] = "Error: " + str(e)
                    return response
            else:
                return self._.text

    def post(self, expected_data_is_in_json=True, **kwargs, ):
        ''':
        :param expected_data_is_in_json: check whether the data payload or the response is in json format or not
        :param kwargs: accept the `api_endpoint` and `payload` as parameters
        :return: return the response

        '''
        if expected_data_is_in_json:
            response = {}
            self._ = requests.post(url=self.url + kwargs.get("api_endpoint"),
                                   headers=self.headers,
                                   params=self.params,
                                   verify=self.verify,
                                   json=kwargs.get("payload"),
                                   )

            if self._.status_code == requests.codes.ok:
                response["status_code"] = self._.status_code
                response["error_message"] = 0



            else:
                response["status_code"] = self._.status_code
                response["error_message"] = self._.text

            return response

    def print_details(self):

        pprint("URL: " + self._.request.url)

        try:
            pprint("Status Code: " + str(self._.status_code))
        except AttributeError:
            print("Status Code: None")

        try:
            pprint("Response Content: " + self._.content.decode("utf-8"))
        except AttributeError:
            print("Response Content: None")

        try:
            pprint("Request Body: " + self._.request.body.decode("utf-8"))
        except AttributeError:
            print("Response Body: None")

        try:
            pprint("Request Headers: " + self._.request.headers.decode("utf-8"))
        except AttributeError:
            print("Response Headers: None")


class NightScout_Tools(api_client):
    def __init__(self, user_timezone, target_reading, low_reading,
                 high_reading, margin, **kwargs):

        super().__init__(**kwargs)
        self.api_token = hashlib.sha1(api_key.encode()).hexdigest()
        self.headers["API_SECRET"] = self.api_token
        self.params = {"count": "14"}  # 14 readings should be okay to cover 60 minutes with 2 readings buffer

        self.target_reading = target_reading
        self.low_reading = low_reading
        self.high_reading = high_reading
        self.margin = margin
        self.user_timezone = user_timezone
        self.refined_data = []

        self.hypoglycemia_directions = ["FortyFiveDown", "SingleDown", "DoubleDown"]  # >70
        self.hyperglycemia_directions = ["FortyFiveUp", "SingleUp", "DoubleUp"]  # <180
        self.default_retry_time = 3650  # around 1 hour

    def _get_actual_timezone_in_the_entry(self, sgv_epoch_time, ):
        '''
        A method used to translate the epoch time found in SGV entry to the actual timezone at user end
        :param sgv_epoch_time: The epoch time of the SGV entry
        :return: datetime object of the sgv entry
        '''
        return datetime.datetime.fromtimestamp(
            divmod(sgv_epoch_time, 1000)[0], tz=pytz.timezone(self.user_timezone))

    def get_current_date_now(self):
        '''
        A method used to get the current  timezone at user end
        :return: datetime object of the actual timezone
        '''
        return datetime.datetime.now(
            tz=pytz.timezone(self.user_timezone))  # returns the current time in the user timezone with epoch format

    def get_entries(self, type="sgv"):
        '''
        A method used to get the SGV entries from Nightscout
        :param type: operate over the SGV entries or the BG entries
        :return: return the SGV entries after refining them
        '''
        entries = self.get(api_endpoint=api_endpoints[type])
        data = entries.get("data")
        error = entries.get("error_message")
        # pprint(entries)
        if data and not error:
            if isinstance(data, list):
                for index, value in enumerate(data):
                    temp_dict = {}
                    temp_dict[type] = value[type]
                    entry_date = value["date"]

                    entry_actual_date_datetime = self._get_actual_timezone_in_the_entry(entry_date)

                    number_of_seconds_difference = abs(
                        (entry_actual_date_datetime - self.get_current_date_now()).total_seconds())

                    # temp_dict["actual_date_in_epoch"] = int(entry_actual_date_datetime.timestamp()) #epoch
                    temp_dict["actual_date_in_str"] = entry_actual_date_datetime.isoformat()  # isoformat

                    temp_dict["original_date_in_str"] = value["dateString"]
                    # temp_dict["original_date_in_epoch"] = entry_date
                    temp_dict["direction"] = value["direction"]
                    temp_dict["seconds_difference"] = number_of_seconds_difference
                    temp_dict["current_date_now"] = self.get_current_date_now().isoformat()
                    self.refined_data.append(temp_dict)
        else:
            self.refined_data = []

        return self.refined_data

    def data_is_valid(self, type="sgv"):
        '''
        A method used to check if the data is valid or not
        :param type: operate over the SGV entries or the BG entries
        :return: True if the data is valid, False otherwise
        '''
        self.refined_data = self.get_entries(type=type)
        # print(self.refined_data[-1])
        if self.refined_data:
            if self.refined_data[-1][
                "seconds_difference"] > 6000:  # if the last entry is more than 60 minutes old then data is not valid
                return False  # ignore

        return True

    def too_high_too_low_for_long_time_algorithm(self, type="sgv"):  # nightscout Entrypoint
        '''
        An algorithm used to check if the given SGV entries are staying too high or too low for long time
        :param type: operate over the SGV entries or the BG entries
        :return: the response_payload to be sent to the user
        '''

        response_payload = {}
        response_payload["action"] = ""
        response_payload["sleep_in_sec"] = self.default_retry_time
        response_payload["mean_value_within_duration"] = 0
        response_payload["expected"] = 0
        response_payload["error_message"] = 0

        if self.data_is_valid(type=type):  # if the data is valid (like serializer in Django Rest Framework :D)
            sgvs = [sgv["sgv"] for sgv in self.refined_data]
            mean_sgv_within_duration = sum(sgvs) / len(sgvs)
            last_entry_direction = self.refined_data[-1]["direction"]

            mean_high_target = (self.target_reading + self.high_reading) / 2
            mean_low_target = (self.target_reading + self.low_reading) / 2
            response_payload["last_data_entry"] = self.refined_data[0]

            # Test Data
            # mean_sgv_within_duration = 400 #testing the high
            # mean_sgv_within_duration = 50 #testing the low
            # last_entry_direction = "FLAT" #bypass the last entry direction check (i.e action:wait)

            if mean_sgv_within_duration > (mean_high_target + self.margin):  # 270
                if last_entry_direction in self.hypoglycemia_directions:
                    response_payload["action"] = "wait"
                    response_payload["sleep_in_sec"] = 930  # wait for another ~ 15 minutes and check again
                    response_payload["mean_value_within_duration"] = mean_sgv_within_duration
                    response_payload["expected"] = mean_high_target + self.margin

                    return response_payload  # snooze for ~ 15 minutes and then check again

                else:  # either 'FLAT' or 'NOT COMPUTABLE'
                    response_payload["action"] = "high_alert"
                    response_payload["sleep_in_sec"] = self.default_retry_time
                    response_payload["mean_value_within_duration"] = mean_sgv_within_duration
                    response_payload["expected"] = mean_low_target + self.margin

                    return response_payload


            elif mean_sgv_within_duration < (mean_low_target - self.margin):

                if last_entry_direction in self.hyperglycemia_directions:

                    response_payload["action"] = "wait"
                    response_payload["sleep_in_sec"] = 930  # wait for another 15 minutes and check again
                    response_payload["mean_value_within_duration"] = mean_sgv_within_duration
                    response_payload["expected"] = mean_low_target + self.margin
                    return response_payload  # snooze for ~ 15 minutes and then check again

                else:  # either 'FLAT' or 'NOT COMPUTABLE'
                    response_payload["action"] = "low_alert"
                    response_payload["sleep_in_sec"] = self.default_retry_time
                    response_payload["mean_value_within_duration"] = mean_sgv_within_duration
                    response_payload["expected"] = mean_low_target + self.margin
                    return response_payload

            else:
                return response_payload

        else:
            response_payload[
                "error_message"] = "Returned data from NightScout are old, Seconds difference is {}, Retrying in {} seconds".format(
                self.refined_data[-1]["seconds_difference"], self.default_retry_time)
            response_payload["sleep_in_sec"] = self.default_retry_time

    def high_standard_deviation_between_sgvs(self, type="sgv"):
        raise NotImplementedError


class notification_manager(object):
    def __init__(self, user, notification_type, notification_data):
        self.user = user
        self.notification_type = notification_type
        self.notification_data = notification_data

    # todo: register different types of notifications here


def dispatch():
    print("dispatching...")
    next_sleep = 3650
    ifttt_url = "https://maker.ifttt.com"
    ns_agent = NightScout_Tools(url=ns_url,
                                api_key=api_key,
                                user_timezone=mytz,
                                target_reading=target_reading,
                                low_reading=low_reading,
                                high_reading=high_reading,
                                margin=margin,
                                )
    supported_algorithms = [ns_agent.too_high_too_low_for_long_time_algorithm]
    for i in supported_algorithms:
        ifttt_payload = {}
        ns_response = i()
        next_sleep = ns_response["sleep_in_sec"]
        print("The nightscout response is:")
        pprint(ns_response)

        if ns_response["action"] == "high_alert" or ns_response["action"] == "low_alert":
            print("start sending to IFTTT webhook")

            ifttt_payload["value1"] = ns_response["mean_value_within_duration"]
            ifttt_payload["value2"] = ns_response["expected"]
            ifttt_payload["value3"] = int(ns_response["sleep_in_sec"] / 60)

            ifttt_agent = api_client(url=ifttt_url)
            ifttt_response = ifttt_agent.post(api_endpoint=api_endpoints["ifttt"],
                                              payload=ifttt_payload)

            # print(ifttt_response)
            # print(ifttt_agent.print_details())
            if ifttt_response["status_code"] != 200:  # something wrong happen with IFTTT, will try again in 30sec
                print("received error from IFTTT, will try again in 30sec")
                next_sleep = 30

        if ns_response["action"] == "wait":
            print("Waiting...")
            next_sleep = ns_response["sleep_in_sec"]
        else:
            print("No action taken, everything seems normal")

    return next_sleep


if __name__ == '__main__':
    while True:
        # Get User Data
        ns_url = os.environ.get("NightScout_URL")  # NightScout URL
        api_key = os.environ.get("NightScout_API_Key")  # NightScout API Key
        ifttt_key = os.environ.get("Your_IFTTT_Key")  # IFTTT Key
        mytz = os.environ.get("Your_Time_Zone", "Asia/Riyadh")  # Your Time Zone
        nightshift_only = os.environ.get("NightShift_Only", "yes")  # NightShift Only
        target_reading = int(os.environ.get("Target_Reading", 109))  # Target Reading
        low_reading = int(os.environ.get("Low_Reading", 65))  # Target Reading
        high_reading = int(os.environ.get("High_Reading", 354))  # Target Reading
        margin = int(os.environ.get("Margin", 10))  # Target Reading
        api_endpoints = {
            "sgv": "api/v1/entries/sgv.json",
            "ifttt": "trigger/{}/with/key/{}".format("average_is_not_ok", ifttt_key),
        }
        time_now_at_user = datetime.datetime.now(pytz.timezone(mytz))
        print("Time now at user is: {}".format(time_now_at_user))
        # for debugging only and replicating the environments in case of any issues
        # for k, v in sorted(os.environ.items()):
        #     print(k + ':', v)
        # print('\n')


        if nightshift_only.lower() == "yes":
            print("working in nightshift only mode")
            nightshift_start_hour = 21
            # print(time_now_at_user)
            # print(time_now_at_user.hour)
            if time_now_at_user.hour >= nightshift_start_hour or time_now_at_user.hour in range(0, 10):
                print("Nightshift started.")
                next_sleep = dispatch()

            elif time_now_at_user.hour == (nightshift_start_hour - 1): #we're just before the starting of nightshift (i.e the user started the app at 20:30)
                date_1 = '{}/{}/{} {}:{}:{}'.format(time_now_at_user.day,
                                                    time_now_at_user.month,
                                                    time_now_at_user.year,
                                                    time_now_at_user.hour,
                                                    time_now_at_user.minute,
                                                    time_now_at_user.second,
                                                    )
                date_2 = '{}/{}/{} {}:00:00'.format(time_now_at_user.day,
                                                    time_now_at_user.month,
                                                    time_now_at_user.year,
                                                    nightshift_start_hour,
                                                    )   #nightshift starts at 21:00
                date_format_str = '%d/%m/%Y %H:%M:%S'
                start = datetime.datetime.strptime(date_1, date_format_str)
                end = datetime.datetime.strptime(date_2, date_format_str)
                # Get the interval between two datetimes as timedelta object
                diff = end - start
                print('Difference between two datetimes in seconds: {}'.format(diff.seconds))
                next_sleep = diff.total_seconds()

            else: #anything else
                next_sleep = 3650 # sleep for another hour till next nightshift

        else: # running all the day
            next_sleep = dispatch()

        next_sleep = int(next_sleep)
        print("{} - Next check is in ~ {} minutes".format(time_now_at_user, int(next_sleep/60)))
        print("==================================================================")
        # next_sleep = 20
        time.sleep(next_sleep)
