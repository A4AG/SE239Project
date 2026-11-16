"""Local Study Chat server for the Week 6 and Week 8 milestones."""

import argparse
import hashlib
import hmac
import re
import secrets
import socketserver
import threading

from protocol import HOST, MAX_TEXT_LENGTH, PORT, read_message, send_message


def password_hash(password, salt):
    return hashlib.scrypt(password, salt=salt, n=2**14, r=8, p=1)


class StudyChatServer(socketserver.ThreadingTCPServer):
    daemon_threads = True

    def __init__(self, address):
        self.accounts = {}
        self.active_users = set()
        self.lock = threading.Lock()
        super().__init__(address, ClientHandler)

    def register(self, username, password):
        salt = secrets.token_bytes(16)
        digest = password_hash(password, salt)
        with self.lock:
            if username in self.accounts:
                return "That username is already registered. Choose Sign in."
            self.accounts[username] = (salt, digest)
        return None

    def sign_in(self, username, password):
        with self.lock:
            account = self.accounts.get(username)
        if account is None:
            return "Incorrect username or password."
        salt, digest = account
        if not hmac.compare_digest(password_hash(password, salt), digest):
            return "Incorrect username or password."

        with self.lock:
            if username in self.active_users:
                return "That username is already signed in."
            self.active_users.add(username)
        return None

    def sign_out(self, username):
        with self.lock:
            self.active_users.remove(username)


class ClientHandler(socketserver.StreamRequestHandler):
    def handle(self):
        self.username = None
        try:
            while True:
                request = read_message(self.rfile)
                if request is None:
                    break
                self.handle_request(request)
        except ValueError as error:
            try:
                self.reply("ERROR", str(error))
            except OSError:
                pass
        except OSError:
            pass
        finally:
            if self.username is not None:
                self.server.sign_out(self.username)
                print(f"{self.username} left.", flush=True)

    def reply(self, kind, detail):
        send_message(self.wfile, kind, detail=detail)

    def handle_request(self, request):
        kind = request["type"]
        if kind == "ECHO":
            message = request.get("text")
            if (
                not isinstance(message, str)
                or not message.strip()
                or len(message) > MAX_TEXT_LENGTH
            ):
                self.reply("ERROR", f"Enter a message of 1 to {MAX_TEXT_LENGTH} characters.")
                return
            send_message(self.wfile, "ECHO_REPLY", text=message)
            return

        if kind not in ("REGISTER", "LOGIN"):
            self.reply("ERROR", "Unknown message type.")
            return
        if self.username is not None:
            self.reply("ERROR", "This connection is already signed in.")
            return

        username = request.get("username")
        password = request.get("password")
        if not isinstance(username, str) or not re.fullmatch(
            r"[A-Za-z0-9_]{1,24}", username
        ):
            self.reply("ERROR", "Use 1 to 24 letters, numbers, or underscores for the username.")
            return
        if not isinstance(password, str) or not 1 <= len(password) <= 64:
            self.reply("ERROR", "Use 1 to 64 characters for the password.")
            return
        try:
            password_bytes = password.encode("utf-8")
        except UnicodeEncodeError:
            self.reply("ERROR", "Use a valid UTF-8 password.")
            return

        if kind == "REGISTER":
            error = self.server.register(username, password_bytes)
            if error:
                self.reply("ERROR", error)
            else:
                self.reply("OK", "Account registered.")
            return

        error = self.server.sign_in(username, password_bytes)
        if error:
            self.reply("ERROR", error)
            return
        self.username = username
        print(f"{username} joined.", flush=True)
        self.reply("OK", f"Signed in as {username}. Joined Study Chat.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=PORT, help=f"local port (default {PORT})")
    args = parser.parse_args()

    try:
        with StudyChatServer((HOST, args.port)) as server:
            print(f"Study Chat is listening on {HOST}:{server.server_address[1]}.", flush=True)
            server.serve_forever()
    except KeyboardInterrupt:
        print("\nStudy Chat stopped.")
    except (OSError, OverflowError) as error:
        parser.exit(1, f"Could not start Study Chat: {error}\n")


if __name__ == "__main__":
    main()
