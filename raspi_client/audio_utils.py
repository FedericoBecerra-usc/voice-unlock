"""
audio_utils.py

Helper functions for recording the audio recordings on the RPi
using arecord.

Design:
-16 kHz
-mono
-16-bit PCM (S16_LE)

Set up for MFCC extraction with librosa on the server side.
"""

import os
import subprocess
import datetime
from typing import Optional

from config import (
    ARECORD_DEVICE,
    SAMPLE_RATE,
    CHANNELS,
    FORMAT,
    DEFAULT_DURATION,
    RECORDINGS_DIR,
)


ARECORD_CMD = "arecord"


# Helper functions

def _ensure_dir(path: str) -> None:
    """Create directory if it doesn't exist."""
    os.makedirs(path, exist_ok=True)


def _build_enrollment_filename(username: str, sample_idx: int, out_dir: str) -> str:
    """Construct a filename for an enrollment sample."""
    _ensure_dir(out_dir)
    return os.path.join(out_dir, f"{username}_enroll_{sample_idx}.wav")


def _build_auth_filename(out_dir: str) -> str:
    """Construct a filename for an auth sample with timestamp."""
    _ensure_dir(out_dir)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    return os.path.join(out_dir, f"auth_{timestamp}.wav")


def _run_arecord(output_path: str, duration: int) -> None:
    """
    Call `arecord` to record audio.
    Raises subprocess.CalledProcessError if arecord fails.
    """
    cmd = [
        ARECORD_CMD,
        "-D", ARECORD_DEVICE,     # ALSA device
        "-f", FORMAT,             # sample format
        "-r", str(SAMPLE_RATE),   # sample rate
        "-c", str(CHANNELS),      # channels
        "-d", str(duration),      # duration in seconds
        output_path
    ]

    print(f"[audio_utils] Running: {' '.join(cmd)}")
    subprocess.run(cmd, check=True)
    print(f"[audio_utils] Saved recording to {output_path}")


# Public API

def check_arecord_available() -> bool:
    """Check if the arecord command is available on the system."""
    try:
        subprocess.run(
            [ARECORD_CMD, "--version"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True
        )
        return True
    except (FileNotFoundError, subprocess.CalledProcessError):
        return False


def set_device(device_name: str) -> None:
    """Set the ALSA device to use for recording."""
    global ARECORD_DEVICE
    ARECORD_DEVICE = device_name
    print(f"[audio_utils] Recording device set to: {ARECORD_DEVICE}")


def record_enrollment_sample(
    username: str,
    sample_idx: int,
    out_dir: str = "recordings",
    duration: Optional[int] = None
) -> str:
    """
    Record a single enrollment sample for a given user.

    """
    if duration is None:
        duration = DEFAULT_DURATION

    output_path = _build_enrollment_filename(username, sample_idx, out_dir)

    print(f"[audio_utils] Enrollment recording for '{username}', sample {sample_idx}")
    print(f"[audio_utils] Duration: {duration}s, Output: {output_path}")

    _run_arecord(output_path, duration)
    return output_path


def record_auth_sample(
    out_dir: str = "recordings",
    duration: Optional[int] = None
) -> str:
    """
    Record a single authentication sample.

    """
    if duration is None:
        duration = DEFAULT_DURATION

    output_path = _build_auth_filename(out_dir)

    print(f"[audio_utils] Authentication recording")
    print(f"[audio_utils] Duration: {duration}s, Output: {output_path}")

    _run_arecord(output_path, duration)
    return output_path


if __name__ == "__main__":
    if not check_arecord_available():
        print("[audio_utils] ERROR: `arecord` is not available. Install ALSA utils:")
        print("    sudo apt-get update && sudo apt-get install alsa-utils")
    else:
        print("[audio_utils] `arecord` found. Recording a test auth sample...")
        record_auth_sample()
