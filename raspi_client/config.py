"""
config.py  (Raspberry Pi side)

Central configuration for the RPi client:
-Server URL of the Flask backend
-API endpoints
-Audio recording parameters (for arecord)
-Local recordings folder
"""

import os

# ==== Server / API settings ====
SERVER_URL = "http://172.20.10.6:5001"

# API endpoints on the Flask server
ENROLL_ENDPOINT = "/api/audio/enroll"
AUTH_ENDPOINT = "/api/audio/authenticate"


# Audio recording settings

ARECORD_DEVICE = "default"

# WAV format
SAMPLE_RATE = 16000        # Hz
CHANNELS = 1               # mono
FORMAT = "S16_LE"          # 16-bit PCM

# Default recording duration (seconds) for each sample
DEFAULT_DURATION = 7

# Local filesystem settings 

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RECORDINGS_DIR = os.path.join(BASE_DIR, "recordings")
os.makedirs(RECORDINGS_DIR, exist_ok=True)