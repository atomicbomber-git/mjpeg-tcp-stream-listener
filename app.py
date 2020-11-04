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
image_last_update_time = None


def listen_to_updates():
    global image_data, image_last_update_time

    def on_image_update(new_image_data):
        global image_data, image_last_update_time
        image_data = new_image_data
        image_last_update_time = datetime.now()

    TCPStreamImageListener(
        listen_host=os.getenv("LISTEN_HOST", "0.0.0.0"),
        listen_port=int(os.getenv("LISTEN_PORT", "8000")),
        on_image_update=on_image_update
    ).listen()


# stream_thread = threading.Thread(target=listen_to_updates)
# stream_thread.setDaemon(True)
# stream_thread.start()


@app.route('/')
def video_feed():
    return Response(gen_image_frame(), mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/video')
def video_page():
    return render_template("video_page.jinja2")


def to_frame(binary_data):
    return (b'--frame\r\n'
            b'Content-Type: image/jpeg\r\n\r\n' + binary_data + b'\r\n')


from PIL import Image, ImageDraw
import io
import random, string


def gen_image_frame():
    global image_data

    def rand_num():
        return "".join(
            [random.choice(string.digits) for _ in range(0, 20)]
        )

    while True:
        image = Image.new('RGB', (640, 480), color=(0, 0, 0))
        draft = ImageDraw.Draw(image)
        draft.text((24, 24), rand_num(), fill=(255, 255, 255), stroke_width=10)
        image_bytes = io.BytesIO()
        image.save(image_bytes, format='JPEG')

        yield to_frame(image_bytes.getvalue())

waitress.serve(
    app,
    host=os.getenv("SERVE_HOST", "0.0.0.0"),
    port=os.getenv("SERVE_PORT", "9000")
)
