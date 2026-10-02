"""
Frame & Light Photography – Flask Backend
Run: python app.py
Then open: http://localhost:5000  (public site)
           http://localhost:5000/admin  (admin panel)
"""

import json
import os
import hashlib
from pathlib import Path
from flask import Flask, request, jsonify, send_from_directory, abort, Response

app = Flask(__name__, static_folder=None)

# ------------------------------------------------------------------
# Paths & defaults
# ------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
CONFIG_FILE = BASE_DIR / "config.json"
HTML_FILE = BASE_DIR / "index.html"

# Default configuration – mirrors the JSON inside the HTML <script id="cfg">
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
    """Load config.json; if missing/corrupt, fall back to defaults."""
    if CONFIG_FILE.exists():
        try:
            with CONFIG_FILE.open("r", encoding="utf-8") as f:
                data = json.load(f)
            # Merge with defaults so missing keys never break the page
            merged = {**DEFAULT_CONFIG, **data}
            return merged
        except (json.JSONDecodeError, OSError):
            pass
    return dict(DEFAULT_CONFIG)


def save_config(cfg: dict) -> None:
    """Persist config to disk."""
    with CONFIG_FILE.open("w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


# ------------------------------------------------------------------
# HTML rendering – injects current config into the page
# ------------------------------------------------------------------
def render_html() -> str:
    if not HTML_FILE.exists():
        abort(500, "index.html not found next to app.py")

    html = HTML_FILE.read_text(encoding="utf-8")
    cfg = load_config()

    # Safely embed JSON (escape </script> to prevent breaking out)
    cfg_json = json.dumps(cfg, ensure_ascii=False).replace("</", "<\\/")

    # Replace the contents of <script id="cfg" ...>...</script>
    import re
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
        # Fallback: inject before </body>
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
    """Admin panel – serves the same page; JS detects /admin and unlocks UI."""
    return Response(render_html(), mimetype="text/html")


@app.route("/api/config", methods=["GET"])
def get_config():
    """Return current config as JSON (used for debugging / integrations)."""
    return jsonify(load_config())


@app.route("/api/save-config", methods=["POST"])
def save_config_endpoint():
    """
    Save updated config sent from the admin panel.
    Expects JSON body matching the cfg object.
    """
    try:
        new_cfg = request.get_json(force=True, silent=False)
        if not isinstance(new_cfg, dict):
            return jsonify({"error": "Invalid payload"}), 400

        # Basic sanity check – keep password hash if not provided
        current = load_config()
        if "ph" not in new_cfg or not new_cfg["ph"]:
            new_cfg["ph"] = current.get("ph", DEFAULT_CONFIG["ph"])

        # Merge on top of defaults to keep unknown fields consistent
        merged = {**DEFAULT_CONFIG, **new_cfg}
        save_config(merged)

        return jsonify({"ok": True, "message": "Config saved"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/verify-password", methods=["POST"])
def verify_password():
    """
    Optional server-side password check.
    Body: {"password": "..."}
    """
    data = request.get_json(silent=True) or {}
    pw = data.get("password", "")
    cfg = load_config()
    hashed = hashlib.sha256(pw.encode("utf-8")).hexdigest()
    return jsonify({"ok": hashed == cfg.get("ph", "")})


# ------------------------------------------------------------------
# Static files fallback (in case HTML references local assets later)
# ------------------------------------------------------------------
@app.route("/<path:filename>")
def static_files(filename):
    # Only allow safe, non-hidden files from BASE_DIR
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
    # Ensure a config file exists on first run
    if not CONFIG_FILE.exists():
        save_config(dict(DEFAULT_CONFIG))
        print(f"[init] Created default {CONFIG_FILE.name}")

    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "1") == "1"
    print(f"→ Public site : http://localhost:{port}/")
    print(f"→ Admin panel : http://localhost:{port}/admin")
    print(f"→ Default password: admin123  (change it from the admin panel)")
    app.run(host="0.0.0.0", port=port, debug=debug)