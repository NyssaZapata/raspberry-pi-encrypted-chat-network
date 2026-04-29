# -----------------------------------------------------------------------------
# Project: Raspberry Pi Encrypted Chat Network
# Attribution: This implementation is based on and inspired by the open-source
#              "Python Garden" encrypted chat project. Portions of the design
#              and architecture were adapted and extended for this system.
# -----------------------------------------------------------------------------

from cryptography.fernet import Fernet
import os

KEY_FILE = "secret.key"

def load_key():
"""Load the encryption key from a file, or generate one if it doesn't  exist.
         	Returns a Fernet key."""
         	if os.path.exists(KEY_FILE):
    	        	with open(KEY_FILE, "rb") as f:
        	    	key = f.read()
         	else:
    	        	key = Fernet.generate_key()
    	        	with open(KEY_FILE, "wb") as f:
       	           	f.write(key)
         	return key
def encrypt_message(key, message):
"""Encrypt a plaintext message (string) and return encrypted bytes."""
         	f = Fernet(key)
         	return f.encrypt(message.encode())
def decrypt_message(key, token):
"""Decrypt encrypted bytes and return the plaintext string."""
         	f = Fernet(key)
         	return f.decrypt(token).decode()
