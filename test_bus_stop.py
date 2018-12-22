import json

from bus_stop import BusStop
from bus_stop_list import BusStopList

# TODO more tests


class TestBusStop:

    # all newly initialised BusStop should be invalid
    def testValidity(self):
        # BusStopList validity
        bus_stops = BusStopList()
        assert bus_stops.valid is False

        # BusStop validity
        with open("./test_data/bus_stop_list.json") as f:
            data = json.load(f)
        bus_stops_data = data["BusStopsResult"]["busstops"]
        bus_stop_list = []
        for bus_stop in bus_stops_data:
            service = BusStop(bus_stop["name"],
                              bus_stop["caption"],
                              bus_stop["latitude"],
                              bus_stop["longitude"])
            bus_stop_list.append(service)
        for bus_stop in bus_stop_list:
            assert bus_stop.valid is False
