import socket

from flask import Flask, Response

app = Flask(__name__)

import socket
import threading

MAX_TOLERATED_EMPTY_MESSAGES = 100
DATA_DELIMITER_SYMBOL = b':::'
MODE_MESSAGE_LEN = 'INTERPRET_MESSAGE_LEN'
MODE_IMAGE = 'INTERPRET_IMAGE'
MODE_SEEK_MARKER = 'INTERPRET_SEEK_MARKER'

HOST = "127.0.0.1"
PORT = 9999

socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

socket.bind((HOST, PORT))
socket.listen()
socket.setblocking(False)

current_interpret_mode = MODE_SEEK_MARKER
message_length_digits = b''
image_message_len = -1
back_buffer = []

must_reconnect = True

connection = None


image_data = open("ssd.png", "rb").read()
image_data_lock = threading.Lock()


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

def update_image():
    global connection, must_reconnect, message_length_digits, current_interpret_mode, image_data, image_message_len

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
                image_data = eat_message(connection, image_message_len)
                current_interpret_mode = MODE_SEEK_MARKER
            else:
                raise Exception("INVALID_STATE, mode {} is unknown.", current_interpret_mode)
        except (IOError, DisconnectedError):
            must_reconnect = True

stream_thread = threading.Thread(target=update_image)
stream_thread.daemon = True
stream_thread.start()

@app.route('/')
def video_feed():
    return Response(gen(), mimetype='multipart/x-mixed-replace; boundary=frame')


if __name__ == '__main__':
    app.run()


def to_frame(binary_data):
    return (b'--frame\r\n'
            b'Content-Type: image/jpeg\r\n\r\n' + binary_data + b'\r\n')

def gen():
    while True:
        image = image_data
        yield to_frame(image)