import os
import hashlib

def generate_nodeid():
    return hashlib.sha256(os.urandom(int(256/8))).hexdigest()
