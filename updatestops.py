from bs4 import BeautifulSoup
import lxml
import json
import requests

def getStops():
    url = 'http://nextbus.comfortdelgro.com.sg/testMethod.asmx/GetBusStops'
    result = requests.get(url)

    soup = BeautifulSoup(result.content, 'html.parser')
    result = json.loads(soup.text)

    return result["BusStopsResult"]

def main():
    stops = getStops()
    with open('stops.json', 'w') as outfile:
        json.dump(stops, outfile)

if __name__ == "__main__":
    main()
