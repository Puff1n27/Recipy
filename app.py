from flask import Flask, jsonify, render_template, request
from flask_login import LoginManager
from config import Config
from models import db, User
from routes.expenses import expenses_bp
from routes.auth import auth_bp
from paddleocr import PaddleOCR
from dotenv import load_dotenv
from services.ocr_service import extract_shop, extract_date, extract_total, detect_language
from PIL import Image
import tempfile
import os
import io

load_dotenv()

_ocr_engines = {}

def get_ocr(lang="japan"):
    if lang not in _ocr_engines:
        _ocr_engines[lang] = PaddleOCR(lang=lang, use_angle_cls=True)
    return _ocr_engines[lang]


def run_ocr(engine, image_path):
    result = engine.predict(image_path)
    try:
        return result[0]["rec_texts"]
    except (KeyError, IndexError, TypeError):
        texts = []
        for block in result:
            if isinstance(block, dict):
                texts.extend(block.get("rec_texts", []))
        return texts

app = Flask(__name__)
app.config.from_object(Config)

# ─── DATABASE ─────────────────────────────────────────
db.init_app(app)

# ─── LOGIN MANAGER ────────────────────────────────────
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "auth.login"

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@login_manager.unauthorized_handler
def unauthorized():
    return jsonify({"error": "Login required", "logged_in": False}), 401

# ─── BLUEPRINTS ───────────────────────────────────────
app.register_blueprint(auth_bp,     url_prefix="/api/auth")
app.register_blueprint(expenses_bp, url_prefix="/api/expenses")

# ─── FRONTEND ─────────────────────────────────────────
@app.route("/")
def index():
    return render_template("index.html")

# ─── SCAN ─────────────────────────────────────────────
@app.route("/api/scan", methods=["POST"])
def scan_receipt():
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["file"]

    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    try:
        image_bytes = file.read()
        image = Image.open(io.BytesIO(image_bytes))

        if image.mode != "RGB":
            image = image.convert("RGB")

        max_width = 2000
        if image.width > max_width:
            ratio = max_width / image.width
            new_size = (max_width, int(image.height * ratio))
            image = image.resize(new_size, Image.LANCZOS)

        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as temp:
            image.save(temp.name, "JPEG", quality=95)
            temp_path = temp.name

    except Exception as e:
        return jsonify({"error": f"Image processing failed: {str(e)}"}), 400

    try:
        texts = run_ocr(get_ocr("japan"), temp_path)
        raw_text = "\n".join(texts)
        lang = detect_language(raw_text)

        # Japanese-tuned model also reads Latin text, but a dedicated
        # English model is more accurate once we know it's not Japanese.
        if lang == "en":
            en_texts = run_ocr(get_ocr("en"), temp_path)
            if en_texts:
                texts = en_texts
                raw_text = "\n".join(texts)

        return jsonify({
            "raw_text":     raw_text,
            "lines":        texts,
            "language":     lang,
            "shop_name":    extract_shop(raw_text, lang),
            "date":         extract_date(raw_text, lang),
            "total_amount": extract_total(raw_text, lang)
        })

    except RuntimeError as e:
        return jsonify({"error": "OCR failed", "detail": str(e)}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

# ─── START ────────────────────────────────────────────
with app.app_context():
    db.create_all()
    print("✅ Database ready!")

if __name__ == "__main__":
    app.run(debug=True)