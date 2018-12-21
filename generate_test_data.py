import json
import requests
from bs4 import BeautifulSoup

from utils import BUS_STOP_LIST_URL, BUS_STOP_URL

# TODO include time json was generated
# TODO move utils into its own folder by including __init__.py
# https://stackoverflow.com/a/21995949/3826254

# TODO try catch


def generateBusStopList():
    url = BUS_STOP_LIST_URL
    response = requests.get(url)

    if response.status_code == requests.codes.ok:  # 200 OK
        soup = BeautifulSoup(response.content, 'html.parser')
        json_data = json.loads(soup.text)
        str_data = json.dumps(json_data)

        with open("./test_data/bus_stop_list.json", "w") as f:
            f.write(str_data)
            print("Successfully downloaded bus_stop_list.json")

        bus_stops = json_data["BusStopsResult"]["busstops"]

        counter = 0
        for bus_stop in bus_stops:
            name = bus_stop["name"]
            url = BUS_STOP_URL + name
            response = requests.get(url)

            # running this on windows will fail for "COM2"
            # https://superuser.com/a/467785
            if name == "COM2":
                name = "COMPUTING"

            if response.status_code == requests.codes.ok:
                soup = BeautifulSoup(response.content, 'html.parser')
                json_data = json.loads(soup.text)
                str_data = json.dumps(json_data)

                with open("test_data/" + name + ".json", "w") as f:
                    f.write(str_data)
                    counter += 1
                    print("Successfully downloaded " + name + ".json")
                    print(str(counter) + "/" +
                          str(len(bus_stops)) + " done")
            else:
                return False

        return True
    else:
        return False


def main():
    generateBusStopList()


if __name__ == "__main__":
    main()
