from flask import Flask, render_template, request, redirect, url_for, Response
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import json
import os
import pdfkit

app = Flask(__name__)
app.secret_key = "supersecretkey"

# ---------------- LOGIN SETUP ----------------
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

class User(UserMixin):
    def __init__(self, username, role):
        self.id = username
        self.role = role

    def is_admin(self):
        return self.role == "admin"

@login_manager.user_loader
def load_user(user_id):
    users = read_users()
    if user_id in users:
        return User(user_id, users[user_id].get("role", "user"))
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

# ---------------- LOGIN ----------------
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
            login_user(User(username, users[username].get("role", "user")))
            return redirect(url_for("dashboard"))

    return render_template("login.html", error=error)

# ---------------- REGISTER ----------------
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
                "phone": phone,
                "role": "user"
            }
            save_users(users)
            return redirect(url_for("login"))

    return render_template("register.html")

# ---------------- DASHBOARD ----------------
@app.route("/dashboard")
@login_required
def dashboard():
    data = read_data()
    alerts_today = len(data["notifications"])

    return render_template(
        "dashboard.html",
        current=data["current"],
        alerts=data["notifications"],
        history=data["history"],
        is_admin=current_user.is_admin(),
        username=current_user.id,
        alerts_today=alerts_today
    )

# ---------------- USER MANAGEMENT ----------------
@app.route("/admin/users")
@login_required
def manage_users():
    if not current_user.is_admin():
        return redirect(url_for("dashboard"))
    users = read_users()
    return render_template("manage_users.html", users=users)

@app.route("/admin/delete_user/<username>")
@login_required
def delete_user(username):
    if not current_user.is_admin():
        return redirect(url_for("dashboard"))
    users = read_users()
    if username in users:
        del users[username]
        save_users(users)
    return redirect(url_for("manage_users"))

# ---------------- DELETE ALERT ----------------
@app.route("/admin/delete_alert/<int:index>")
@login_required
def delete_alert(index):
    if not current_user.is_admin():
        return redirect(url_for("dashboard"))
    data = read_data()
    if 0 <= index < len(data["notifications"]):
        data["notifications"].pop(index)
    with open("data.json", "w") as f:
        json.dump(data, f, indent=4)
    return redirect(url_for("dashboard"))

# ---------------- DOWNLOAD REPORT AS PDF ----------------
@app.route("/admin/download_report")
@login_required
def download_report():
    if not current_user.is_admin():
        return redirect(url_for("dashboard"))

    data = read_data()
    rendered = render_template("report.html", history=data["history"])

    # Adjust the path to wkhtmltopdf for your system
    config = pdfkit.configuration(
        wkhtmltopdf=r"C:\Users\unkno\.vscode\Smart-Water-Monitoring-System\wkhtmltopdf\bin\wkhtmltopdf.exe"
    )

    pdf = pdfkit.from_string(rendered, False, configuration=config)

    return Response(
        pdf,
        mimetype="application/pdf",
        headers={"Content-Disposition": "attachment;filename=water_report.pdf"}
    )

# ---------------- HISTORY ----------------
@app.route("/history")
@login_required
def history():
    data = read_data()
    return render_template("history.html", data=data["history"])

# ---------------- LOGOUT ----------------
@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))

# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(debug=True)