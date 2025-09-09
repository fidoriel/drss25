# use with gitlab.hpi.de/osm/eulynx-point-server

from flask import Flask, jsonify, request
from pyLYNX.messages.signal import EulynxSignalParser, EulynxSignalLuminosity
from pyLYNX.pyLYNX import pyLYNX
from pyLYNX.messages._generic import EulynxGeneric
from multiprocessing import Process, Manager
import time
import logging

app = Flask(__name__)
pylynx_process = None
movements = []
in_progress = False


class SBBEulynxSignalAspect:
    # dark = [0xA1, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0x01, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF]
    red = [
        0xA1,
        0xFF,
        0x00,
        0xFF,
        0xFF,
        0xFF,
        0xFF,
        0xFF,
        0xFF,
        0xFF,
        0xFF,
        0xFF,
        0xFF,
        0xFF,
        0xFF,
        0xFF,
        0xFF,
        0xFF,
    ]
    orange = [
        0xA1,
        0xFF,
        0xFF,
        0x00,
        0xFF,
        0xFF,
        0xFF,
        0xFF,
        0xFF,
        0xFF,
        0xFF,
        0xFF,
        0xFF,
        0xFF,
        0xFF,
        0xFF,
        0xFF,
        0xFF,
    ]
    # green_50_limit = [0xA1, 0xFF, 0x05, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF]
    green = [
        0xA1,
        0xFF,
        0xEF,
        0xFF,
        0xFF,
        0xFF,
        0xFF,
        0xFF,
        0xFF,
        0xFF,
        0xFF,
        0xFF,
        0xFF,
        0xFF,
        0xFF,
        0xFF,
        0xFF,
        0xFF,
    ]


class SBBEulynxSignal(EulynxGeneric):
    protocol_type = bytes.fromhex("30")

    @classmethod
    def indicate_signal_aspect(
        cls, sender_id: str, receiver_id: str, signal_aspect: list[int]
    ) -> bytes:
        """
        generate command to indicate a signal aspect

        :param sender_id: Identifier of the sending instance of the command
        :param receiver_id: Identifier of the receiving instance of the command

        returns bytes
        """
        message = cls.protocol_type  # Protocol Type
        message += bytes.fromhex("0100")  # Message Type

        # sender Identifier
        sender_id = sender_id.encode("iso8859-1")
        message += sender_id + ((20 - len(sender_id)) * bytes.fromhex("5f"))

        # receiver Identifier
        receiver = receiver_id.encode("iso8859-1")
        message += receiver + ((20 - len(receiver)) * bytes.fromhex("5f"))

        for i in signal_aspect:
            message += i.to_bytes()
        return message

    @classmethod
    def set_luminosity(
        cls, sender_id: str, receiver_id: str, luminosity: bytes
    ) -> bytes:
        """
        generate command to indicate a signal aspect

        :param sender_id: Identifier of the sending instance of the command
        :param receiver_id: Identifier of the receiving instance of the command

        returns bytes
        """
        message = cls.protocol_type  # Protocol Type
        message += bytes.fromhex("0002")  # Message Type

        # sender Identifier
        sender_id = sender_id.encode("iso8859-1")
        message += sender_id + ((20 - len(sender_id)) * bytes.fromhex("5f"))

        # receiver Identifier
        receiver = receiver_id.encode("iso8859-1")
        message += receiver + ((20 - len(receiver)) * bytes.fromhex("5f"))

        message += luminosity

        return message


class PylynxProcess:
    def __init__(self):
        pass

    def _block_until_message_count(self, _srv, _parser, _target_message_count):
        while _parser.message_counter < _target_message_count:
            _srv.parse_messages()
            time.sleep(1)

    def start_pylynx(self, _movements, _in_progress):
        print("exec start pylynx")
        with pyLYNX("0.0.0.0:50051") as srv1:
            parser = FlexiDugParser()
            srv1.register_default_parser(parser)
            time.sleep(5)
            print("Sending Init Messages")
            srv1.send_message(SBBEulynxSignal.pdi_version_check("DE_IXL01", "LS1"))
            self._block_until_message_count(srv1, parser, 1)
            print("PDI Version Check completed")
            srv1.send_message(SBBEulynxSignal.initialization_request("DE_IXL01", "LS1"))
            self._block_until_message_count(srv1, parser, 4)
            print("Initialization Request completed")

            current_message_count = 4
            while True:
                if len(_movements) > 0:
                    aspect, lum = _movements.pop(0)
                    srv1.send_message(
                        SBBEulynxSignal.indicate_signal_aspect(
                            "DE_IXL01", "LS1", aspect
                        )
                    )
                    srv1.send_message(
                        SBBEulynxSignal.set_luminosity("DE_IXL01", "LS1", lum)
                    )
                    self._block_until_message_count(
                        srv1, parser, current_message_count + 1
                    )
                    current_message_count = current_message_count + 1
                    _in_progress.value = False
                else:
                    time.sleep(0.1)


class FlexiDugParser(EulynxSignalParser):
    def __init__(self):
        self.message_counter = 0

    def parse_message(self, message: bytes) -> bool:
        """
        parse a EULYNX message

        @param message EULYNX message as byte array

        @returns True if the message could be parsed successfully, otherwise False
        """
        logging.warning(message)
        self.message_counter += 1
        return True


def enque_new_status(movement: str):
    print(f"enque {movement}")
    in_progress.value = True
    movements.append(movement)


@app.route("/signal", methods=["GET"])
def turn_left():
    aspect_str = request.args.get("aspect", "red")
    lum_str = request.args.get("luminosity", "day")
    try:
        aspect = getattr(SBBEulynxSignalAspect(), aspect_str)
    except AttributeError:
        return jsonify({"error": f"Signal aspect '{aspect_str}' not found."}), 400
    try:
        lum = getattr(EulynxSignalLuminosity(), lum_str)
    except AttributeError:
        return jsonify({"error": f"Luminosity '{lum_str}' not found."}), 400

    enque_new_status((aspect, lum))
    while in_progress.value:
        time.sleep(0.1)
    return jsonify({"signal_aspect": aspect_str, "luminosity": lum_str})


if __name__ == "__main__":
    manager = Manager()
    movements = manager.list()
    in_progress = manager.Value("in_progress", False)

    pylynx_process = PylynxProcess()
    thread = Process(target=pylynx_process.start_pylynx, args=(movements, in_progress))
    thread.start()
    app.run(debug=True, use_reloader=False)
