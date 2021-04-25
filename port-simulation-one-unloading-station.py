
import simpy
import numpy
import random
from collections import deque


class ShipException(Exception):
    pass


class Ship:

    def __init__(self, env, port,  arrival_time, unload_time, refuel_time, name):
        self.env, self.port, self.name = env, port, name
        self.arrival_time, self.unload_time, self.refuel_time, = arrival_time, unload_time, refuel_time
        self.waiting_unload_time, self.waiting_refuel_time = 0, 0
        self.unloaded, self.refueled = False, False
        self.env.process(self.run_life_cicle())

    def unload_cargo(self, dock):
        # print(f"@{self.env.now} - {self.name}: Started unloading.")
        yield self.env.timeout(self.unload_time)
        self.unloaded = True
        self.port.unloading_station.release(dock)
        # print(f"@{self.env.now} - {self.name}: Finnised unloading.")

    def refuel(self, dock):
        # print(f"@{self.env.now} - {self.name}: Started fueling.")
        yield self.env.timeout(self.refuel_time)
        self.refueled = True
        self.port.refueling_station.release(dock)
        # print(f"@{self.env.now} - {self.name}: Finnised fueling.")

    def run_life_cicle(self):
        # print(f"@{self.env.now} - {self.name}: Arrived at Port.")

        if self.port.idle:
            self.port.process.interrupt()

        try:
            if self.unloaded != True:
                # ! Enter Unload Queue
                unloading_queue = self.env.event()
                self.port.unloading_service_line.append(unloading_queue)
                start_unloading_waiting = self.env.now
                yield unloading_queue

                with self.port.unloading_station.request() as unload_dock:
                    # ! Waiting for Unload Dock
                    yield unload_dock
                    self.waiting_unload_time = self.env.now - start_unloading_waiting
                    # ! Started Unload
                    yield from self.unload_cargo(unload_dock)

            if self.unloaded == True and self.refueled != True:
                # ! Enter Refuel Queue
                refuel_queue = self.env.event()
                self.port.refueling_service_line.append(refuel_queue)
                start_refueling_waiting = self.env.now

                with self.port.refueling_station.request() as refuel_dock:
                    # ! Waiting for Refuel Dock
                    yield refuel_dock
                    self.waiting_refuel_time = self.env.now - start_refueling_waiting

                    # ! Started Refuel
                    yield from self.refuel(refuel_dock)
        except ShipException:
            print(f"@{self.env.now} - Ship cannot get an fueling dock.")


class Port:
    def __init__(self, env, unloading_station, refueling_station):
        self.env, self.unloading_station, self.refueling_station = env, unloading_station, refueling_station
        self.idle = False
        self.unloading_service_line = deque()
        self.refueling_service_line = deque()
        self.process = env.process(self.run_life_cicle())

    def run_life_cicle(self):
        while True:
            if self.unloading_service_line:
                ship_arrived = self.unloading_service_line.popleft()

                with self.unloading_station.request() as u_dock:
                    yield u_dock
                    ship_arrived.succeed()

            if self.refueling_service_line:
                ship_arrived = self.refueling_service_line.popleft()

                with self.refueling_station.request() as r_dock:
                    yield r_dock
                    ship_arrived.succeed()

            else:
                self.idle = True
                # print(f"@{self.env.now} - Port is waiting for Ships.")
                try:
                    yield self.env.event()
                except simpy.Interrupt:
                    self.idle = False
                    # print(f"@{self.env.now} - Ships are waiting for service.")


def generate_ships(env, time, unloading_station, refueling_station):
    i = 0
    ships = []

    while True:

        arrival_time = numpy.random.choice(numpy.arange(5, 19), p=[
            0.01, 0.03, 0.06, 0.07, 0.09, 0.1, 0.11, 0.11, 0.11, 0.09, 0.07, 0.06, 0.05, 0.04])

        unload_time = numpy.random.choice(numpy.arange(9, 17), p=[
            0.2, 0.22, 0.19, 0.16, 0.1, 0.08, 0.03, 0.02])

        refuel_time = numpy.random.choice(numpy.arange(9, 17), p=[
            0.2, 0.22, 0.19, 0.16, 0.1, 0.08, 0.03, 0.02])

        if (env.now+arrival_time) > time:
            unloaded_ships = []
            refueled_ships = []
            for ship in ships:
                if ship.unloaded:
                    unloaded_ships.append(ship)

                if ship.refueled:
                    refueled_ships.append(ship)

            return unloaded_ships, refueled_ships

        yield env.timeout(random.randint(0, arrival_time))
        i += 1
        ships.append(Ship(env, Port(env, unloading_station, refueling_station),
                          arrival_time, unload_time, refuel_time, name=f"Ship {i}"))


def simulation(env, time, number_of_unloading_stations, number_of_refueling_stations):
    unloading_stations = simpy.Resource(env, number_of_unloading_stations)
    refueling_stations = simpy.Resource(env, number_of_refueling_stations)
    ships, ships2 = yield env.process(generate_ships(env, time, unloading_stations, refueling_stations))

    print("Unloaded Ships")
    for ship in ships:
        print(f"@{ship.name} - U: {ship.unloaded} - R:{ship.refueled}")

    print("------------------")
    print("Refueled Ships")
    for ship in ships2:
        print(f"@{ship.name} - U: {ship.unloaded} - R:{ship.refueled}")


def main(time, number_of_unloading_stations, number_of_refueling_stations):
    env = simpy.Environment()
    env.process(simulation(env, time, number_of_unloading_stations,
                number_of_refueling_stations))

    env.run(until=time+1)


if __name__ == "__main__":
    time = 1000
    number_of_unloading_stations = 1
    number_of_refueling_stations = 1
    main(time, number_of_unloading_stations, number_of_refueling_stations)