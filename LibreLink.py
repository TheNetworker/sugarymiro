#!/usr/bin/python
__author__ = "Bassem Aly"
__EMAIL__ = "babdelmageed@juniper.net"

# https://libreview-unofficial.stoplight.io/docs/libreview-unofficial
import requests
from requests.utils import requote_uri
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
import hashlib
from pprint import pprint

url = "https://api-eu.libreview.io"
data = {
    # "Domain": "Libreview",
    # "GatewayType": "LinkUp.Android",
    # "UserName": "basim.alyy@gmail.com",
    # "Password": "QHSbwsj7"
    "email": "basim.alyy@gmail.com                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              ",
    "password": "QHSbwsj89@",
    "trustedDeviceToken": "13661d0dda184885ad8d62e83af814e5"
}

headers = {
    "Content-Type": "application/json;charset=UTF-8",
    "User-Agent": "Webkit",
    "Accept": "application/json",
    # "Authorization": "Bearer 123",
    "Platform": "llu.android",
    # "product": "lv",
    "product": "llu.ios",
    "version": "4.9.0",
    "cache-control": "no-cache",
    "accept-language": "en-US,en;q=0.9,ar;q=0.8,it;q=0.7,fa;q=0.6",
}

jwt_url = url + "/lsl/api/nisperson/getauthenticateduser"
jwt_url = url + "/llu/auth/login"
# print(jwt_url)

response = requests.post(jwt_url, json=data, verify=False, headers=headers)
# pprint(response.json())
jwt = response.json()["data"]["authTicket"]["token"]
headers["authorization"] = "Bearer " + jwt
# pprint(headers)

connections_url = url + "/llu/connections"
response = requests.get(connections_url, verify=False, headers=headers)
# pprint(response.json())

patient_id = response.json()["data"][0]["patientId"]
# print(patient_id)


# jwt = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6ImIyMWZiYzZmLTY5OGItMTFlYi1iOTAyLTAyNDJhYzExMDAwMiIsImZpcnN0TmFtZSI6Ik1hcmlhbSIsImxhc3ROYW1lIjoiQmFzc2VtIiwiY291bnRyeSI6IlNBIiwicmVnaW9uIjoiZXUiLCJyb2xlIjoicGF0aWVudCIsInVuaXRzIjoxLCJwcmFjdGljZXMiOltdLCJjIjoxLCJzIjoibHYiLCJleHAiOjE3MjgyMjYxMDN9.p4i8lfK3zrDcLkudM2VBobxIwGXZ4lUwEoZe5JNRkeU"


logbook_url = url + "/llu/connections/" + patient_id + "/logbook"
graph_url = url + "/llu/connections/" + patient_id + "/graph"

response = requests.get(graph_url, verify=False, headers=headers)
# print(response.request.headers)
# pprint(response.json()["data"])

latest_reading = response.json()["data"]["connection"]["glucoseItem"]
latest_reading_value = latest_reading["Value"]
latest_reading_trend = latest_reading["TrendArrow"]
print(latest_reading)