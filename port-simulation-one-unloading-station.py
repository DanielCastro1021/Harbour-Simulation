
import simpy
import numpy
import random
import matplotlib.pyplot as plt
from collections import deque


class ShipException(Exception):
    pass


class Ship:

    def __init__(self, env, port, unload_time, refuel_time, name):
        self.env, self.port, self.name = env, port, name
        self.unload_time, self.refuel_time, =  unload_time, refuel_time
        self.waiting_unload_time, self.waiting_refuel_time = 0, 0
        self.unloaded, self.refueled = False, False
        self.env.process(self.run_life_cicle())

    def enter_unloading_queue(self):
        self.port.unloading_service_line_history.append(
            [self.env.now, len(self.port.unloading_service_line)])

    def enter_refueling_queue(self):
        self.port.refueling_service_line_history.append(
            [self.env.now, len(self.port.refueling_service_line)])

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
            if self.unloaded == False:
                # ! Enter Unload Queue
                unloading_queue = self.env.event()
                self.port.unloading_service_line.append(unloading_queue)
                self.enter_unloading_queue()
                start_unloading_waiting = self.env.now
                yield unloading_queue

                with self.port.unloading_station.request() as unload_dock:
                    # ! Waiting for Unload Dock
                    yield unload_dock
                    self.waiting_unload_time = self.env.now - start_unloading_waiting
                    # ! Started Unload
                    yield from self.unload_cargo(unload_dock)

            if self.unloaded == True and self.refueled == False:
                # ! Enter Refuel Queue
                refuel_queue = self.env.event()
                self.port.refueling_service_line.append(refuel_queue)
                self.enter_refueling_queue()
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
        self.unloading_service_line, self.unloading_service_line_history = deque(), []
        self.refueling_service_line, self.refueling_service_line_history = deque(), []
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
    port = Port(env, unloading_station, refueling_station)

    while True:

        arrival_time = numpy.random.choice(numpy.arange(5, 19), p=[
            0.01, 0.03, 0.06, 0.07, 0.09, 0.1, 0.11, 0.11, 0.11, 0.09, 0.07, 0.06, 0.05, 0.04])

        unload_time = numpy.random.choice(numpy.arange(9, 17), p=[
            0.2, 0.22, 0.19, 0.16, 0.1, 0.08, 0.03, 0.02])

        refuel_time = numpy.random.choice(numpy.arange(9, 17), p=[
            0.2, 0.22, 0.19, 0.16, 0.1, 0.08, 0.03, 0.02])

        if (env.now + arrival_time) >= time:
            return ships, port
        else:
            yield env.timeout(random.randint(0, arrival_time))
            i += 1
            ships.append(Ship(env, port, unload_time,
                         refuel_time, name=f"Ship {i}"))


def stats_and_graphs(ships, port):
    plt.figure(1)
    filename = "img/unload.jpg"

    Y = [(ship.waiting_unload_time)
         for ship in ships if ship.unloaded == True]
    X = range(0, len(Y))

    plt.plot(X, Y, "-o")
    plt.xlabel("Number of ships")
    plt.ylabel("Waiting time for unloading")
    plt.xticks(X)
    plt.savefig(filename)
    #!!! ----------
    plt.figure(2)
    filename = "img/refuel.jpg"
    Y = [(ship.waiting_refuel_time)
         for ship in ships if ship.refueled == True]
    X = range(0, len(Y))

    plt.plot(X, Y, "-o")
    plt.xlabel("Number of ships")
    plt.ylabel("Waiting time for unloading")
    plt.xticks(X)
    plt.savefig(filename)
    #!!! ----------
    plt.figure(3)
    filename = "img/unload_queue.jpg"
    X = [timestamp[0]for timestamp in port.unloading_service_line_history]
    Y = [timestamp[1]for timestamp in port.unloading_service_line_history]

    plt.plot(X, Y, "-o")
    plt.xlabel("Time")
    plt.ylabel("Unloading Queue Lenght")
    plt.xticks(X)
    plt.savefig(filename)
    #!!! ----------
    plt.figure(4)
    filename = "img/refuel_queue.jpg"
    X = [timestamp[0]for timestamp in port.refueling_service_line_history]
    Y = [timestamp[1]for timestamp in port.refueling_service_line_history]

    plt.plot(X, Y, "-o")
    plt.xlabel("Time")
    plt.ylabel("Refueling Queue Lenght")
    plt.xticks(X)
    plt.savefig(filename)


def simulation(env, time, number_of_unloading_stations, number_of_refueling_stations):
    unloading_stations = simpy.Resource(env, number_of_unloading_stations)
    refueling_stations = simpy.Resource(env, number_of_refueling_stations)
    ships, port = yield env.process(generate_ships(env, time, unloading_stations, refueling_stations))
    stats_and_graphs(ships, port)


def main(time, number_of_unloading_stations, number_of_refueling_stations):
    env = simpy.Environment()
    env.process(simulation(env, time, number_of_unloading_stations,
                number_of_refueling_stations))
    env.run(until=(time + 5))


if __name__ == "__main__":
    time = 100
    number_of_unloading_stations = 3
    number_of_refueling_stations = 1
    main(time, number_of_unloading_stations, number_of_refueling_stations)
