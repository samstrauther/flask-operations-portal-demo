from flask import Flask, request, redirect, url_for, session, render_template_string, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

app = Flask(__name__)
app.config["SECRET_KEY"] = "demo-secret-key-change-this"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///demo_portal.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)


# ----------------------------
# Database Models
# ----------------------------
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # admin or user

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Issue(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(50), default="Submitted")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    submitted_by = db.Column(db.String(80), nullable=False)


# ----------------------------
# Helper
# ----------------------------
def seed_demo_data():
    if not User.query.filter_by(username="admin").first():
        admin = User(username="admin", role="admin")
        admin.set_password("admin123")
        db.session.add(admin)

    if not User.query.filter_by(username="user1").first():
        user = User(username="user1", role="user")
        user.set_password("user123")
        db.session.add(user)

    db.session.commit()


def login_required():
    return "user_id" in session


def admin_required():
    return session.get("role") == "admin"


# ----------------------------
# Base HTML
# ----------------------------
BASE_HTML = """
<!doctype html>
<html>
<head>
    <title>{{ title }}</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 900px;
            margin: 40px auto;
            padding: 0 20px;
            background: #f7f7f7;
            color: #222;
        }
        .card {
            background: white;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        }
        input, textarea, select, button {
            width: 100%;
            padding: 10px;
            margin-top: 8px;
            margin-bottom: 15px;
            border: 1px solid #ccc;
            border-radius: 6px;
        }
        button {
            background: #333;
            color: white;
            cursor: pointer;
        }
        button:hover {
            background: #111;
        }
        a {
            color: #333;
            text-decoration: none;
            margin-right: 12px;
        }
        .nav {
            margin-bottom: 20px;
        }
        .flash {
            padding: 10px;
            background: #eef3ff;
            border: 1px solid #cfdcff;
            border-radius: 6px;
            margin-bottom: 15px;
        }
        .small {
            color: #666;
            font-size: 0.9rem;
        }
        .status {
            font-weight: bold;
        }
    </style>
</head>
<body>
    <div class="nav">
        <a href="{{ url_for('home') }}">Home</a>
        {% if session.get('user_id') %}
            {% if session.get('role') == 'admin' %}
                <a href="{{ url_for('admin_dashboard') }}">Admin Dashboard</a>
            {% else %}
                <a href="{{ url_for('user_dashboard') }}">User Dashboard</a>
                <a href="{{ url_for('submit_issue') }}">Submit Issue</a>
            {% endif %}
            <a href="{{ url_for('logout') }}">Logout</a>
        {% else %}
            <a href="{{ url_for('login') }}">Login</a>
        {% endif %}
    </div>

    {% with messages = get_flashed_messages() %}
        {% if messages %}
            {% for message in messages %}
                <div class="flash">{{ message }}</div>
            {% endfor %}
        {% endif %}
    {% endwith %}

    {{ content|safe }}
</body>
</html>
"""


def render_page(title, content):
    return render_template_string(BASE_HTML, title=title, content=content)


# ----------------------------
# Routes
# ----------------------------
@app.route("/")
def home():
    content = """
    <div class="card">
        <h1>Operations Portal Demo</h1>
        <p>This is a simplified Flask demo showing role-based login, issue submission, and admin tracking workflows.</p>
        <p class="small"><strong>Demo accounts:</strong><br>
        Admin: admin / admin123<br>
        User: user1 / user123</p>
    </div>
    """
    return render_page("Home", content)


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            session["user_id"] = user.id
            session["username"] = user.username
            session["role"] = user.role
            flash("Logged in successfully.")

            if user.role == "admin":
                return redirect(url_for("admin_dashboard"))
            return redirect(url_for("user_dashboard"))

        flash("Invalid username or password.")

    content = """
    <div class="card">
        <h2>Login</h2>
        <form method="POST">
            <label>Username</label>
            <input type="text" name="username" required>

            <label>Password</label>
            <input type="password" name="password" required>

            <button type="submit">Login</button>
        </form>
    </div>
    """
    return render_page("Login", content)


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.")
    return redirect(url_for("home"))


