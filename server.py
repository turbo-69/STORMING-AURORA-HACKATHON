import logging
import os
import typing

from flask import Flask
from flask import request


def create_app(handlers: typing.Dict):
    app = Flask("Battlesnake")

    @app.get("/")
    def on_info():
        return handlers["info"]()

    @app.post("/start")
    def on_start():
        game_state = request.get_json()
        handlers["start"](game_state)
        return "ok"

    @app.post("/move")
    def on_move():
        game_state = request.get_json()
        return handlers["move"](game_state)

    @app.post("/end")
    def on_end():
        game_state = request.get_json()
        handlers["end"](game_state)
        return "ok"

    @app.after_request
    def identify_server(response):
        response.headers.set(
            "server", "battlesnake/github/starter-snake-python"
        )
        return response

    return app


def run_server(handlers: typing.Dict):
    app = create_app(handlers)

    host = "0.0.0.0"
    port = int(os.environ.get("PORT", "8000"))

    logging.getLogger("werkzeug").setLevel(logging.ERROR)

    print(f"\nRunning Battlesnake at http://{host}:{port}")
    # threaded=True: the bot may be playing more than one game at a time
    # during heats (the event handbook explicitly warns about this). Flask's
    # dev server defaults to handling one request at a time, which can queue
    # /move requests from concurrent games and risk the 500ms deadline.
    app.run(host=host, port=port, threaded=True)

