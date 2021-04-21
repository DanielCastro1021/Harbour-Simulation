import simpy
import random


class Ship:
    TIME_UNLOADING_CARGO = 5  # ! Random Number
    TIME_REFUEL = 10  # ! Random Number

    def __init__(self, env, unloading_station, fueling_station, name):
        self.env, self.unloading_station, self.fueling_station, self.name = env, unloading_station, fueling_station, name
        self.env.process(self.run_life_cicle())

    def unload_cargo(self):
        yield self.env.timeout(Ship.TIME_UNLOADING_CARGO)

    def refuel(self):
        yield self.env.timeout(Ship.TIME_REFUEL)

    def run_life_cicle(self):
        print(f"@{self.env.now} - {self.name}: Arrived At Port")

        with self.unloading_station.request() as req:
            print(f"@{self.env.now} - {self.name}: Arrived Unloading Station")
            yield req
            print(f"@{self.env.now} - {self.name}: Started Unloading.")
            yield from self.unload_cargo()
            print(f"@{self.env.now} - {self.name}: Finnised Unloading.")

            with self.fueling_station.request() as req:
                print(f"@{self.env.now} - {self.name}: Arrived Fuel Station")
                yield req
                print(f"@{self.env.now} - {self.name}: Started Fueling.")
                yield from self.unload_cargo()
                print(f"@{self.env.now} - {self.name}: Finnised Fueling.")


def generate_ships(env, unloading_station, fueling_station):
    i = 0
    ship_inter_arrival_time = 10  # ! Random Number
    while True:
        yield env.timeout(random.randint(1, ship_inter_arrival_time))
        i += 1
        Ship(env, unloading_station, fueling_station, name=f"Ship {i}")


def main(time):
    env = simpy.Environment()

    # * Número de estações de descarga
    unloading_station = simpy.Resource(env, 2)
    # * Número de estações de abastecimento
    fueling_station = simpy.Resource(env, 1)

    env.process(generate_ships(env,  unloading_station, fueling_station)
                )
    env.run(until=time)


if __name__ == "__main__":

    time = 100

    main(time)
