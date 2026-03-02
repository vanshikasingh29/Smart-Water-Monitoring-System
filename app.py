from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user
import json

app = Flask(__name__)
app.secret_key = "supersecretkey"

# --- Login Setup ---
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

users = {"admin": {"password": "1234"}}  # simple in-memory users

class User(UserMixin):
    def __init__(self, username):
        self.id = username

@login_manager.user_loader
def load_user(user_id):
    if user_id in users:
        return User(user_id)
    return None

# --- Helper to read data.json ---
def read_data():
    with open("data.json", "r") as f:
        return json.load(f)

# --- Routes ---
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        if username in users and users[username]["password"] == password:
            login_user(User(username))
            return redirect(url_for("dashboard"))
    return render_template("login.html")

@app.route("/dashboard")
@login_required
def dashboard():
    data = read_data()
    return render_template(
        "dashboard.html",
        current=data["current"],
        alerts=data["notifications"],
        history=data["history"]
    )

@app.route("/history")
@login_required
def history():
    data = read_data()
    return render_template("history.html", data=data["history"])

@app.route("/get_notifications")
@login_required
def get_notifications():
    data = read_data()
    return jsonify(data["notifications"])

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)