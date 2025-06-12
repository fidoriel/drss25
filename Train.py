import traci
import logging

# copy of the train class from flexidug

class Train(object):
    def __init__(self, train_id: str):
        self.train_id: str = train_id
        self.created_in_sumo: bool = False
        self.last_start_position: str = ""
        self.next_start_position: str = ""
        self.direction: str = "in"
        self.current_route: list[tuple[str, str]] = []

    def is_automatic_train(self):
        return False

    def get_current_sumo_position(self):
        if not self.created_in_sumo:
            logging.error(f"Train {self.train_id} was not created in SUMO!")
        return traci.vehicle.getRoadID(self.train_id)

    def get_current_sumo_route(self):
        if not self.created_in_sumo:
            logging.error(f"Train {self.train_id} was not created in SUMO!")
        return traci.vehicle.getRouteID(self.train_id)

    def set_sumo_route(self, signal_tuple: tuple[str, str]):
        if not self.created_in_sumo:
            logging.error(f"Train {self.train_id} was not created in SUMO!")
        logging.info(
            f"Set next route 'route_{signal_tuple[0]}-{signal_tuple[1]}' for train {self.train_id}"
        )
        traci.vehicle.setRouteID(
            self.train_id, f"route_{signal_tuple[0]}-{signal_tuple[1]}"
        )

    def get_speed(self):
        if not self.created_in_sumo:
            logging.error(f"Train {self.train_id} was not created in SUMO!")
        return traci.vehicle.getSpeed(self.train_id)

    def set_speed(self, speed: float):
        if not self.created_in_sumo:
            logging.error(f"Train {self.train_id} was not created in SUMO!")
        traci.vehicle.slowDown(self.train_id, speed, 8.0)
        traci.vehicle.setMaxSpeed(self.train_id, speed)

    def is_on_last_edge_of_route(self):
        if not self.created_in_sumo:
            logging.error(f"Train {self.train_id} was not created in SUMO!")
        last_edge = traci.route.getEdges(self.get_current_sumo_route())[-1]
        return self.get_current_sumo_position() == last_edge

    def stop_train(self):
        if not self.created_in_sumo:
            logging.error(f"Train {self.train_id} was not created in SUMO!")
        traci.vehicle.slowDown(self.train_id, 0.0, 8.0)
        traci.vehicle.setMaxSpeed(self.train_id, 0.001)

    def is_arrived_at_location(self):
        if self.get_speed() > 0:
            return False

        last_route_id = f"route_{self.current_route[-1][0]}-{self.current_route[-1][1]}"
        last_edge_of_last_route = traci.route.getEdges(last_route_id)[-1]
        return last_edge_of_last_route == self.get_current_sumo_position()
