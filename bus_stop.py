from bs4 import BeautifulSoup
import datetime
import json
import requests

from shuttle_service import ShuttleServiceResult

# Constants
BUS_STOP_LIST_URL = 'http://nextbus.comfortdelgro.com.sg/testMethod.asmx/GetBusStops'
BUS_STOP_URL = 'http://nextbus.comfortdelgro.com.sg/testMethod.asmx/GetShuttleService?busstopname='

class BusStopResult:
  def __init__(self, stop_id):
    url = BUS_STOP_URL + stop_id
    response = requests.get(url)
    self.time_created = datetime.datetime.now() # datetime
    self.expiry_time = self.time_created + datetime.timedelta(seconds=30) # datetime

    if response.status_code == requests.codes.ok: # 200 OK
      self.valid = True
      soup = BeautifulSoup(response.content, 'html.parser')
      data = json.loads(soup.text)
      stop_info = data["ShuttleServiceResult"]

      self.name = stop_info["name"] # str
      self.caption = stop_info["caption"] # str
      self.shuttle_services = [] # [ShuttleServiceResult]
      shuttles = data["ShuttleServiceResult"]["shuttles"]
      for shuttle in shuttles:
        service = ShuttleServiceResult(shuttle["name"], shuttle["arrivalTime"], shuttle["nextArrivalTime"])
        self.shuttle_services.append(service)
    else: # unsuccessful API call
      self.valid = False      


  def update(self):
    self.clearShuttleServiceList()

    url = BUS_STOP_URL + self.name
    response = requests.get(url)
    self.time_created = datetime.datetime.now() # datetime
    self.expiry_time = self.time_created + datetime.timedelta(seconds=30) # datetime

    if response.status_code == requests.codes.ok: # 200 OK
      self.valid = True
      soup = BeautifulSoup(response.content, 'html.parser')
      data = json.loads(soup.text)

      shuttles = data["ShuttleServiceResult"]["shuttles"]

      for shuttle in shuttles:
        service = ShuttleServiceResult(shuttle["name"], shuttle["arrivalTime"], shuttle["nextArrivalTime"])
        self.shuttle_services.append(service)

      # TODO sort resulting list
    else:
      self.valid = False


  def clearShuttleServiceList(self):
    del self.shuttle_services[:]


  def hasExpired(self):
    return datetime.datetime.now() > self.expiry_time


  def dataAsString(self):
    text = ""
    if self.valid:
      text = text + "Bus arrival timings for " + self.caption + "\n\n" #text to be displayed to user

      for service in self.shuttle_services:
        bus_id = service.name
        arrival_time = service.arrival_time
        next_arrival_time = service.next_arrival_time

        text = text + bus_id + "\n" #append bus id
        text = text + "Next: " + arrival_time + "\n" #append next arrival time
        if arrival_time != "-": #show subsequent only if there is a there is a bus arriving next
          text = text + "Subsequent: " + next_arrival_time + "\n" #append subsequent arrival time
        text = text + "\n"

      text = text.rstrip() #rstrip removes the additional \n characters from the back of the string

    else:
      text = text + "Sorry, the bus timing service seems to be unavailable." + "\n"

    return text


  # TODO better method name
  def getData(self):
    if self.hasExpired():
      self.update()

    text = self.dataAsString()

    return text
