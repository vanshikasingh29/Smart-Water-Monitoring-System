from flask import Flask, render_template, request, redirect, url_for, Response
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask import make_response
from datetime import datetime, timedelta
from flask import flash
import json, os, pdfkit
import base64
import io
import matplotlib.pyplot as plt



app = Flask(__name__)
app.secret_key = "supersecretkey"

# ---------------- LOGIN ----------------
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


# ---------------- USERS ----------------
def read_users():
    if not os.path.exists("user.json"):
        return {}
    with open("user.json", "r") as f:
        return json.load(f)


def save_users(users):
    with open("user.json", "w") as f:
        json.dump(users, f, indent=4)


# ---------------- DATA ----------------
def read_data():
    if not os.path.exists("data.json"):
        default = {
            "current": {"ph": 7, "turbidity": 0, "temperature": 25, "risk": "SAFE"},
            "notifications": [],
            "history": []
        }
        with open("data.json", "w") as f:
            json.dump(default, f, indent=4)

    with open("data.json", "r") as f:
        return json.load(f)




# ----------SUPPORT SYSTEM-----------------
def read_support():
    if not os.path.exists("support.json"):
        with open("support.json", "w") as f:
            json.dump({"messages": []}, f, indent=4)
    with open("support.json", "r") as f:
        return json.load(f)


def save_support(data):
    with open("support.json", "w") as f:
        json.dump(data, f, indent=4)

#----------------  NOTIFICATION BADGE ----------------
@app.context_processor
def inject_support_notifications():
    data = read_support()
    new_support = sum(1 for m in data.get("messages", []) if m.get("status") == "new")
    return dict(new_support=new_support)

# ---------------- SYSTEM STATUS ----------------
def get_system_status(data):
    required_keys = ["ph", "turbidity", "temperature"]

    if not data.get("current"):
        return "SYSTEM OFFLINE", False

    for key in required_keys:
        if key not in data["current"] or data["current"][key] is None:
            return "DATA MISSING", False

    return "OPERATIONAL", True


# ---------------- CHART GENERATOR ----------------
def generate_chart_image(data):
    if not data:
        return None, None, None

    labels = [d["time"] for d in data]
    ph = [d["ph"] for d in data]
    turbidity = [d["turbidity"] for d in data]
    temperature = [d["temperature"] for d in data]

    def make_chart(values, title, color):
        plt.figure(figsize=(6,3))
        plt.plot(labels, values, color=color)
        plt.title(title)
        plt.xticks(rotation=45)
        plt.tight_layout()

        img = io.BytesIO()
        plt.savefig(img, format='png')
        plt.close()
        img.seek(0)

        return base64.b64encode(img.getvalue()).decode()

    return (
        make_chart(ph, "pH Levels", "blue"),
        make_chart(temperature, "Temperature", "red"),
        make_chart(turbidity, "Turbidity", "green")
    )
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



@app.route("/support", methods=["GET", "POST"])
@login_required
def support():
    data = read_support()

    if request.method == "POST":
        message = request.form["message"]

        new_msg = {
            "user": current_user.id,
            "message": message,
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "status": "new"
        }

        data["messages"].append(new_msg)
        save_support(data)

        flash("Message sent!")
        return redirect(url_for("support"))

    return render_template(
        "support.html",
        is_admin=current_user.is_admin()
    )


#--------------ADMIN SUPPORT----------------
@app.route("/admin/support")
@login_required
def admin_support():
    if not current_user.is_admin():
        return redirect(url_for("dashboard"))

    data = read_support()

    new_count = sum(1 for m in data["messages"] if m["status"] == "new")

    return render_template(
        "admin_support.html",
        messages=data["messages"],
        new_count=new_count,
        is_admin=True
    )


#--------------MARK AS READ---------------------
@app.route("/admin/mark_read/<int:index>")
@login_required
def mark_read(index):
    if not current_user.is_admin():
        return redirect(url_for("dashboard"))

    data = read_support()


    if 0 <= index < len(data["messages"]):
        data["messages"].pop(index)

    save_support(data)

    return redirect(url_for("admin_support"))


# ---------------- DASHBOARD ----------------
@app.route("/dashboard")
@login_required
def dashboard():
    data = read_data()

    alerts_today = len(data["notifications"])
    users = read_users()
    total_users = len(users)

    status_text, status_ok = get_system_status(data)


    # LOAD SAMPLES
    samples_file = "samples.json"
    if os.path.exists(samples_file):
        with open(samples_file, "r") as f:
            samples = json.load(f).get("samples", [])
    else:
        samples = []

    return render_template(
        "dashboard.html",
        current=data["current"],
        alerts=data["notifications"],
        history=data["history"],
        samples=samples,
        is_admin=current_user.is_admin(),
        username=current_user.id,
        alerts_today=alerts_today,
        total_users=total_users,
        status_text=status_text,
        status_ok=status_ok
    )

