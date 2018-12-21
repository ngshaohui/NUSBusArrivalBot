from geopy.distance import vincenty

# constants

BUS_STOP_URL = 'http://nextbus.comfortdelgro.com.sg/testMethod.asmx/GetShuttleService?busstopname='
BUS_STOP_LIST_URL = "http://nextbus.comfortdelgro.com.sg/testMethod.asmx/GetBusStops"
SERVICE_PICK_UP_POINT = "http://nextbus.comfortdelgro.com.sg/testMethod.asmx/GetPickupPoint?route_code="

# return [BusStop]
# default of 5 nearest stops


def getNNearestStops(query_point, bus_stops, n=5):
    nearest_stops = []  # insert closest at the front, furthest at the back
    nearest_distances = []

    bus_stop_list = bus_stops.getBusStopList()

    for bus_stop in bus_stop_list:
        stop_location = bus_stop.getLocation()
        current_distance = vincenty(query_point, stop_location).meters

        if len(nearest_stops) == 0:  # initialise reference values
            nearest_distances.append(current_distance)
            nearest_stops.append(bus_stop)
        else:  # insert to array maintaining ascending order
            index = 0
            for distance in nearest_distances:
                if (current_distance < distance):
                    nearest_distances.insert(index, current_distance)
                    nearest_stops.insert(index, bus_stop)
                    break
                index = index + 1

        if len(nearest_stops) == n:
            break

    return nearest_stops
