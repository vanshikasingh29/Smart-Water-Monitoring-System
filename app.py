from flask import Flask, render_template, request, redirect, url_for, Response
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import json, os, pdfkit

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
    if not os.path.exists("user.json"): return {}
    with open("user.json","r") as f: return json.load(f)
def save_users(users):
    with open("user.json","w") as f: json.dump(users,f,indent=4)

# ---------------- DATA ----------------
def read_data():
    if not os.path.exists("data.json"):
        default = {"current":{"ph":7,"turbidity":0,"temperature":25,"risk":"SAFE"},"notifications":[],"history":[]}
        with open("data.json","w") as f: json.dump(default,f,indent=4)
    with open("data.json","r") as f: return json.load(f)

# ---------------- LOGIN/REGISTER ----------------
@app.route("/", methods=["GET","POST"])
def login():
    users = read_users(); error=None
    if request.method=="POST":
        username = request.form["username"]; password=request.form["password"]
        if username not in users: error="Username does not exist"
        elif users[username]["password"] != password: error="Incorrect password"
        else: login_user(User(username, users[username].get("role","user"))); return redirect(url_for("dashboard"))
    return render_template("login.html", error=error)

@app.route("/register", methods=["GET","POST"])
def register():
    users = read_users()
    if request.method=="POST":
        username=request.form["username"]; password=request.form["password"]
        email=request.form["email"]; phone=request.form["phone"]
        if username not in users:
            users[username] = {"password":password,"email":email,"phone":phone,"role":"user"}
            save_users(users); return redirect(url_for("login"))
    return render_template("register.html")

# ---------------- DASHBOARD ----------------
@app.route("/dashboard")
@login_required
def dashboard():
    data = read_data(); alerts_today=len(data["notifications"])
    # Load samples for dropdown
    samples_file = "samples.json"
    if os.path.exists(samples_file):
        with open(samples_file,"r") as f: samples=json.load(f).get("samples",[])
    else: samples=[]
    return render_template("dashboard.html",
        current=data["current"],
        alerts=data["notifications"],
        history=data["history"],
        is_admin=current_user.is_admin(),
        username=current_user.id,
        alerts_today=alerts_today,
        samples=samples
    )

# ---------------- VIEW SAMPLE ----------------
@app.route("/sample/<name>")
@login_required
def view_sample(name):
    samples_file="samples.json"
    if os.path.exists(samples_file):
        with open(samples_file,"r") as f: samples=json.load(f).get("samples",[])
    else: samples=[]
    sample=next((s for s in samples if s["name"]==name), None)
    if not sample: return redirect(url_for("dashboard"))
    return render_template("sample.html", sample=sample, samples=samples)

# ---------------- SAVE SAMPLE ----------------
@app.route("/save_sample")
@login_required
def save_sample():
    data = read_data()
    samples_file = "samples.json"
    if os.path.exists(samples_file):
        with open(samples_file,"r") as f:
            all_samples = json.load(f)
    else:
        all_samples = {"samples":[]}

    # Get the name from query parameters
    sample_name = request.args.get("name")
    if not sample_name or sample_name.strip() == "":
        existing = len(all_samples["samples"])
        sample_name = f"Sample{existing+1}"  # fallback automatic name

    # Prevent duplicate names
    if any(s["name"] == sample_name for s in all_samples["samples"]):
        sample_name += f"_{len(all_samples['samples'])+1}"

    new_sample = {
        "name": sample_name,
        "current": data["current"],
        "alerts": data["notifications"],
        "history": data["history"]
    }
    all_samples["samples"].append(new_sample)

    with open(samples_file,"w") as f:
        json.dump(all_samples, f, indent=4)

    return redirect(url_for("view_sample", name=sample_name))

# ---------------- DELETE SAMPLE ----------------
@app.route("/delete_sample/<name>")
@login_required
def delete_sample(name):
    samples_file="samples.json"
    if os.path.exists(samples_file):
        with open(samples_file,"r") as f: all_samples=json.load(f)
        all_samples["samples"]=[s for s in all_samples["samples"] if s["name"]!=name]
        with open(samples_file,"w") as f: json.dump(all_samples,f,indent=4)
    return redirect(url_for("dashboard"))

# ---------------- HISTORY/ADMIN ----------------
@app.route("/history")
@login_required
def history(): return render_template("history.html", data=read_data()["history"])

@app.route("/admin/users")
@login_required
def manage_users():
    if not current_user.is_admin(): return redirect(url_for("dashboard"))
    users=read_users(); return render_template("manage_users.html", users=users)

@app.route("/admin/delete_user/<username>")
@login_required
def delete_user(username):
    if not current_user.is_admin(): return redirect(url_for("dashboard"))
    users=read_users()
    if username in users: del users[username]; save_users(users)
    return redirect(url_for("manage_users"))

@app.route("/admin/delete_alert/<int:index>")
@login_required
def delete_alert(index):
    if not current_user.is_admin(): return redirect(url_for("dashboard"))
    data=read_data()
    if 0<=index<len(data["notifications"]): data["notifications"].pop(index)
    with open("data.json","w") as f: json.dump(data,f,indent=4)
    return redirect(url_for("dashboard"))

@app.route("/admin/download_report")
@login_required
def download_report():
    if not current_user.is_admin(): return redirect(url_for("dashboard"))
    data=read_data(); rendered=render_template("report.html", history=data["history"])
    config=pdfkit.configuration(wkhtmltopdf=r"C:\Users\unkno\.vscode\Smart-Water-Monitoring-System\wkhtmltopdf\bin\wkhtmltopdf.exe")
    pdf=pdfkit.from_string(rendered,False,configuration=config)
    return Response(pdf,mimetype="application/pdf",headers={"Content-Disposition":"attachment;filename=water_report.pdf"})

@app.route("/logout")
@login_required
def logout(): logout_user(); return redirect(url_for("login"))

if __name__=="__main__": app.run(debug=True)