import socket
from typing import Callable, ClassVar
import threading, time

MAX_TOLERATED_EMPTY_MESSAGES = 100
DATA_DELIMITER_SYMBOL = b':::'
MODE_MESSAGE_LEN = 'INTERPRET_MESSAGE_LEN'
MODE_IMAGE = 'INTERPRET_IMAGE'
MODE_SEEK_MARKER = 'INTERPRET_SEEK_MARKER'


class DisconnectedError(Exception):
    pass


class TCPStreamImageListener:
    def __init__(
            self,
            listen_host: str,
            listen_port: int,
            on_image_update: Callable
    ) -> None:

        self.socket = None
        self.connection = None
        self.must_reconnect = True
        self.listen_host = listen_host
        self.listen_port = listen_port

        self.on_image_update: ClassVar[Callable] = on_image_update
        self.current_interpret_mode = MODE_SEEK_MARKER
        self.message_length_digits = b''
        self.image_message_len = -1

        self.message_back_buffer = []

        self.init_socket()

    def init_socket(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.bind((self.listen_host, self.listen_port))
        self.socket.listen()
        self.socket.setblocking(False)

    def eat_message(self, expected_message_length):
        message_buffer = b''
        empty_message_count = 0

        while len(message_buffer) < expected_message_length:
            if len(self.message_back_buffer) > 0:
                message_buffer += self.message_back_buffer.pop()
            else:
                temp = self.connection.recv(1)

                if temp == b'':
                    empty_message_count += 1

                if empty_message_count > MAX_TOLERATED_EMPTY_MESSAGES:
                    raise DisconnectedError()

                message_buffer += temp
        return message_buffer

    def listen(self):
        while True:
            try:
                if self.must_reconnect:
                    self.connection, _ = self.socket.accept()
                    self.must_reconnect = False

                if self.current_interpret_mode == MODE_MESSAGE_LEN:
                    message = self.eat_message(expected_message_length=1)

                    if message.isdigit():
                        self.message_length_digits += message
                    else:
                        self.message_back_buffer.append(message)

                        try:
                            self.image_message_len = int(self.message_length_digits)
                            self.current_interpret_mode = MODE_IMAGE
                        except ValueError:
                            self.current_interpret_mode = MODE_SEEK_MARKER

                        self.message_length_digits = b''
                elif self.current_interpret_mode == MODE_SEEK_MARKER:
                    buffer = b''

                    while len(buffer) < len(DATA_DELIMITER_SYMBOL):
                        buffer += self.eat_message(expected_message_length=1)

                        if buffer == DATA_DELIMITER_SYMBOL:
                            self.current_interpret_mode = MODE_MESSAGE_LEN                        

                elif self.current_interpret_mode == MODE_IMAGE:

                    self.on_image_update(
                        self.eat_message(expected_message_length=self.image_message_len)
                    )

                    self.current_interpret_mode = MODE_SEEK_MARKER
                else:
                    raise Exception("INVALID_STATE, mode {} is unknown.", self.current_interpret_mode)
            except (IOError, DisconnectedError):
                self.must_reconnect = True