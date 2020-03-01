import threading

from flask import Flask, Response, render_template
from stream.listener import TCPStreamImageListener
from dotenv import load_dotenv
from datetime import datetime
import waitress
import os

SOURCE_DISCONNECTED_IMAGE = "stream_source_disconnected.png"

# Initialize environment variables from ./.env file. Example can be found at ./.env.example
load_dotenv()

app = Flask(__name__)

image_data = open(SOURCE_DISCONNECTED_IMAGE, "rb").read()


def listen_to_updates():
    global image_data

    def on_image_update(new_image_data):
        global image_data
        image_data = new_image_data
        print("Image updated at {}".format(datetime.now()))

    TCPStreamImageListener(
        listen_host=os.getenv("LISTEN_HOST"),
        listen_port=int(os.getenv("LISTEN_PORT")),
        on_image_update=on_image_update
    ).listen()


stream_thread = threading.Thread(target=listen_to_updates)
stream_thread.setDaemon(True)
stream_thread.start()


@app.route('/')
def video_feed():
    return Response(gen_image_frame(), mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/video')
def video_page():
    return render_template("video_page.jinja2")


def to_frame(binary_data):
    return (b'--frame\r\n'
            b'Content-Type: image/jpeg\r\n\r\n' + binary_data + b'\r\n')


def gen_image_frame():
    while True:
        image = image_data
        yield to_frame(image)


waitress.serve(
    app,
    host=os.getenv("SERVE_HOST"),
    port=os.getenv("SERVE_PORT")
)
