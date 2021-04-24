
import simpy
import numpy
import random
from collections import deque


class ShipException(Exception):
    pass


class Ship:

    def __init__(self, env, port,  arrival_time, unload_time, refuel_time, name):
        self.env, self.port, self.name, self.arrival_time, self.unload_time, self.refuel_time = env, port, name, arrival_time, unload_time, refuel_time
        self.env.process(self.run_life_cicle())

    def unload_cargo(self):
        yield self.env.timeout(self.unload_time)

    def refuel(self):
        yield self.env.timeout(self.refuel_time)

    def run_life_cicle(self):
        print(f"@{self.env.now} - {self.name}: Arrived at port.")
        dock = self.env.event()
        self.port.unloading_service_line.append(dock)

        if self.port.idle:
            self.port.process.interrupt()

        try:
            print(
                f"@{self.env.now} - {self.name} is waiting for an unloading dock.")
            yield dock

            with self.port.unloading_station.request() as dock:
                print(
                    f"@{self.env.now} - {self.name}: Arrived at unloading station dock.")
                yield dock

                print(f"@{self.env.now} - {self.name}: Started unloading.")

                yield from self.unload_cargo()
                # * Release Resource
                self.port.unloading_station.release(dock)
                print(f"@{self.env.now} - {self.name}: Finnised unloading.")

                self.port.fueling_service_line.append(dock)

                with self.port.fueling_station.request() as dock:
                    print(
                        f"@{self.env.now} - {self.name}: Arrived at fuel station dock.")
                    yield dock

                    print(f"@{self.env.now} - {self.name}: Started fueling.")
                    yield from self.refuel()
                    # * Release Resource
                    self.port.fueling_station.release(dock)
                    print(f"@{self.env.now} - {self.name}: Finnised fueling.")

        except ShipException:
            print(f"@{self.env.now} - Ship cannot get an unloading dock.")


class Port:
    def __init__(self, env, unloading_station, fueling_station):
        self.env, self.unloading_station, self.fueling_station = env, unloading_station, fueling_station
        self.idle = False
        self.unloading_service_line = deque()
        self.fueling_service_line = deque()
        self.process = env.process(self.run_life_cicle())

    def run_life_cicle(self):
        while True:
            if self.unloading_service_line:
                ship_arrived = self.unloading_service_line.popleft()

                with self.unloading_station.request() as dock:
                    try:
                        yield dock
                        ship_arrived.succeed()
                    except simpy.Interrupt:
                        ship_arrived.fail(ShipException())

            if self.fueling_service_line:
                ship_arrived = self.fueling_service_line.popleft()

                with self.fueling_service_line.request() as dock:
                    try:
                        yield dock
                        ship_arrived.succeed()
                    except simpy.Interrupt:
                        ship_arrived.fail(ShipException())

            else:
                self.idle = True
                # print(f"@{self.env.now} - Port is waiting for Ships.")
                try:
                    yield self.env.event()
                except simpy.Interrupt:
                    self.idle = False
                    # print(f"@{self.env.now} - Ships are waiting for service.")


def generate_ships(env, unloading_station, fueling_station):
    i = 0
    arrival_time = numpy.random.choice(numpy.arange(5, 19), p=[
        0.01, 0.03, 0.06, 0.07, 0.09, 0.1, 0.11, 0.11, 0.11, 0.09, 0.07, 0.06, 0.05, 0.04])

    unload_time = numpy.random.choice(numpy.arange(9, 17), p=[
        0.2, 0.22, 0.19, 0.16, 0.1, 0.08, 0.03, 0.02])

    refuel_time = numpy.random.choice(numpy.arange(9, 17), p=[
        0.2, 0.22, 0.19, 0.16, 0.1, 0.08, 0.03, 0.02])

    while True:
        yield env.timeout(random.randint(0, arrival_time))
        i += 1
        Ship(env, Port(env, unloading_station, fueling_station),
             arrival_time, unload_time, refuel_time, name=f"Ship {i}")


def main(time):
    env = simpy.Environment()
    # * Número de estações de descarga
    unloading_station = simpy.Resource(env, 1)
    # * Número de estações de abastecimento
    fueling_station = simpy.Resource(env, 1)
    env.process(generate_ships(env,  unloading_station, fueling_station))
    env.run(until=time)


if __name__ == "__main__":
    time = 1000
    main(time)
