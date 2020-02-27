import socket
import threading

MAX_TOLERATED_EMPTY_MESSAGES = 100
DATA_DELIMITER_SYMBOL = b':::'
MODE_MESSAGE_LEN = 'INTERPRET_MESSAGE_LEN'
MODE_IMAGE = 'INTERPRET_IMAGE'
MODE_SEEK_MARKER = 'INTERPRET_SEEK_MARKER'

HOST = "127.0.0.1"
PORT = 9999
connection = None

socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

socket.bind((HOST, PORT))
socket.listen()
socket.setblocking(False)

current_interpret_mode = MODE_SEEK_MARKER
message_length_digits = b''
image_message_len = -1
back_buffer = []

must_reconnect = True


class DisconnectedError(Exception):
    pass


def eat_message(connection, expected_message_length):
    global must_reconnect

    message_buffer = b''
    empty_message_count = 0

    while len(message_buffer) < expected_message_length:
        if len(back_buffer) > 0:
            message_buffer += back_buffer.pop()
        else:
            temp = connection.recv(1)

            if temp == b'':
                empty_message_count += 1

            if empty_message_count > MAX_TOLERATED_EMPTY_MESSAGES:
                raise DisconnectedError()

            message_buffer += temp

    return message_buffer


def listen_to_stream():
    global connection, must_reconnect, message_length_digits, current_interpret_mode

    while True:
        try:
            if must_reconnect:
                connection, address = socket.accept()
                must_reconnect = False

            if current_interpret_mode == MODE_MESSAGE_LEN:
                message = eat_message(connection, 1)

                if message.isdigit():
                    message_length_digits += message
                else:
                    back_buffer.append(message)

                    try:
                        image_message_len = int(message_length_digits)
                        current_interpret_mode = MODE_IMAGE
                    except ValueError:
                        current_interpret_mode = MODE_SEEK_MARKER

                    message_length_digits = b''
            elif current_interpret_mode == MODE_SEEK_MARKER:
                buffer = b''

                while len(buffer) < len(DATA_DELIMITER_SYMBOL):
                    buffer += eat_message(connection, 1)

                if buffer == DATA_DELIMITER_SYMBOL:
                    current_interpret_mode = MODE_MESSAGE_LEN

            elif current_interpret_mode == MODE_IMAGE:
                image_message = eat_message(connection, image_message_len)

                print("IMAGE DETECTED")

                current_interpret_mode = MODE_SEEK_MARKER
            else:
                raise Exception("INVALID_STATE, mode {} is unknown.", current_interpret_mode)
        except (IOError, DisconnectedError):
            must_reconnect = True

stream_thread = threading.Thread(target=listen_to_stream)
stream_thread.start()