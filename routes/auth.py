from flask import Blueprint, jsonify, request, session
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user, logout_user, login_required, current_user
from models import db, User

auth_bp = Blueprint("auth", __name__)


# ─── REGISTER ─────────────────────────────────────────
@auth_bp.route("/register", methods=["POST"])
def register():
    data = request.get_json(force=True)

    if not data:
        return jsonify({"error": "No data received"}), 400

    username = data.get("username", "").strip()
    email    = data.get("email", "").strip()
    password = data.get("password", "").strip()

    # Validate fields
    if not username or not email or not password:
        return jsonify({"error": "All fields required"}), 400

    if len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters"}), 400

    # Check if user already exists
    if User.query.filter_by(email=email).first():
        return jsonify({"error": "Email already registered"}), 409

    if User.query.filter_by(username=username).first():
        return jsonify({"error": "Username already taken"}), 409

    # Create new user
    # Hash password — never store plain text!
    hashed_password = generate_password_hash(password)

    user = User(
        username = username,
        email    = email,
        password = hashed_password
    )

    try:
        db.session.add(user)
        db.session.commit()

        # Auto login after register
        login_user(user)

        return jsonify({
            "message": "Account created successfully!",
            "user":    user.to_dict()
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


# ─── LOGIN ────────────────────────────────────────────
@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json(force=True)

    if not data:
        return jsonify({"error": "No data received"}), 400

    email    = data.get("email", "").strip()
    password = data.get("password", "").strip()

    if not email or not password:
        return jsonify({"error": "Email and password required"}), 400

    # Find user by email
    user = User.query.filter_by(email=email).first()

    # Check password
    if not user or not check_password_hash(user.password, password):
        return jsonify({"error": "Invalid email or password"}), 401

    # Login user
    login_user(user, remember=True)

    return jsonify({
        "message": "Login successful!",
        "user":    user.to_dict()
    })


# ─── LOGOUT ───────────────────────────────────────────
@auth_bp.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    return jsonify({"message": "Logged out successfully!"})


# ─── GET CURRENT USER ─────────────────────────────────
@auth_bp.route("/me", methods=["GET"])
@login_required
def get_current_user():
    return jsonify({"user": current_user.to_dict()})


# ─── CHECK AUTH STATUS ────────────────────────────────
@auth_bp.route("/status", methods=["GET"])
def auth_status():
    if current_user.is_authenticated:
        return jsonify({
            "logged_in": True,
            "user": current_user.to_dict()
        })
    return jsonify({"logged_in": False})