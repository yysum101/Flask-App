import os
import psycopg2
import urllib.parse as up
from flask import Flask, request, redirect, url_for, session, flash, render_template_string
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.secret_key = "supersecret"

# Database config for Render
DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL:
    up.uses_netloc.append("postgres")
    url = up.urlparse(DATABASE_URL)
    app.config["SQLALCHEMY_DATABASE_URI"] = f"postgresql://{url.username}:{url.password}@{url.hostname}:{url.port}{url.path}"
else:
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///local.db"

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

# ------------------ MODELS ------------------ #
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    about = db.Column(db.String(500))
    posts = db.relationship("Post", backref="author", lazy=True)
    messages = db.relationship("Message", backref="sender", lazy=True)

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    subject = db.Column(db.String(200), nullable=False)
    body = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(500), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

with app.app_context():
    db.create_all()

# ------------------ TEMPLATES ------------------ #
BASE_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>{{ title }}</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
<style>
body { background: linear-gradient(135deg, #a2d2ff, #b9fbc0); min-height: 100vh; }
.card { border-radius: 15px; box-shadow: 0px 4px 15px rgba(0,0,0,0.1); }
.chat-bubble { padding: 10px 15px; border-radius: 15px; margin-bottom: 5px; max-width: 70%; }
.chat-right { background-color: #a2d2ff; align-self: flex-end; text-align: right; }
.chat-left { background-color: #b9fbc0; align-self: flex-start; }
</style>
</head>
<body>
<nav class="navbar navbar-expand-lg navbar-dark bg-primary">
<div class="container-fluid">
<a class="navbar-brand fw-bold" href="#">FriendBook</a>
<div class="collapse navbar-collapse">
<ul class="navbar-nav ms-auto">
{% if session.get('user_id') %}
<li class="nav-item"><a class="nav-link" href="{{ url_for('dashboard') }}">Dashboard</a></li>
<li class="nav-item"><a class="nav-link" href="{{ url_for('chat') }}">Chat</a></li>
<li class="nav-item"><a class="nav-link" href="{{ url_for('profile', user_id=session['user_id']) }}">Profile</a></li>
<li class="nav-item"><a class="nav-link" href="{{ url_for('settings') }}">Settings</a></li>
<li class="nav-item"><a class="nav-link" href="{{ url_for('logout') }}">Logout</a></li>
{% else %}
<li class="nav-item"><a class="nav-link" href="{{ url_for('login') }}">Login</a></li>
<li class="nav-item"><a class="nav-link" href="{{ url_for('register') }}">Register</a></li>
{% endif %}
</ul>
</div>
</div>
</nav>
<div class="container my-4">
{% with messages = get_flashed_messages() %}
  {% if messages %}
    {% for msg in messages %}
      <div class="alert alert-info">{{ msg }}</div>
    {% endfor %}
  {% endif %}
{% endwith %}
{{ content|safe }}
</div>
</body>
</html>
"""

# ------------------ ROUTES ------------------ #
@app.route("/")
def home():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        confirm = request.form["confirm"]
        about = request.form["about"]
        if password != confirm:
            flash("Passwords do not match")
            return redirect(url_for("register"))
        if User.query.filter_by(username=username).first():
            flash("Username already taken")
            return redirect(url_for("register"))
        hashed = generate_password_hash(password)
        user = User(username=username, password=hashed, about=about)
        db.session.add(user)
        db.session.commit()
        flash("Registered successfully, please login.")
        return redirect(url_for("login"))
    content = """
    <div class="card p-4 mx-auto" style="max-width:400px;">
    <h3 class="mb-3">Register</h3>
    <form method="POST">
      <input class="form-control mb-2" name="username" placeholder="Username" required>
      <input class="form-control mb-2" type="password" name="password" placeholder="Password" required>
      <input class="form-control mb-2" type="password" name="confirm" placeholder="Confirm Password" required>
      <textarea class="form-control mb-2" name="about" placeholder="Tell us more about yourself"></textarea>
      <button class="btn btn-success w-100">Register</button>
    </form>
    </div>
    """
    return render_template_string(BASE_HTML, title="Register", content=content)

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            session["user_id"] = user.id
            flash("Welcome back!")
            return redirect(url_for("dashboard"))
        flash("Invalid credentials")
    content = """
    <div class="card p-4 mx-auto" style="max-width:400px;">
    <h3 class="mb-3">Login</h3>
    <form method="POST">
      <input class="form-control mb-2" name="username" placeholder="Username" required>
      <input class="form-control mb-2" type="password" name="password" placeholder="Password" required>
      <button class="btn btn-primary w-100">Login</button>
    </form>
    </div>
    """
    return render_template_string(BASE_HTML, title="Login", content=content)

@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out")
    return redirect(url_for("login"))

@app.route("/dashboard", methods=["GET", "POST"])
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))
    if request.method == "POST":
        subject = request.form["subject"]
        body = request.form["body"]
        post = Post(subject=subject, body=body, user_id=session["user_id"])
        db.session.add(post)
        db.session.commit()
        flash("Post added")
    posts = Post.query.order_by(Post.timestamp.desc()).all()
    content = """
    <div class="card p-4 mb-4">
      <h4>New Post</h4>
      <form method="POST">
        <input class="form-control mb-2" name="subject" placeholder="Subject" required>
        <textarea class="form-control mb-2" name="body" placeholder="Body" required></textarea>
        <button class="btn btn-success">Post</button>
      </form>
    </div>
    {% for post in posts %}
    <div class="card p-3 mb-3">
      <h5>{{ post.subject }}</h5>
      <p>{{ post.body }}</p>
      <small>By {{ post.author.username }} on {{ post.timestamp.strftime('%Y-%m-%d %H:%M') }}</small>
    </div>
    {% endfor %}
    """
    return render_template_string(BASE_HTML, title="Dashboard", content=render_template_string(content, posts=posts))

@app.route("/chat", methods=["GET", "POST"])
def chat():
    if "user_id" not in session:
        return redirect(url_for("login"))
    if request.method == "POST":
        text = request.form["text"]
        msg = Message(text=text, user_id=session["user_id"])
        db.session.add(msg)
        db.session.commit()
    messages = Message.query.order_by(Message.timestamp.asc()).all()
    content = """
    <div class="d-flex flex-column">
    {% for msg in messages %}
      <div class="chat-bubble {% if msg.user_id == session['user_id'] %}chat-right{% else %}chat-left{% endif %}">
        <b>{{ msg.sender.username }}</b><br>{{ msg.text }}
      </div>
    {% endfor %}
    </div>
    <form method="POST" class="mt-3 d-flex">
      <input class="form-control me-2" name="text" placeholder="Type a message" required>
      <button class="btn btn-primary">Send</button>
    </form>
    """
    return render_template_string(BASE_HTML, title="Chat", content=render_template_string(content, messages=messages))

@app.route("/profile/<int:user_id>")
def profile(user_id):
    if "user_id" not in session:
        return redirect(url_for("login"))
    user = User.query.get_or_404(user_id)
    content = f"""
    <div class="card p-4">
      <h3>{user.username}</h3>
      <p>{user.about or "No information yet."}</p>
    </div>
    """
    return render_template_string(BASE_HTML, title="Profile", content=content)

@app.route("/settings", methods=["GET", "POST"])
def settings():
    if "user_id" not in session:
        return redirect(url_for("login"))
    user = User.query.get(session["user_id"])
    if request.method == "POST":
        new_username = request.form["username"]
        new_about = request.form["about"]
        new_password = request.form["password"]
        if new_username:
            user.username = new_username
        if new_about:
            user.about = new_about
        if new_password:
            user.password = generate_password_hash(new_password)
        db.session.commit()
        flash("Profile updated")
    content = f"""
    <div class="card p-4 mx-auto" style="max-width:500px;">
    <h3>Settings</h3>
    <form method="POST">
      <input class="form-control mb-2" name="username" placeholder="New Username" value="{user.username}">
      <textarea class="form-control mb-2" name="about" placeholder="About">{user.about or ""}</textarea>
      <input class="form-control mb-2" type="password" name="password" placeholder="New Password">
      <button class="btn btn-warning w-100">Update</button>
    </form>
    </div>
    """
    return render_template_string(BASE_HTML, title="Settings", content=content)

if __name__ == "__main__":
    app.run(debug=True)
