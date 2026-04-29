# -----------------------------------------------------------------------------
# Project: Raspberry Pi Encrypted Chat Network
# Attribution: This implementation is based on and inspired by the open-source
#              "Python Garden" encrypted chat project. Portions of the design
#              and architecture were adapted and extended for this system.
# -----------------------------------------------------------------------------

import socket
import threading
import time
from cryptography.fernet import Fernet

SERVER_NAME = "SERVER"

def load_key():
    """ Load the shared Fernet encryption key """
    return open("secret.key", "rb").read()

def encrypt_message(message, key):
    """ Encrypt a plaintext message using Fernet """
    return Fernet(key).encrypt(message.encode())

def decrypt_message(message, key):
    """ Decrypt a Fernet-encrypted message """
    return Fernet(key).decrypt(message).decode()

class Server:
    def __init__(self, host="0.0.0.0", port=5555):
        self.host = host
        self.port = port
        self.key = load_key()

        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.bind((self.host, self.port))
        self.server.listen()

        # Allow clean shutdown by timing out accept()
        self.server.settimeout(1)

        self.clients = []
        self.nicknames = []
        self.addresses = []
        self.running = True

        # Lock prevents printing collisions
        self.print_lock = threading.Lock()

        print("[SERVER STARTED]")
        print(f"[LISTENING] Server running on {self.host}:{self.port}\n")
        print("Menu Option: ")
        print("Type /quit to shut down the server.")
        print("Type /users to view everyone and their IP address in the chat.")
        print("Type /whoami to view Self and IP address.")
        print("Hit enter to bring prompt back up!\n")

    def broadcast(self, message, sender=None):
        """Send a plaintext message to all clients (encrypted).
           Sender is excluded so messages are not echoed back."""

        encrypted = encrypt_message(message, self.key)

        for client in self.clients:
            if client != sender:
                try:
                    client.send(encrypted)
                except:
                    pass

    def handle_client(self, client):
        """Handle incoming messages from a single client"""
        while self.running:
            try:
                encrypted_data = client.recv(4096)

                if not encrypted_data:
                    break

                decrypted = decrypt_message(encrypted_data, self.key)

                # command handling
                if decrypted.startswith("/users"):
                    user_list = "\n".join(f" - {name}" for name in self.nicknames)

                    response = (
                        f"[SERVER]: Users Online ({len(self.nicknames)})\n"
                        f"{user_list}"
                    )

                    encrypted_response = encrypt_message(response, self.key)

                    try:
                        client.send(encrypted_response)
                    except:
                        pass

                    continue

                # /whoami command
                if decrypted.startswith("/whoami"):
                    index = self.clients.index(client)
                    nickname = self.nicknames[index]
                    addr = self.addresses[index]

                    response = f"[SERVER]: You are {nickname} ({addr})"

                    client.send(encrypt_message(response, self.key))
                    continue

                # relay message to other clients
                encrypted_out = encrypt_message(decrypted, self.key)

                for c in self.clients:
                    if c != client:
                        try:
                            c.send(encrypted_out)
                        except:
                            pass

                # print once on server
                if not decrypted.startswith(f"[{SERVER_NAME}]"):
                    with self.print_lock:
                        print(f"\r{decrypted}")
                        print(f"\r[{SERVER_NAME}]: ", end="", flush=True)

            except:
                break

        # Handle disconnect
        self.remove_client(client)

    def remove_client(self, client):
        """Remove a client cleanly when they disconnect"""
        if client in self.clients:
            index = self.clients.index(client)
            nickname = self.nicknames[index]

            self.clients.remove(client)
            self.nicknames.pop(index)
            self.addresses.pop(index)

            try:
                client.close()
            except:
                pass

            leave_msg = f"[LEAVE] {nickname}"

            with self.print_lock:
                print(f"\r{leave_msg}")
                print(f"[{SERVER_NAME}]: ", end="", flush=True)

    def write_loop(self):
        """Allow the server operator to send messages."""
        while self.running:
            text = input(f"[{SERVER_NAME}]: ").strip()

            if not text:
                continue

            # server command: list connected users
            if text == "/users":
                with self.print_lock:
                    if self.nicknames:
                        print(f"[SERVER]: Connected users ({len(self.nicknames)}):")
                        for name, addr in zip(self.nicknames, self.addresses):
                            print(f" - {name} ({addr[0]}:{addr[1]})")
                    else:
                        print("[SERVER]: No users connected.")
                continue

            # server command: /whoami
            if text == "/whoami":
                with self.print_lock:
                    print(f"\r[SERVER]: You are {SERVER_NAME} ({self.host}:{self.port})")
                continue

            # server command: /quit
            if text.lower() == "/quit":
                shutdown_msg = "[SERVER]: Server is shutting down."

                with self.print_lock:
                    print(shutdown_msg)

                self.broadcast(shutdown_msg)
                self.shutdown()
                break

            msg = f"[{SERVER_NAME}]: {text}"

            # send only to clients
            encrypted = encrypt_message(msg, self.key)

            for client in self.clients:
                try:
                    client.send(encrypted)
                except:
                    pass

    def shutdown(self):
        """ Cleanly shut down the server and all client connections"""

        self.running = False

        # Close all client sockets
        for client in self.clients:
            try:
                client.shutdown(socket.SHUT_RDWR)
                client.close()
            except:
                pass

        try:
            self.server.close()
        except:
            pass

        print("[SERVER SHUTDOWN] Server stopped cleanly.")

    def receive(self):
        """ Accept new clients and perform nickname handshake"""
        while self.running:
            try:
                client, address = self.server.accept()
            except socket.timeout:
                continue
            except OSError:
                break

            # Request nickname
            client.send(b"NICK")
            nickname = client.recv(4096).decode("ascii")

            self.clients.append(client)
            self.nicknames.append(nickname)
            self.addresses.append(address)

            join_msg = f"[JOIN] {nickname}"

            with self.print_lock:
                print(f"\r{join_msg}\n")
                print(f"[{SERVER_NAME}]: ", end="", flush=True)

            self.broadcast(join_msg)

            # small delay ensures JOIN arrives before user messages
            time.sleep(0.05)

            # Start thread for this client
            thread = threading.Thread(target=self.handle_client, args=(client,))
            thread.start()

# Start the server
if __name__ == "__main__":
    server = Server()
    threading.Thread(target=server.receive, daemon=True).start()
    server.write_loop()
