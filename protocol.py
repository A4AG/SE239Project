"""Newline-delimited UTF-8 JSON shared by the client and server."""

import json

HOST = "127.0.0.1"
PORT = 5050
MAX_FRAME_BYTES = 16_384
MAX_TEXT_LENGTH = 500


def read_message(stream):
    line = stream.readline(MAX_FRAME_BYTES + 1)
    if not line:
        return None
    if len(line) > MAX_FRAME_BYTES or not line.endswith(b"\n"):
        raise ValueError("Expected a complete JSON message within the size limit.")

    try:
        message = json.loads(line.decode("utf-8"))
    except (ValueError, RecursionError) as error:
        raise ValueError("Expected a UTF-8 JSON message.") from error
    if not isinstance(message, dict) or not isinstance(message.get("type"), str):
        raise ValueError("Expected a JSON object with a message type.")
    return message


def send_message(stream, kind, **fields):
    line = json.dumps({"type": kind, **fields}) + "\n"
    stream.write(line.encode("utf-8"))
    stream.flush()
