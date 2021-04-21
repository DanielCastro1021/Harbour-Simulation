import simpy
import random
from collections import deque


class ShipException(Exception):
    pass


class Ship:
    TIME_UNLOADING_CARGO = random.randint(1, 5)  # ! Random Number
    TIME_REFUEL = random.randint(1, 10)  # ! Random Number

    def __init__(self, env, port, name):
        self.env, self.port, self.name = env, port, name
        self.env.process(self.run_life_cicle())

    def unload_cargo(self):
        yield self.env.timeout(Ship.TIME_UNLOADING_CARGO)

    def refuel(self):
        yield self.env.timeout(Ship.TIME_REFUEL)

    def run_life_cicle(self):
        print(f"@{self.env.now} - {self.name}: Arrived at port.")
        dock = self.env.event()
        self.port.unloading_service_line.append(dock)

        if self.port.idle:
            self.port.process.interrupt()

        try:
            print(f"@{self.env.now} - Ship is waiting for an unloading dock.")
            yield dock

            with self.port.unloading_station.request() as dock:
                print(
                    f"@{self.env.now} - {self.name}: Arrived at unloading station dock.")
                yield dock
                print(f"@{self.env.now} - {self.name}: Started unloading.")
                yield from self.unload_cargo()
                print(f"@{self.env.now} - {self.name}: Finnised unloading.")

                with self.port.fueling_station.request() as dock:
                    print(
                        f"@{self.env.now} - {self.name}: Arrived at fuel station dock.")
                    yield dock
                    print(f"@{self.env.now} - {self.name}: Started fueling.")
                    yield from self.unload_cargo()
                    print(f"@{self.env.now} - {self.name}: Finnised fueling.")
        except ShipException:
            print(f"@{self.env.now} - Ship cannot get an unloading dock.")


class Port:
    def __init__(self, env, unloading_station, fueling_station):
        self.env, self.unloading_station, self.fueling_station = env, unloading_station, fueling_station
        self.idle = False
        self.unloading_service_line = deque()
        self.fueling_service_line = deque()  # !!! Implementar com a queue para descarga
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
    ship_inter_arrival_time = 10  # ! Random Number
    while True:
        yield env.timeout(random.randint(0, ship_inter_arrival_time))
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

    time = 100

    main(time)