# ---------------- VIEW CHARTS ----------------
@app.route("/charts")
@login_required
def charts():
    data = read_data()
    history = data["history"]

  
    if history:
        latest_time = max(datetime.strptime(d["time"], "%Y-%m-%d %H:%M:%S") for d in history)
    else:
        latest_time = datetime.now()

    one_week_ago = latest_time - timedelta(days=7)

    filtered = []
    for item in history:
        try:
            t = datetime.strptime(item["time"], "%Y-%m-%d %H:%M:%S")
            if t >= one_week_ago:
                filtered.append(item)
        except:
            continue

    # LOAD SAMPLES (for sidebar)
    samples_file = "samples.json"
    if os.path.exists(samples_file):
        with open(samples_file, "r") as f:
            samples = json.load(f).get("samples", [])
    else:
        samples = []

    return render_template(
        "charts.html",
        history=filtered,  
        samples=samples,
        is_admin=current_user.is_admin()
    )

# ---------------- MONTHLY CHART PAGE ----------------
@app.route("/monthly-charts")
@login_required
def monthly_charts():
    data = read_data()
    history = data["history"]

    one_month_ago = datetime.now() - timedelta(days=30)
    monthly_data = []

    for item in history:
        time_str = item.get("time")

        if not time_str:
            continue

        try:
            t = datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
        except:
            continue

        if t >= one_month_ago:
            monthly_data.append(item)

    samples_file = "samples.json"
    if os.path.exists(samples_file):
        with open(samples_file, "r") as f:
            samples = json.load(f).get("samples", [])
    else:
        samples = []

    return render_template(
        "monthly_charts.html",
        history=history,
        samples=samples,
        is_admin=current_user.is_admin()
    )


# ---------------- SENSOR CHARTS PAGE ----------------
@app.route("/sensor-charts")
@login_required
def sensor_charts():
    samples_file = "samples.json"

    if os.path.exists(samples_file):
        with open(samples_file, "r") as f:
            samples = json.load(f).get("samples", [])
    else:
        samples = []

    return render_template(
    "sensor_charts.html",
    samples=samples,
    is_admin=current_user.is_admin()
    )


# ---------------- VIEW SAMPLE ----------------
@app.route("/sample/<name>")
@login_required
def view_sample(name):
    samples_file = "samples.json"

    if os.path.exists(samples_file):
        with open(samples_file, "r") as f:
            samples = json.load(f).get("samples", [])
    else:
        samples = []

    sample = next((s for s in samples if s["name"] == name), None)

    if not sample:
        return redirect(url_for("dashboard"))

    return render_template("sample.html", sample=sample, samples=samples)


# ---------------- SAVE SAMPLE ----------------
@app.route("/save_sample")
@login_required
def save_sample():
    data = read_data()
    samples_file = "samples.json"

    if os.path.exists(samples_file):
        with open(samples_file, "r") as f:
            all_samples = json.load(f)
    else:
        all_samples = {"samples": []}

    sample_name = request.args.get("name")

    if not sample_name or sample_name.strip() == "":
        sample_name = f"Sample{len(all_samples['samples']) + 1}"

    if any(s["name"] == sample_name for s in all_samples["samples"]):
        sample_name += f"_{len(all_samples['samples'])+1}"

    new_sample = {
        "name": sample_name,
        "current": data["current"],
        "alerts": data["notifications"],
        "history": data["history"]
    }

    all_samples["samples"].append(new_sample)

    with open(samples_file, "w") as f:
        json.dump(all_samples, f, indent=4)

    return redirect(url_for("view_sample", name=sample_name))


# ---------------- DELETE SAMPLE ----------------
@app.route("/delete_sample/<name>")
@login_required
def delete_sample(name):
    samples_file = "samples.json"

    if os.path.exists(samples_file):
        with open(samples_file, "r") as f:
            all_samples = json.load(f)

        all_samples["samples"] = [
            s for s in all_samples["samples"] if s["name"] != name
        ]

        with open(samples_file, "w") as f:
            json.dump(all_samples, f, indent=4)

    return redirect(url_for("dashboard"))


# ---------------- HISTORY-------------------
@app.route("/history")
@login_required
def history():
    data = read_data()
    history = data.get("history", [])

    # ensure location exists
    for record in history:
        if "location" not in record:
            record["location"] = "Leeds, West Yorkshire"

    # GET FILTER VALUES
    location_filter = request.args.get("location", "").strip()
    risk_filter = request.args.get("risk", "").strip()
    date_filter = request.args.get("date", "").strip()

    # APPLY FILTERS
    filtered = []

    for r in history:
        match = True

        if location_filter and location_filter.lower() not in r["location"].lower():
            match = False

        if risk_filter and risk_filter != r["risk"]:
            match = False

        if date_filter and date_filter not in r["time"]:
            match = False

        if match:
            filtered.append(r)

    return render_template(
        "history.html",
        data=filtered,
        location_filter=location_filter,
        risk_filter=risk_filter,
        date_filter=date_filter
    )

