#!/usr/bin/env python3
"""
app.py

Flask server for the Voice Vault project.

Single web page (dashboard.html) will handle:
-Admin login/logout
-User registration
-Vault lock/unlock
-Display of secrets when unlocked

"""

import os
import datetime
from flask import (
    Flask,
    request,
    render_template,
    redirect,
    url_for,
    session,
    flash,
    jsonify,
)

import ml_utils
import storage

from config import (
    ADMIN_PASSWORD,
    SECRET_KEY,
    DISTANCE_THRESHOLD,
    DATA_DIR,
    PORT,
    AUDIO_DIR,
)

# Flask setup

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__, template_folder=os.path.join(BASE_DIR, "webpages"))
app.config["SECRET_KEY"] = SECRET_KEY

DATA_DIR = os.path.join(BASE_DIR, "data")
AUDIO_DIR = os.path.join(DATA_DIR, "audio_samples")

os.makedirs(AUDIO_DIR, exist_ok=True)


# Helpers

def get_timestamp_str() -> str:
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# Dashboard User Interface
@app.route("/", methods=["GET", "POST"])
def dashboard():
    is_admin = session.get("is_admin", False)
    enroll_username = None 

    if request.method == "POST":
        action = request.form.get("action")

        # Admin login
        if action == "admin_login":
            password = request.form.get("password", "")
            if password == ADMIN_PASSWORD:
                session["is_admin"] = True
                is_admin = True
                flash("Admin login successful.", "success")
            else:
                flash("Incorrect password.", "danger")

        # Admin logout
        elif action == "admin_logout":
            session.pop("is_admin", None)
            is_admin = False
            flash("Logged out of admin.", "info")

        # Enroll user
        elif action == "enroll_user":
            if not is_admin:
                flash("Admin login required to enroll users.", "warning")
            else:
                username = request.form.get("username", "").strip()
                if not username:
                    flash("Username is required.", "warning")
                else:
                    storage.create_user(username)
                    enroll_username = username
                    flash(f"User '{username}' ready for enrollment. Use the Pi to record samples.", "success")

    # Load state for display

    last_auth = storage.load_last_auth_result()  # or None
    is_unlocked = last_auth is not None and last_auth.get("success", False)
    recognized_user = last_auth.get("user") if last_auth else None
    distance = last_auth.get("distance") if last_auth else None

    # Users list
    users_dict = storage.load_users()
    users = list(users_dict.keys())

    # Secrets
    secrets = storage.load_secrets()
    global_secret = secrets.get("global_message", "No global secret set.")
    user_secret = ""
    if recognized_user:
        user_secret = secrets.get("user_notes", {}).get(recognized_user, "No user-specific secret.")

    # Script they must read for enrollment
    enrollment_script = "This is a test enrollment. Please read the following script: 'My voice is my key, verify me securely.'"

    server_url = request.host_url.rstrip("/") 

    return render_template(
        "dashboard.html",
        is_admin=is_admin,
        enroll_username=enroll_username,
        enrollment_script=enrollment_script,
        server_url=server_url,
        users=users,
        # Vault status
        is_unlocked=is_unlocked,
        recognized_user=recognized_user,
        distance=distance,
        # Secrets
        global_secret=global_secret,
        user_secret=user_secret,
    )


# ===== API ENDPOINTS FOR RASPBERRY PI =====

