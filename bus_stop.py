from bs4 import BeautifulSoup
import datetime
import json
import requests

from shuttle_service import ShuttleService
from utils import BUS_STOP_URL

# Constants
TIMEOUT = 30

class BusStop:
  def __init__(self, name, caption, latitude, longitude):

    self.time_created = datetime.datetime.min # datetime
    self.expiry_time = datetime.datetime.min # datetime
    self.name = name # str
    self.caption = caption # str
    self.latitude = latitude # float
    self.longitude = longitude # float
    self.shuttle_services = [] # [ShuttleService]
    self.valid = False # bool


  def getName(self):
    return self.name


  def getCaption(self):
    return self.caption


  # return (float, float)
  def getLocation(self):
    return (self.latitude, self.longitude)


  def update(self):
    self.clearShuttleServiceList()

    url = BUS_STOP_URL + self.name
    response = requests.get(url)
    self.time_created = datetime.datetime.now() # datetime
    self.expiry_time = self.time_created + datetime.timedelta(seconds=TIMEOUT) # datetime

    if response.status_code == requests.codes.ok: # 200 OK
      self.valid = True
      soup = BeautifulSoup(response.content, 'html.parser')
      data = json.loads(soup.text)

      shuttles = data["ShuttleServiceResult"]["shuttles"]

      for shuttle in shuttles:
        service = ShuttleService(shuttle["name"], shuttle["arrivalTime"], shuttle["nextArrivalTime"])
        self.shuttle_services.append(service)

      # sort list by name
      self.shuttle_services.sort(key=lambda x: x.name)
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
        bus_name = service.name
        arrival_time = service.arrival_time
        next_arrival_time = service.next_arrival_time

        text = text + bus_name + "\n" #append bus id
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