# ---------------- EXPORT CSV ----------------
@app.route("/export_csv")
@login_required
def export_csv():
    data = read_data().get("history", [])

    # CSV HEADER
    output = "Time,Location,pH,Temperature,Turbidity,Risk\n"

    # ADD DATA ROWS
    for r in data:
        output += f"{r.get('time','')},{r.get('location','')},{r.get('ph','')},{r.get('temperature','')},{r.get('turbidity','')},{r.get('risk','')}\n"

    # CREATE RESPONSE
    response = make_response(output)
    response.headers["Content-Disposition"] = "attachment; filename=history.csv"
    response.headers["Content-type"] = "text/csv"

    return response

# ---------------- ADMIN USERS ----------------
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

    
    if username == current_user.id:
        return "You cannot delete your own account", 403

    users = read_users()

    if username in users:
        del users[username]
        save_users(users)

    return redirect(url_for("manage_users"))


@app.route('/admin/toggle_admin/<username>')
@login_required
def toggle_admin(username):
    if not current_user.is_admin():
        return "Unauthorized", 403

    users = read_users()

    if username not in users:
        flash("User not found.")
        return redirect(url_for("manage_users"))

    # Count admins
    admin_count = sum(1 for u in users.values() if u.get("role") == "admin")

    current_role = users[username].get("role")


    if current_role == "admin" and admin_count == 1:
        flash("You cannot remove the last admin. Promote another user first.")
        return redirect(url_for("manage_users"))

    # Toggle role
    if current_role == "admin":
        users[username]["role"] = "user"
        flash(f"{username} is no longer an admin.")
    else:
        users[username]["role"] = "admin"
        flash(f"{username} is now an admin.")

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


# ---------------- DOWNLOAD REPORT ----------------
@app.route("/admin/download_report")
@login_required
def download_report():
    if not current_user.is_admin():
        return redirect(url_for("dashboard"))

    report_type = request.args.get("report_type")

    data = read_data()
    history = data.get("history", [])
    alerts = data.get("notifications", [])

    # LOAD SAMPLES
    samples_file = "samples.json"
    if os.path.exists(samples_file):
        with open(samples_file, "r") as f:
            samples = json.load(f).get("samples", [])
    else:
        samples = []

    
    if history:
        latest_time = max(datetime.strptime(d["time"], "%Y-%m-%d %H:%M:%S") for d in history)
    else:
        latest_time = datetime.now()

    # ---------------- FILTER ----------------
    if report_type == "weekly":
        filtered = [
            d for d in history
            if datetime.strptime(d["time"], "%Y-%m-%d %H:%M:%S") >= latest_time - timedelta(days=7)
        ]
        filename = "weekly_report.pdf"
        title = "📊 Weekly AquaGuard Report"

    elif report_type == "monthly":
        filtered = [
            d for d in history
            if datetime.strptime(d["time"], "%Y-%m-%d %H:%M:%S") >= latest_time - timedelta(days=30)
        ]
        filename = "monthly_report.pdf"
        title = "📊 Monthly AquaGuard Report"

    else:
        return "Invalid report type"

    # ---------------- MAIN CHARTS ----------------
    ph_chart, temp_chart, turb_chart = generate_chart_image(filtered)

    # ---------------- SENSOR CHARTS ----------------
    sensor_ph = sensor_temp = sensor_turb = None

    if samples:
        labels = [s["name"] for s in samples]

        ph_vals = [s["current"]["ph"] for s in samples]
        temp_vals = [s["current"]["temperature"] for s in samples]
        turb_vals = [s["current"]["turbidity"] for s in samples]

        def make_sensor_chart(values, title):
            plt.figure(figsize=(6,3))
            plt.plot(labels, values, marker='o')
            plt.title(title)
            plt.tight_layout()

            img = io.BytesIO()
            plt.savefig(img, format='png')
            plt.close()
            img.seek(0)

            return base64.b64encode(img.getvalue()).decode()

        sensor_ph = make_sensor_chart(ph_vals, "pH Comparison")
        sensor_temp = make_sensor_chart(temp_vals, "Temperature Comparison")
        sensor_turb = make_sensor_chart(turb_vals, "Turbidity Comparison")

    # ---------------- RENDER ----------------
    template = "weekly_report.html" if report_type == "weekly" else "monthly_report.html"

    rendered = render_template(
    template,
    title=title,
    data=filtered,
    alerts=alerts,
    ph_chart=ph_chart,
    temp_chart=temp_chart,
    turb_chart=turb_chart,
    sensor_ph=sensor_ph,
    sensor_temp=sensor_temp,
    sensor_turb=sensor_turb
    )

    config = pdfkit.configuration(
        wkhtmltopdf=r"C:\Users\unkno\.vscode\Smart-Water-Monitoring-System\wkhtmltopdf\bin\wkhtmltopdf.exe"
    )

    pdf = pdfkit.from_string(rendered, False, configuration=config)

    return Response(
        pdf,
        mimetype="application/pdf",
        headers={"Content-Disposition": f"attachment;filename={filename}"}
    )
# ---------------- LOGOUT ----------------
@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))


# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(debug=True)