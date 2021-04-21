import simpy
import random
from collections import deque


class ShipException(Exception):
    pass


class Ship:
    TIME_UNLOADING_CARGO = 5  # ! Random Number
    TIME_REFUEL = 10  # ! Random Number

    def __init__(self, env, port, name):
        self.env, self.port, self.name = env, port, name
        self.env.process(self.run_life_cicle())

    def unload_cargo(self):
        yield self.env.timeout(Ship.TIME_UNLOADING_CARGO)

    def refuel(self):
        yield self.env.timeout(Ship.TIME_REFUEL)

    def run_life_cicle(self):
        print(f"@{self.env.now} - {self.name}: Arrived At Port")
        arrived = self.env.event()
        self.port.service_line.append(arrived)

        if self.port.idle:
            self.port.process.interrupt()

        try:
            yield arrived
            print(f"@{self.env.now} - Ship can unload")

            with self.port.unloading_station.request() as req:
                print(f"@{self.env.now} - {self.name}: Arrived Unloading Station")
                yield req
                print(f"@{self.env.now} - {self.name}: Started Unloading.")
                yield from self.unload_cargo()
                print(f"@{self.env.now} - {self.name}: Finnised Unloading.")

                with self.port.fueling_station.request() as req:
                    print(f"@{self.env.now} - {self.name}: Arrived Fuel Station")
                    yield req
                    print(f"@{self.env.now} - {self.name}: Started Fueling.")
                    yield from self.unload_cargo()
                    print(f"@{self.env.now} - {self.name}: Finnised Fueling.")
        except ShipException:
            print(f"@{self.env.now} - Ship cannot unload")


class Port:
    def __init__(self, env, unloading_station, fueling_station):
        self.env, self.unloading_station, self.fueling_station = env, unloading_station, fueling_station
        self.idle = False
        self.service_line = deque()
        self.process = env.process(self.run_life_cicle())

    def run_life_cicle(self):
        while True:
            if self.service_line:
                ship_arrived = self.service_line.popleft()

                with self.unloading_station.request() as ticket:
                    try:
                        yield ticket
                        ship_arrived.succeed()
                    except simpy.Interrupt:
                        ship_arrived.fail(ShipException())

            else:
                self.idle = True
                print(f"@{self.env.now} - Port waiting for Ships.")
                try:
                    yield self.env.event()
                except simpy.Interrupt:
                    self.idle = False
                    print(f"@{self.env.now} - Ships arrived at Port.")


def generate_ships(env, unloading_station, fueling_station):
    i = 0
    ship_inter_arrival_time = 10  # ! Random Number
    while True:
        yield env.timeout(random.randint(1, ship_inter_arrival_time))
        i += 1
        Ship(env, Port(env, unloading_station,
             fueling_station), name=f"Ship {i}")


def main(time):
    env = simpy.Environment()

    # * Número de estações de descarga
    unloading_station = simpy.Resource(env, 1)
    # * Número de estações de abastecimento
    fueling_station = simpy.Resource(env, 1)

    env.process(generate_ships(env,  unloading_station, fueling_station))
    env.run(until=time)


if __name__ == "__main__":

    time = 5000

    main(time)
