#!/usr/bin/env python3
"""
ml_utils.py

Features:
-Load WAV audio file
-Extract MFCC-based speaker features
-Predict speaker using cosine distance to enrolled voiceprints
"""

import os
from typing import Dict, Tuple, Optional

import numpy as np
import librosa

from config import SAMPLE_RATE, N_MFCC, N_FFT, HOP_LENGTH, N_MELS


# Feature extraction

def _apply_vad(y: np.ndarray, top_db_trim: float = 25.0, top_db_split: float = 30.0) -> np.ndarray:
    """
    Apply voice activity detection (VAD) to remove silence
    and low-energy regions.

    """
    # Trim leading/trailing silence
    y_trimmed, _ = librosa.effects.trim(y, top_db=top_db_trim)

    # If everything got trimmed, fall back to original
    if y_trimmed.size == 0:
        y_trimmed = y

    # Split into non-silent intervals
    intervals = librosa.effects.split(y_trimmed, top_db=top_db_split)

    # If no intervals found, fall back to trimmed signal
    if len(intervals) == 0:
        return y_trimmed

    # Concatenate non-silent segments
    voiced = [y_trimmed[start:end] for start, end in intervals]
    y_voiced = np.concatenate(voiced)

    # Safety: if something went wrong, fall back to trimmed signal
    if y_voiced.size == 0:
        return y_trimmed

    return y_voiced


def extract_features(filepath: str) -> np.ndarray:
    """
    Load a WAV file and return a compact, robust feature vector for speaker recognition.

    Steps:
    -Load audio (mono, 16 kHz)
    -Apply simple VAD to remove silence/low-energy segments
    -Compute MFCCs
    -Drop c0 and keep c1..c(N_MFCC-1)
    -Compute mean and std over time for each coefficient
    -Concatenate into a fixed-length embedding
    -L2-normalize embedding ( for cosine distance)

    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Audio file not found: {filepath}")

    # Load audio as mono, resample to SAMPLE_RATE
    y, sr = librosa.load(filepath, sr=SAMPLE_RATE, mono=True)

    if y.size == 0:
        raise ValueError("Empty audio signal.")

    # Apply simple VAD to remove silence
    y_voiced = _apply_vad(y)

    # After VAD, make sure we still have enough audio
    if y_voiced.size < 0.5 * SAMPLE_RATE:
        raise ValueError("Less than 0.5s of voiced speech.")

    # Compute MFCCs on voiced signal
    mfcc = librosa.feature.mfcc(
        y=y_voiced,
        sr=sr,
        n_mfcc=N_MFCC,
        n_fft=N_FFT,
        hop_length=HOP_LENGTH,
        n_mels=N_MELS,
    )  

    # Drop c0 (row 0) and keep c1..c(N_MFCC-1)
    if mfcc.shape[0] < 2:
        raise ValueError("Not enough MFCC coefficients computed.")
    mfcc_no_c0 = mfcc[1:, :] 

    # Compute statistics over time: mean and std for each coefficient
    mfcc_mean = np.mean(mfcc_no_c0, axis=1)
    mfcc_std = np.std(mfcc_no_c0, axis=1)

    # Concatenate into a single feature vector
    feature_vector = np.concatenate([mfcc_mean, mfcc_std], axis=0)  # dimension will be 2*(N_MFCC-1)

    # L2-normalize to get an embedding suitable for cosine distance
    norm = np.linalg.norm(feature_vector)
    if norm > 1e-10:
        feature_vector = feature_vector / norm

    return feature_vector


# Distance and predition   

def _cosine_distance(a: np.ndarray, b: np.ndarray) -> float:
    """
    Compute cosine distance between two vectors:
    distance = 1 - cosine_similarity.

    """
    dot = float(np.dot(a, b))
    norm_a = float(np.linalg.norm(a))
    norm_b = float(np.linalg.norm(b))

    if norm_a == 0.0 or norm_b == 0.0:
        # Maximum distance if one vector is zero
        return 2.0

    cosine_sim = dot / (norm_a * norm_b)
    return float(1.0 - cosine_sim)


def predict_speaker(
    voiceprints: Dict[str, np.ndarray],
    sample_feature: np.ndarray,
) -> Tuple[Optional[str], Optional[float]]:
    """
    Given stored voiceprints and a sample feature vector, find the closest speaker
    using cosine distance.

    :param voiceprints: dict: username -> np.ndarray (voiceprint embedding)
    :param sample_feature: np.ndarray of shape (D,)
    :return: (best_user, distance) or (None, None) if voiceprints is empty
    """
    if not voiceprints:
        return None, None

    best_user: Optional[str] = None
    best_distance: Optional[float] = None

    # Ensure sample is L2-normalized (just in case)
    sample_norm = np.linalg.norm(sample_feature)
    if sample_norm > 1e-10:
        sample_feature = sample_feature / sample_norm

    for username, vp in voiceprints.items():
        # Ensure same dimensionality
        if vp.shape != sample_feature.shape:
            # Skip mismatched dims (e.g. after changing feature extractor)
            continue

        # L2-normalize stored voiceprint as well (if not already)
        vp_norm = np.linalg.norm(vp)
        if vp_norm > 1e-10:
            vp_normed = vp / vp_norm
        else:
            vp_normed = vp

        dist = _cosine_distance(sample_feature, vp_normed)

        if best_distance is None or dist < best_distance:
            best_distance = dist
            best_user = username

    if best_user is None:
        return None, None

    return best_user, best_distance