@app.route("/api/audio/enroll", methods=["POST"])
def api_audio_enroll():
    print("[ENROLL] ===== Enrollment request received =====")
    
    audio_file = request.files.get("audio")
    username = request.form.get("username", "").strip()
    sample_idx = request.form.get("sample_idx", None)
    
    print(f"[ENROLL] Username: {username}")
    print(f"[ENROLL] Sample index: {sample_idx}")
    print(f"[ENROLL] Audio file received: {audio_file is not None}")

    if not audio_file or not username:
        print("[ENROLL] ERROR: Missing audio file or username")
        return jsonify({"status": "error", "message": "Missing audio file or username"}), 400

    # Verify user exists (must be created in dashboard first)
    print("[ENROLL] Checking if user exists...")
    users = storage.load_users()
    print(f"[ENROLL] Loaded users: {list(users.keys())}")
    if username not in users:
        print(f"[ENROLL] ERROR: User '{username}' not found in users list")
        return jsonify({
            "status": "error", 
            "message": f"Username '{username}' is not verified. Please create the user in the admin dashboard first."
        }), 400
    print(f"[ENROLL] User '{username}' verified")

    # Save audio file
    print("[ENROLL] Saving audio file...")
    try:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{username}_enroll_{sample_idx or 'x'}_{timestamp}.wav"
        filepath = os.path.join(AUDIO_DIR, filename)
        print(f"[ENROLL] Saving to: {filepath}")
        audio_file.save(filepath)
        print(f"[ENROLL] Audio file saved successfully")
        print(f"[ENROLL] File exists: {os.path.exists(filepath)}")
        print(f"[ENROLL] File size: {os.path.getsize(filepath) if os.path.exists(filepath) else 'N/A'} bytes")
    except Exception as e:
        print(f"[ENROLL] ERROR: Failed to save audio file: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"status": "error", "message": f"Failed to save audio file: {e}"}), 500

    # Extract features
    print("[ENROLL] Extracting features from audio file...")
    try:
        features = ml_utils.extract_features(filepath)
        print(f"[ENROLL] Features extracted successfully")
        print(f"[ENROLL] Feature shape: {features.shape if hasattr(features, 'shape') else type(features)}")
        print(f"[ENROLL] Feature type: {type(features)}")
    except Exception as e:
        print(f"[ENROLL] ERROR: Feature extraction failed: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"status": "error", "message": f"Feature extraction failed: {str(e)}"}), 500

    # Register sample in storage
    print("[ENROLL] Registering sample in storage...")
    try:
        storage.register_sample(username, filepath, features)
        print(f"[ENROLL] Sample registered successfully")
    except Exception as e:
        print(f"[ENROLL] ERROR: Failed to register sample: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"status": "error", "message": f"Failed to register sample: {str(e)}"}), 500

    # Recompute/update voiceprint for this user
    print("[ENROLL] Recomputing voiceprint...")
    try:
        storage.recompute_voiceprint(username)
        print(f"[ENROLL] Voiceprint recomputed successfully")
    except Exception as e:
        print(f"[ENROLL] ERROR: Failed to recompute voiceprint: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"status": "error", "message": f"Failed to recompute voiceprint: {str(e)}"}), 500

    print(f"[ENROLL] ===== Enrollment completed successfully for '{username}' =====")
    return jsonify({"status": "ok", "message": "Enrollment sample received"}), 200


@app.route("/api/audio/authenticate", methods=["POST"])
def api_audio_authenticate():
    audio_file = request.files.get("audio")

    if not audio_file:
        return jsonify({"success": False, "error": "Missing audio file"}), 400

    # Save audio file
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"auth_{timestamp}.wav"
    filepath = os.path.join(AUDIO_DIR, filename)
    audio_file.save(filepath)

    # Extract features
    try:
        features = ml_utils.extract_features(filepath)
    except Exception as e:
        return jsonify({"success": False, "error": f"Feature extraction failed: {e}"}), 500

    # Load voiceprints
    voiceprints = storage.load_voiceprints() 
    if not voiceprints:
        return jsonify({"success": False, "error": "No enrolled users"}), 400

    # Predict speaker using ML
    best_user, distance = ml_utils.predict_speaker(voiceprints, features)

    # Convert numpy types to native Python types for JSON serialization
    if distance is not None:
        distance = float(distance)
    
    # Decide if there is a match
    success = bool(distance is not None and distance < DISTANCE_THRESHOLD)

    # Save last auth result and log the attempt
    result = {
        "timestamp": get_timestamp_str(),
        "success": bool(success), 
        "user": best_user if success else None,
        "distance": distance, 
        "raw_best_user": best_user,
    }
    storage.save_last_auth_result(result)
    storage.log_attempt(
        timestamp=result["timestamp"],
        recognized_user=best_user,
        distance=result["distance"],
        success=success,
        audio_path=filepath,
    )

    return jsonify(
        {
            "success": success,
            "recognized_user": best_user,
            "distance": result["distance"],
        }
    ), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT, debug=True)

