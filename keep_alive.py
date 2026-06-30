"""
سرور Flask سبک برای نگه داشتن سرویس Render در حالت زنده.
این فقط یک endpoint ساده ارائه می‌دهد تا Render سرویس را Web Service تشخیص دهد.
"""
import logging
import threading

from flask import Flask

app = Flask(__name__)
flask_logger = logging.getLogger("werkzeug")
flask_logger.setLevel(logging.WARNING)  # جلوگیری از شلوغ شدن لاگ‌ها


@app.route("/")
def home():
    return "Bot is alive!", 200


@app.route("/health")
def health():
    return {"status": "ok"}, 200


def run():
    app.run(host="0.0.0.0", port=8080)


def keep_alive():
    t = threading.Thread(target=run, daemon=True)
    t.start()
