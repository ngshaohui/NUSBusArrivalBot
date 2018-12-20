import datetime
import json
import requests
from bs4 import BeautifulSoup

from bus_stop import BusStop
from utils import BUS_STOP_LIST_URL

# Constants
TIMEOUT = 43200 # 12 hours in seconds

class BusStopList:
    def __init__(self):
        self.time_created = datetime.datetime.min # datetime
        self.expiry_time = datetime.datetime.min # datetime
        self.bus_stop_list = [] # [BusStop]
        self.valid = False # bool


    # return [BusStop]
    def getBusStopList(self):
        if not self.valid:
            self.update()
        return self.bus_stop_list


    def update(self):
        self.clearBusStopList()

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
                service = BusStop(bus_stop["name"], bus_stop["caption"], bus_stop["latitude"], bus_stop["longitude"])
                self.bus_stop_list.append(service)

            # sort list by name
            self.bus_stop_list.sort(key=lambda x: x.name)
        else:
            self.valid = False


    # TODO return?
    # side effect: clears the list self.bus_stop_list
    def clearBusStopList(self):
        del self.bus_stop_list[:]


    # return bool
    def hasExpired(self):
        return datetime.datetime.now() > self.expiry_time


    # TODO raise error if not found
    def getStopName(self, bus_stop_caption):
        for bus_stop in self.bus_stop_list:
            if bus_stop_caption == bus_stop.getCaption():
                return bus_stop.getName()


    # TODO raise error if not found
    def getStopCaption(self, bus_stop_name):
        for bus_stop in self.bus_stop_list:
            if bus_stop_name == bus_stop.getName():
                return bus_stop.getCaption()


    # TODO better method name
    # TODO raise error if not found
    # can get bus stop by either name or caption
    # defaults to using name if both are provided
    def getBusStopData(self, name):
        for bus_stop in self.bus_stop_list:
            if bus_stop.name == name:
                return bus_stop.getData()
