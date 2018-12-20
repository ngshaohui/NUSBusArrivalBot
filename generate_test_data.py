import json
import requests
from bs4 import BeautifulSoup

from utils import BUS_STOP_LIST_URL, BUS_STOP_URL

# TODO include time json was generated
# TODO generate json for bus stops
# TODO move utils into its own folder by including __init__.py
# https://stackoverflow.com/a/21995949/3826254

# TODO try catch
def generateBusStopList():
    url = BUS_STOP_LIST_URL
    response = requests.get(url)

    if response.status_code == requests.codes.ok: # 200 OK
        soup = BeautifulSoup(response.content, 'html.parser')
        json_data = json.loads(soup.text)
        str_data = json.dumps(json_data)

        with open("./test/bus_stop_list.json", "w") as f:
            f.write(str_data)

        return True

    return False


def main():
    generateBusStopList()


if __name__ == "__main__":
    main()
