"""
config.py  (Laptop / Flask server side)

Central configuration for the Voice Vault backend.

"""

import os

# Admin credentials.
ADMIN_PASSWORD = "admin123"
SECRET_KEY = "6112"

# Server configuration.
PORT = int(os.getenv("PORT", 5001)) 

# Threshold on distance between sample feature vector and stored voiceprint.
DISTANCE_THRESHOLD = 0.01

# Directories
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
AUDIO_DIR = os.path.join(DATA_DIR, "audio_samples")
SECRETS_DIR = os.path.join(BASE_DIR, "secrets")

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(AUDIO_DIR, exist_ok=True)
os.makedirs(SECRETS_DIR, exist_ok=True)

# Paths for JSON files (used by storage.py)
USERS_JSON = os.path.join(DATA_DIR, "users.json")
VOICEPRINTS_JSON = os.path.join(DATA_DIR, "voiceprints.json")
LAST_AUTH_JSON = os.path.join(DATA_DIR, "last_auth.json")
ATTEMPTS_JSON = os.path.join(DATA_DIR, "attempts.json")
SECRETS_JSON = os.path.join(SECRETS_DIR, "secrets.json")


# ML extraction parameters
SAMPLE_RATE = 16000  
N_MFCC = 13
N_FFT = 512
HOP_LENGTH = 160      
N_MELS = 40