import json

from bus_stop import BusStop

# TODO should have more test date to load


class TestBusStop:

    # all newly initialised BusStop should be invalid
    def test_validity(self):
        with open("./test/bus_stop_list.json") as f:
            data = json.load(f)
        bus_stops = data["BusStopsResult"]["busstops"]
        bus_stop_list = []
        for bus_stop in bus_stops:
                service = BusStop(bus_stop["name"],
                                  bus_stop["caption"],
                                  bus_stop["latitude"],
                                  bus_stop["longitude"])
                bus_stop_list.append(service)
        for bus_stop in bus_stop_list:
            assert bus_stop.valid is False
