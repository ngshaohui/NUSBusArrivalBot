import datetime
import json
import requests
from bs4 import BeautifulSoup

from bus_stop_location import BusStopLocation

# Constants
BUS_STOP_LIST_URL = "http://nextbus.comfortdelgro.com.sg/testMethod.asmx/GetBusStops"
TIMEOUT = 43200 # 12 hours in seconds

class BusStopLocationList:
    def __init__(self):
        self.time_created = datetime.date.min # datetime
        self.expiry_time = datetime.date.min # datetime
        self.bus_stop_list = [] # [BusStopLocation]
        self.valid = False # bool

    def update(self):
        self.clearShuttleServiceList()

        url = BUS_STOP_LIST_URL
        response = requests.get(url)
        self.time_created = datetime.datetime.now() # datetime
        self.expiry_time = self.time_created + datetime.timedelta(seconds=TIMEOUT) # datetime

        if response.status_code == requests.codes.ok: # 200 OK
            self.valid = True
            soup = BeautifulSoup(response.content, 'html.parser')
            data = json.loads(soup.text)

            bus_stops = data["BusStopsResult"]["busstops"]

            for bus_stop in bus_stops:
                service = BusStopLocation(bus_stop["name"], bus_stop["caption"], bus_stop["latitude"], bus_stop["longitude"])
                self.bus_stop_list.append(service)

            # sort list by name
            self.bus_stop_list.sort(key=lambda x: x.name)
        else:
            self.valid = False

    def clearShuttleServiceList(self):
        del self.bus_stop_list[:]

    def hasExpired(self):
        return datetime.datetime.now() > self.expiry_time
