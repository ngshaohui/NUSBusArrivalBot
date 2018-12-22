import json

from bus_stop import BusStop
from bus_stop_list import BusStopList
from utils import getNNearestStops


class TestUtils:

    # TODO add test coordinates for BTC campus
    def testNearestStops(self):
        central_library_coordinates = (1.296670, 103.773186)
        computing_coordinates = (1.295151, 103.773885)
        sports_hall_coordinates = (1.300758, 103.776001)
        science_canteen_coordinates = (1.296792, 103.780553)
        i3_coordinates = (1.292983, 103.775401)

        # load data
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

        # create BusStopList
        bus_stops = BusStopList()
        bus_stops.bus_stop_list = bus_stop_list
        bus_stops.valid = True

        nearest_stops = getNNearestStops(
            central_library_coordinates, bus_stops)
        ref_central_library_stops = [
            "COMCEN",
            "CENLIB",
            "COM2",
            "STAFFCLUB-OPP",
            "AS7"
        ]
        for i in range(5):
            assert nearest_stops[i].getName() == ref_central_library_stops[i]

        nearest_stops = getNNearestStops(
            computing_coordinates, bus_stops)
        ref_computing_stops = [
            "COM2",
            "CENLIB",
            "BIZ2",
            "COMCEN",
            "AS7"
        ]
        for i in range(5):
            assert nearest_stops[i].getName() == ref_computing_stops[i]

        nearest_stops = getNNearestStops(
            sports_hall_coordinates, bus_stops)
        ref_sports_hall_stops = [
            "CENLIB",
            "BLK-EA-OPP",
            "COM2",
            "BIZ2",
            "AS7"
        ]
        for i in range(5):
            assert nearest_stops[i].getName() == ref_sports_hall_stops[i]

        nearest_stops = getNNearestStops(
            science_canteen_coordinates, bus_stops)
        ref_science_canteen_stops = [
            "BIZ2",
            "COM2",
            "COMCEN",
            "CENLIB",
            "AS7"
        ]
        for i in range(5):
            assert nearest_stops[i].getName() == ref_science_canteen_stops[i]

        nearest_stops = getNNearestStops(
            i3_coordinates, bus_stops)
        ref_i3_stops = [
            "BIZ2",
            "HSSML-OPP",
            "COM2",
            "NUSS-OPP",
            "AS7"
        ]
        for i in range(5):
            assert nearest_stops[i].getName() == ref_i3_stops[i]
