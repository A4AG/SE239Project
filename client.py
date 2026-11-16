"""Terminal client for the local Study Chat server."""

import argparse
import getpass
import socket

from protocol import HOST, PORT, read_message, send_message


def request(stream, kind, **fields):
    send_message(stream, kind, **fields)
    reply = read_message(stream)
    if reply is None:
        raise ConnectionError("The server closed the connection.")
    return reply


def choose_action():
    print("\n1. Exchange a message with the server")
    print("2. Register and sign in")
    print("3. Sign in")
    print("4. Exit client")
    choice = input("Choose 1, 2, 3, or 4: ").strip()
    while choice not in ("1", "2", "3", "4"):
        choice = input("Choose 1, 2, 3, or 4: ").strip()
    return choice


def run_session(stream, choice):
    if choice == "1":
        reply = request(stream, "ECHO", text=input("Message: "))
        if reply["type"] == "ECHO_REPLY":
            print(f"Server replied: {reply['text']}")
        else:
            print(reply["detail"])
        return

    username = input("Username: ").strip()
    password = getpass.getpass("Type your test password and press Enter (typing is hidden): ")
    credentials = {"username": username, "password": password}
    if choice == "2":
        reply = request(stream, "REGISTER", **credentials)
        print(reply["detail"])
        if reply["type"] != "OK":
            return

    reply = request(stream, "LOGIN", **credentials)
    print(reply["detail"])
    if reply["type"] == "OK":
        input("Press Enter to disconnect and return to the menu. ")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=PORT, help=f"local port (default {PORT})")
    args = parser.parse_args()

    try:
        while (choice := choose_action()) != "4":
            try:
                with socket.create_connection((HOST, args.port), timeout=5) as connection:
                    print(f"Connected to Study Chat on {HOST}:{args.port}.")
                    with connection.makefile("rwb") as stream:
                        run_session(stream, choice)
                        # Wait for the server to release the session before another sign-in.
                        connection.shutdown(socket.SHUT_WR)
                        stream.read(1)
            except (OSError, ValueError, OverflowError) as error:
                print(f"Connection error: {error}")
    except (EOFError, KeyboardInterrupt):
        print("\nClient closed.")


if __name__ == "__main__":
    main()
