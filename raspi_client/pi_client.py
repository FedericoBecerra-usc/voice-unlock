#!/usr/bin/env python3
"""
pi_client.py

Raspberry Pi client for Voice Vault.

Features:
-Record audio samples (enrollment & authentication) using audio_utils.py
-Send recorded WAV files to the Flask server running on the laptop

Usage:
Enroll user user with default settings (3 samples)
    python3 pi_client.py enroll username
Authenticate (no username needed, server will decide who it matches)
    python3 pi_client.py auth
"""

import argparse
import os
import sys
import requests

from audio_utils import (
    check_arecord_available,
    record_enrollment_sample,
    record_auth_sample,
)

from config import SERVER_URL, ENROLL_ENDPOINT, AUTH_ENDPOINT

def build_url(server_url: str, endpoint: str) -> str:
    """Safely join base server URL with endpoint path."""
    return server_url.rstrip("/") + endpoint


def send_enrollment_sample(server_url: str, username: str, sample_idx: int, wav_path: str) -> None:
    url = build_url(server_url, ENROLL_ENDPOINT)

    if not os.path.exists(wav_path):
        print(f"[pi_client] ERROR: WAV file not found: {wav_path}")
        return

    print(f"[pi_client] Uploading enrollment sample {sample_idx} for '{username}' to {url}")

    files = {"audio": open(wav_path, "rb")}
    data = {"username": username, "sample_idx": sample_idx}

    try:
        resp = requests.post(url, files=files, data=data, timeout=10)
        resp.raise_for_status()
        print(f"[pi_client] Server response: {resp.status_code} {resp.text}")
    except requests.RequestException as e:
        print(f"[pi_client] ERROR: Failed to send enrollment sample: {e}")


def send_auth_sample(server_url: str, wav_path: str) -> None:
    url = build_url(server_url, AUTH_ENDPOINT)

    if not os.path.exists(wav_path):
        print(f"[pi_client] ERROR: WAV file not found: {wav_path}")
        return

    print(f"[pi_client] Uploading auth sample to {url}")

    files = {"audio": open(wav_path, "rb")}

    try:
        resp = requests.post(url, files=files, timeout=10)
        resp.raise_for_status()
        try:
            data = resp.json()
            print(f"[pi_client] Auth result JSON: {data}")
        except ValueError:
            print(f"[pi_client] Auth result (raw): {resp.text}")
    except requests.RequestException as e:
        print(f"[pi_client] ERROR: Failed to send auth sample: {e}")


def handle_enroll(args: argparse.Namespace) -> None:
    username = args.username
    num_samples = args.num_samples
    server_url = args.server

    print(f"[pi_client] Enrolling user '{username}' with {num_samples} sample(s)")
    print(f"[pi_client] Server URL: {server_url}")

    for sample_idx in range(1, num_samples + 1):
        input(f"\nPress Enter to record sample {sample_idx}/{num_samples} for '{username}'...")
        wav_path = record_enrollment_sample(username=username, sample_idx=sample_idx)

        # Send sample to the server
        send_enrollment_sample(server_url, username, sample_idx, wav_path)

    print(f"\n[pi_client] Enrollment process finished for '{username}'. "
          f"Check the Flask admin UI for updated status.")


def handle_auth(args: argparse.Namespace) -> None:
    server_url = args.server

    print(f"[pi_client] Starting authentication recording")
    print(f"[pi_client] Server URL: {server_url}")
    input("Press Enter to record your authentication sample...")

    wav_path = record_auth_sample()
    send_auth_sample(server_url, wav_path)
    print("[pi_client] Authentication attempt sent. Check the vault page on the server.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Raspberry Pi client for the Voice Vault project"
    )

    parser.add_argument(
        "--server",
        type=str,
        default=SERVER_URL,
        help=f"Base URL of the Flask server (default: {SERVER_URL})"
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # Enroll command
    enroll_parser = subparsers.add_parser(
        "enroll", help="Enroll a new user (or add more samples to an existing user)"
    )
    enroll_parser.add_argument(
        "username",
        type=str,
        help="Username to enroll (e.g. alice)"
    )
    enroll_parser.add_argument(
        "--num-samples",
        type=int,
        default=3,
        help="Number of enrollment samples to record (default: 3)"
    )
    enroll_parser.set_defaults(func=handle_enroll)

    # Authentication command
    auth_parser = subparsers.add_parser(
        "auth", help="Record a sample and send it for authentication"
    )
    auth_parser.set_defaults(func=handle_auth)

    return parser.parse_args()


def main() -> None:
    if not check_arecord_available():
        print("[pi_client] ERROR: `arecord` is not available on this system.")
        print("Install ALSA utils with:")
        print("    sudo apt-get update && sudo apt-get install alsa-utils")
        sys.exit(1)

    args = parse_args()
    args.func(args)


if __name__ == "__main__":
    main()