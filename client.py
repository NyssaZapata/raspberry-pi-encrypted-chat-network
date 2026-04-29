# -----------------------------------------------------------------------------
# Project: Raspberry Pi Encrypted Chat Network
# Attribution: This implementation is based on and inspired by the open-source
#              "Python Garden" encrypted chat project. Portions of the design
#              and architecture were adapted and extended for this system.
# -----------------------------------------------------------------------------

import socket
import threading
from cryptography.fernet import Fernet

def load_key():
    """ Load the shared Fernet encryption key """
    return open("secret.key", "rb").read()

def encrypt_message(message, key):
    """ Encrypt a plaintext message using Fernet """
    return Fernet(key).encrypt(message.encode())

def decrypt_message(message, key):
    """ Decrypt a Fernet-encrypted message """.
    return Fernet(key).decrypt(message).decode()

class Client:
    def __init__(self, host, port=5555):
        self.nickname = input("Enter nickname: ")
        self.key = load_key()

        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client.connect((host, port))

        self.print_lock = threading.Lock()
        self.ready = threading.Event()
        self.typing = False

        # Handshake: Server requests nickname
        first_msg = self.client.recv(4096)
        if first_msg == b"NICK":
            self.client.send(self.nickname.encode('ascii'))

        print("\nConnected to chat.\n")
        print("Menu Options: ")
        print("Type /quit to leave.")
        print("Type /users to view others in the chat.")
        print("Type /whoami to view your Nickname and your IP address.")
        print("Hit enter to bring the prompt back!\n")

        # Start background receive thread
        threading.Thread(target=self.receive, daemon=True).start()

        # Wait for first server message
        self.ready.wait()

        # Main thread handles user input
        self.write_loop()

    def receive(self):
        """ Continuously receive and decrypt messages from the server """
        while True:
            try:
                message = self.client.recv(4096)

                # Ignore empty packets
                if not message:
                    break

                decrypted = decrypt_message(message, self.key)

                with self.print_lock:

                    if self.typing:
                        # move to start and clear line
                        print("\r\033[K", end="")

                    # print incoming message
                    print(decrypted)

                    if self.typing:
                        print(f"[{self.nickname}]: ", end="", flush=True)

                self.ready.set()

            except:
                print("\n[DISCONNECTED] Server has shut down.")
                break

    def write_loop(self):
        """ Main thread: read user input and send encrypted messages """

        while True:
            try:
                self.typing = True
                text = input(f"[{self.nickname}]: ").strip()
                self.typing = False

                # normalize immediately
                text = text.strip()

                # hard block empty input
                if text == "":
                    continue

                # Clean exit command
                if text.lower() == "/quit":
                    try:
                        self.client.close()
                    except:
                        pass
                    print("You have disconnected from the chat.")
                    break

                # command vs normal message
                if text.startswith("/"):
                    msg = text
                else:
                    msg = f"[{self.nickname}]: {text}"

                if not msg.strip():
                    continue

                encrypted = encrypt_message(msg, self.key)
                self.client.send(encrypted)

            except:
                print("[DISCONNECTED] Server has shut down.")
                break

host = input("Enter server ZeroTier IP: ")
Client(host)
