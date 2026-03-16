from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user
import json
import os

app = Flask(__name__)
app.secret_key = "supersecretkey"


# ---------------- LOGIN SETUP ----------------

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"


class User(UserMixin):
    def __init__(self, username):
        self.id = username


@login_manager.user_loader
def load_user(user_id):
    users = read_users()
    if user_id in users:
        return User(user_id)
    return None


# ---------------- USER DATABASE ----------------

def read_users():
    if not os.path.exists("user.json"):
        return {}

    with open("user.json", "r") as f:
        return json.load(f)


def save_users(users):
    with open("user.json", "w") as f:
        json.dump(users, f, indent=4)


# ---------------- SENSOR DATA ----------------

def read_data():
    with open("data.json", "r") as f:
        return json.load(f)


# ---------------- LOGIN PAGE ----------------

@app.route("/", methods=["GET", "POST"])
def login():

    users = read_users()
    error = None

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        if username not in users:
            error = "Username does not exist"

        elif users[username]["password"] != password:
            error = "Incorrect password"

        else:
            login_user(User(username))
            return redirect(url_for("dashboard"))

    return render_template("login.html", error=error)


# ---------------- REGISTER PAGE ----------------

@app.route("/register", methods=["GET", "POST"])
def register():

    users = read_users()

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]
        email = request.form["email"]
        phone = request.form["phone"]

        if username not in users:

            users[username] = {
                "password": password,
                "email": email,
                "phone": phone
            }

            save_users(users)

            return redirect(url_for("login"))

    return render_template("register.html")


# ---------------- DASHBOARD ----------------

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


# ---------------- HISTORY ----------------

@app.route("/history")
@login_required
def history():

    data = read_data()

    return render_template(
        "history.html",
        data=data["history"]
    )


# ---------------- ALERT API ----------------

@app.route("/get_notifications")
@login_required
def get_notifications():

    data = read_data()

    return jsonify(data["notifications"])


# ---------------- LOGOUT ----------------

@app.route("/logout")
@login_required
def logout():

    logout_user()

    return redirect(url_for("login"))


# ---------------- RUN SERVER ----------------

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)