@app.route("/user")
def user_dashboard():
    if not login_required() or session.get("role") != "user":
        flash("Please log in as a user.")
        return redirect(url_for("login"))

    issues = Issue.query.filter_by(submitted_by=session["username"]).order_by(Issue.created_at.desc()).all()

    rows = ""
    for issue in issues:
        rows += f"""
        <tr>
            <td>{issue.id}</td>
            <td>{issue.title}</td>
            <td class="status">{issue.status}</td>
            <td>{issue.created_at.strftime('%Y-%m-%d %H:%M')}</td>
        </tr>
        """

    content = f"""
    <div class="card">
        <h2>User Dashboard</h2>
        <p>Welcome, <strong>{session['username']}</strong></p>
        <p><a href="{url_for('submit_issue')}">Submit a New Issue</a></p>
    </div>

    <div class="card">
        <h3>Your Submitted Issues</h3>
        <table width="100%" cellpadding="8" cellspacing="0" border="1">
            <tr>
                <th>ID</th>
                <th>Title</th>
                <th>Status</th>
                <th>Created</th>
            </tr>
            {rows if rows else '<tr><td colspan="4">No issues submitted yet.</td></tr>'}
        </table>
    </div>
    """
    return render_page("User Dashboard", content)


@app.route("/submit", methods=["GET", "POST"])
def submit_issue():
    if not login_required() or session.get("role") != "user":
        flash("Please log in as a user.")
        return redirect(url_for("login"))

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()

        if not title or not description:
            flash("Title and description are required.")
            return redirect(url_for("submit_issue"))

        issue = Issue(
            title=title,
            description=description,
            submitted_by=session["username"]
        )
        db.session.add(issue)
        db.session.commit()

        flash("Issue submitted successfully.")
        return redirect(url_for("user_dashboard"))

    content = """
    <div class="card">
        <h2>Submit Issue</h2>
        <form method="POST">
            <label>Issue Title</label>
            <input type="text" name="title" required>

            <label>Description</label>
            <textarea name="description" rows="6" required></textarea>

            <button type="submit">Submit</button>
        </form>
    </div>
    """
    return render_page("Submit Issue", content)


@app.route("/admin")
def admin_dashboard():
    if not login_required() or not admin_required():
        flash("Please log in as an admin.")
        return redirect(url_for("login"))

    issues = Issue.query.order_by(Issue.created_at.desc()).all()

    rows = ""
    for issue in issues:
        rows += f"""
        <tr>
            <td>{issue.id}</td>
            <td>{issue.title}</td>
            <td>{issue.submitted_by}</td>
            <td>{issue.status}</td>
            <td>{issue.created_at.strftime('%Y-%m-%d %H:%M')}</td>
            <td>
                <form method="POST" action="{url_for('update_status', issue_id=issue.id)}">
                    <select name="status">
                        <option value="Submitted" {"selected" if issue.status == "Submitted" else ""}>Submitted</option>
                        <option value="In Review" {"selected" if issue.status == "In Review" else ""}>In Review</option>
                        <option value="Resolved" {"selected" if issue.status == "Resolved" else ""}>Resolved</option>
                    </select>
                    <button type="submit">Update</button>
                </form>
            </td>
        </tr>
        """

    content = f"""
    <div class="card">
        <h2>Admin Dashboard</h2>
        <p>Welcome, <strong>{session['username']}</strong></p>
    </div>

    <div class="card">
        <h3>All Submitted Issues</h3>
        <table width="100%" cellpadding="8" cellspacing="0" border="1">
            <tr>
                <th>ID</th>
                <th>Title</th>
                <th>Submitted By</th>
                <th>Status</th>
                <th>Created</th>
                <th>Action</th>
            </tr>
            {rows if rows else '<tr><td colspan="6">No issues available.</td></tr>'}
        </table>
    </div>
    """
    return render_page("Admin Dashboard", content)


@app.route("/update_status/<int:issue_id>", methods=["POST"])
def update_status(issue_id):
    if not login_required() or not admin_required():
        flash("Unauthorized.")
        return redirect(url_for("login"))

    issue = Issue.query.get_or_404(issue_id)
    new_status = request.form.get("status", "").strip()

    if new_status not in ["Submitted", "In Review", "Resolved"]:
        flash("Invalid status.")
        return redirect(url_for("admin_dashboard"))

    issue.status = new_status
    db.session.commit()

    flash(f"Issue #{issue.id} updated to {new_status}.")
    return redirect(url_for("admin_dashboard"))


# ----------------------------
# App Startup
# ----------------------------
with app.app_context():
    db.create_all()
    seed_demo_data()

if __name__ == "__main__":
    app.run(debug=True)
