import simpy
import numpy
import pandas
import random
import matplotlib.pyplot as plt
from collections import deque


def poisson_distribution():
    return numpy.random.poisson(lam=10, size=1)[0]


def gamma_distribution():
    return numpy.random.gamma(shape=10, size=1)[0]


def studied_distribuition():
    return numpy.random.choice(numpy.arange(5, 19), p=[
        0.01, 0.03, 0.06, 0.07, 0.09, 0.1, 0.11, 0.11, 0.11, 0.09, 0.07, 0.06, 0.05, 0.04])


class ShipException(Exception):
    pass


class Ship:

    def __init__(self, env, port, arrival_time, unload_time, refuel_time, name):
        self.env, self.port, self.name = env, port, name
        self.unloaded, self.refueled = False, False
        self.arrival_time, self.unload_time, self.refuel_time, =  arrival_time, unload_time, refuel_time
        self.waiting_unload_time, self.waiting_refuel_time = numpy.NaN, numpy.NaN
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

    def to_dataframe(self):
        return {
            'name': self.name,
            'unloaded': self.unloaded,
            'refueled': self.refueled,
            'arrival_time': self.arrival_time,
            'unload_time': self.arrival_time,
            'refuel_time': self.refuel_time,
            'waiting_unload_time': self.waiting_refuel_time,
            'waiting_refuel_time': self.waiting_refuel_time,
        }


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


def generate_ships(env, time, unloading_station, refueling_station, arrival_distribution, unload_distribution, refuel_distribution):
    i = 0
    ships = []
    port = Port(env, unloading_station, refueling_station)

    while True:
        arrival_time = arrival_distribution()
        unload_time = unload_distribution()
        refuel_time = refuel_distribution()

        if (env.now + arrival_time) >= time:
            return ships, port
        else:
            yield env.timeout(random.randint(0, arrival_time))
            i += 1
            ships.append(Ship(env, port, arrival_time, unload_time,
                         refuel_time, name=f"Ship {i}"))


def simulation(env, time, number_of_unloading_stations, number_of_refueling_stations, arrival_distribution, unload_distribution, refuel_distribution):
    unloading_stations = simpy.Resource(env, number_of_unloading_stations)
    refueling_stations = simpy.Resource(env, number_of_refueling_stations)
    ships, port = yield env.process(generate_ships(env, time, unloading_stations, refueling_stations, arrival_distribution, unload_distribution, refuel_distribution))
    simulation_report(ships, port, arrival_distribution,
                      unload_distribution, refuel_distribution)


def simulation_report(ships, port, arrival_distribution, unload_distribution, refuel_distribution):
    plt.figure(1)
    filename = f"img/unload_{arrival_distribution.__name__}_{unload_distribution.__name__}_{refuel_distribution.__name__}.png"

    Y = [(ship.waiting_unload_time)
         for ship in ships if ship.unloaded == True]
    X = range(0, len(Y))

    plt.plot(X, Y, "-o")
    plt.xlabel("Number of ship")
    plt.ylabel("Waiting time for unloading")
    plt.xticks(X)
    plt.savefig(filename)
    #!!! ----------
    plt.figure(2)
    filename = f"img/refuel_{arrival_distribution.__name__}_{unload_distribution.__name__}_{refuel_distribution.__name__}.png"

    Y = [(ship.waiting_refuel_time)
         for ship in ships if ship.refueled == True]
    X = range(0, len(Y))

    plt.plot(X, Y, "-o")
    plt.xlabel("Number of ship")
    plt.ylabel("Waiting time for unloading")
    plt.xticks(X)
    plt.savefig(filename)
    #!!! ----------
    plt.figure(3)
    filename = f"img/unload_queue_{arrival_distribution.__name__}_{unload_distribution.__name__}_{refuel_distribution.__name__}.png"
    X = [timestamp[0]for timestamp in port.unloading_service_line_history]
    Y = [timestamp[1]for timestamp in port.unloading_service_line_history]

    plt.plot(X, Y, "-o")
    plt.xlabel("Time")
    plt.ylabel("Unloading Queue Lenght")
    plt.xticks(X)
    plt.savefig(filename)
    #!!! ----------
    plt.figure(4)
    filename = f"img/refuel_queue_{arrival_distribution.__name__}_{unload_distribution.__name__}_{refuel_distribution.__name__}.png"
    X = [timestamp[0]for timestamp in port.refueling_service_line_history]
    Y = [timestamp[1]for timestamp in port.refueling_service_line_history]

    plt.plot(X, Y, "-o")
    plt.xlabel("Time")
    plt.ylabel("Refueling Queue Lenght")
    plt.xticks(X)
    plt.savefig(filename)

    df_ships = pandas.DataFrame.from_records([s.to_dataframe() for s in ships])

    df_unloaded = pandas.DataFrame.from_records([s.to_dataframe() for s in [ship
                                                                            for ship in ships if ship.unloaded == True]])
    df_refueled = pandas.DataFrame.from_records([s.to_dataframe() for s in [ship
                                                                            for ship in ships if ship.refueled == True]])

    df_unloaded.drop(
        columns=['arrival_time',  'refuel_time', 'waiting_refuel_time'], inplace=True)
    df_refueled.drop(
        columns=['arrival_time', 'unload_time', 'waiting_unload_time'], inplace=True)

    print(df_unloaded.describe())
    print(df_refueled.describe())


def main(time, number_of_unloading_stations, number_of_refueling_stations, arrival_distribution, unload_distribution, refuel_distribution):
    env = simpy.Environment()
    env.process(simulation(env, time, number_of_unloading_stations,
                number_of_refueling_stations, arrival_distribution, unload_distribution, refuel_distribution))
    env.run(until=(time + 5))


if __name__ == "__main__":
    distributions = {0: poisson_distribution,
                     1: gamma_distribution, 2: studied_distribuition}

    arrival_distribution = distributions.get(0)
    unload_distribution = distributions.get(0)
    refuel_distribution = distributions.get(0)

    time = 8*30
    number_of_unloading_stations = 1
    number_of_refueling_stations = 1

    main(time, number_of_unloading_stations, number_of_refueling_stations,
         arrival_distribution, unload_distribution, refuel_distribution)
