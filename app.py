"""
Frame & Light Photography – Flask Backend (Railway-ready)
"""

import json
import os
import hashlib
import re
from pathlib import Path
from flask import Flask, request, jsonify, send_from_directory, abort, Response

app = Flask(__name__, static_folder=None)

# ------------------------------------------------------------------
# Paths – Railway filesystem is writable
# ------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
CONFIG_FILE = BASE_DIR / "config.json"
HTML_FILE = BASE_DIR / "index.html"

# ------------------------------------------------------------------
# Default configuration
# ------------------------------------------------------------------
DEFAULT_CONFIG = {
    "name": "Frame & Light",
    "h1": "Photographs that keep the day as it felt.",
    "sub": ("Weddings, portraits, events and brand shoots. "
            "Tell us what you are planning and we will reply "
            "with availability and a quote."),
    "cta": "Book a shoot",
    "services": [
        "Wedding", "Pre-wedding", "Engagement", "Birthday / Party",
        "Corporate event", "Portrait / Fashion", "Product / Brand", "Other"
    ],
    "budgets": [
        "Under ₹25,000",
        "₹25,000 – ₹50,000",
        "₹50,000 – ₹1,00,000",
        "₹1,00,000 – ₹2,50,000",
        "Above ₹2,50,000"
    ],
    "sources": [
        "Instagram", "Facebook", "Google search",
        "Friend / Referral", "Previous client", "Other"
    ],
    "wa": "918770644974",
    "accent": "#2F5D62",
    "popup": True,
    "popTitle": "Book your shoot",
    "popSub": "Fill in the details and we will get back to you within a day.",
    "hero": "",
    # SHA-256 of default password "admin123"
    "ph": hashlib.sha256(b"admin123").hexdigest(),
}

# ------------------------------------------------------------------
# Config helpers
# ------------------------------------------------------------------
def load_config() -> dict:
    """Load config.json; fall back to defaults if missing/corrupt."""
    if CONFIG_FILE.exists():
        try:
            with CONFIG_FILE.open("r", encoding="utf-8") as f:
                data = json.load(f)
            return {**DEFAULT_CONFIG, **data}
        except (json.JSONDecodeError, OSError):
            pass
    return dict(DEFAULT_CONFIG)


def save_config(cfg: dict) -> None:
    """Persist config to disk."""
    with CONFIG_FILE.open("w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


# ------------------------------------------------------------------
# HTML rendering – injects config into the page
# ------------------------------------------------------------------
def render_html() -> str:
    if not HTML_FILE.exists():
        abort(500, "index.html not found next to app.py")

    html = HTML_FILE.read_text(encoding="utf-8")
    cfg = load_config()
    cfg_json = json.dumps(cfg, ensure_ascii=False).replace("</", "<\\/")

    pattern = re.compile(
        r'(<script\s+id="cfg"[^>]*>)(.*?)(</script>)',
        re.DOTALL | re.IGNORECASE,
    )
    if pattern.search(html):
        html = pattern.sub(
            lambda m: m.group(1) + cfg_json + m.group(3),
            html,
            count=1,
        )
    else:
        html = html.replace(
            "</body>",
            f'<script id="cfg" type="application/json">{cfg_json}</script>\n</body>'
        )
    return html


# ------------------------------------------------------------------
# Routes
# ------------------------------------------------------------------
@app.route("/")
def index():
    """Public site."""
    return Response(render_html(), mimetype="text/html")


@app.route("/admin")
def admin():
    """Admin panel – same HTML, JS detects /admin path."""
    return Response(render_html(), mimetype="text/html")


@app.route("/api/config", methods=["GET"])
def get_config():
    """Return current config as JSON."""
    return jsonify(load_config())


@app.route("/api/save-config", methods=["POST"])
def save_config_endpoint():
    """Save updated config from admin panel."""
    try:
        new_cfg = request.get_json(force=True, silent=False)
        if not isinstance(new_cfg, dict):
            return jsonify({"error": "Invalid payload"}), 400

        current = load_config()
        if "ph" not in new_cfg or not new_cfg["ph"]:
            new_cfg["ph"] = current.get("ph", DEFAULT_CONFIG["ph"])

        merged = {**DEFAULT_CONFIG, **new_cfg}
        save_config(merged)
        return jsonify({"ok": True, "message": "Config saved"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/verify-password", methods=["POST"])
def verify_password():
    """Optional server-side password check."""
    data = request.get_json(silent=True) or {}
    pw = data.get("password", "")
    cfg = load_config()
    hashed = hashlib.sha256(pw.encode("utf-8")).hexdigest()
    return jsonify({"ok": hashed == cfg.get("ph", "")})


# ------------------------------------------------------------------
# Health check (Railway uses this to verify the app is up)
# ------------------------------------------------------------------
@app.route("/healthz")
def healthz():
    return jsonify({"ok": True}), 200


# ------------------------------------------------------------------
# Static files fallback (LAST so it doesn't shadow /api, /admin)
# ------------------------------------------------------------------
@app.route("/<path:filename>")
def static_files(filename):
    safe_path = (BASE_DIR / filename).resolve()
    if not str(safe_path).startswith(str(BASE_DIR)):
        abort(404)
    if safe_path.is_file():
        return send_from_directory(BASE_DIR, filename)
    abort(404)


# ------------------------------------------------------------------
# Entry point
# ------------------------------------------------------------------
if __name__ == "__main__":
    if not CONFIG_FILE.exists():
        save_config(dict(DEFAULT_CONFIG))
        print(f"[init] Created default {CONFIG_FILE.name}")

    port = int(os.environ.get("PORT", 5000))
    print(f"→ Public site : http://localhost:{port}/")
    print(f"→ Admin panel : http://localhost:{port}/admin")
    print(f"→ Default password: admin123")
    app.run(host="0.0.0.0", port=port)
