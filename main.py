from flask import Flask, request, redirect, flash, render_template_string, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, login_required, logout_user, current_user, UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
import webbrowser

app = Flask(__name__)
app.config['SECRET_KEY'] = 'dev-secret-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///hobbyhub.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# --- Models ---
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(256), nullable=False)
    name = db.Column(db.String(120))
    is_admin = db.Column(db.Boolean, default=False)
    posts = db.relationship("Post", backref="author", lazy=True)

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    image_url = db.Column(db.String(500))
    likes = db.Column(db.Integer, default=0)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- Routes ---
@app.route('/')
def index():
    posts = Post.query.order_by(Post.id.desc()).all()
    return render_template_string("""
    <h1>HobbyHub - Hobby Social Network</h1>
    {% for msg in get_flashed_messages() %}
        <p>{{msg}}</p>
    {% endfor %}
    {% if current_user.is_authenticated %}
        <p>Hello, {{current_user.name or current_user.email}}! <a href="{{ url_for('profile') }}">Profile</a> | <a href="{{ url_for('logout') }}">Logout</a></p>
        {% if current_user.is_admin %}<p><a href="{{ url_for('admin') }}">Admin Panel</a></p>{% endif %}
    {% else %}
        <p><a href="{{ url_for('login') }}">Login</a> | <a href="{{ url_for('register') }}">Register</a></p>
    {% endif %}

    <h2>User Posts:</h2>
    {% for post in posts %}
        <div style="border:1px solid #ccc; padding:10px; margin:10px 0;">
            <h3>{{ post.title }}</h3>
            <p>{{ post.content }}</p>
            {% if post.image_url %}<img src="{{ post.image_url }}" width="200">{% endif %}
            <p>Author: {{ post.author.name or post.author.email }} | Likes: {{ post.likes }}</p>
        </div>
    {% else %}
        <p>No posts yet.</p>
    {% endfor %}
    """, posts=posts)

@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        email = request.form['email'].lower()
        password = request.form['password']
        name = request.form['name']
        if User.query.filter_by(email=email).first():
            flash("User already exists")
        else:
            user = User(email=email, password=generate_password_hash(password), name=name)
            db.session.add(user)
            db.session.commit()
            flash("Registered! Please log in.")
            return redirect(url_for('login'))
    return render_template_string("""
    <h2>Register</h2>
    <form method="post">
        Name: <input name="name"><br>
        Email: <input name="email"><br>
        Password: <input name="password" type="password"><br>
        <input type="submit">
    </form>
    """)

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        email = request.form['email'].lower()
        password = request.form['password']
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            flash("Logged in successfully!")
            return redirect(url_for('index'))
        flash("Invalid email or password")
    return render_template_string("""
    <h2>Login</h2>
    <form method="post">
        Email: <input name="email"><br>
        Password: <input name="password" type="password"><br>
        <input type="submit">
    </form>
    """)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash("You have been logged out")
    return redirect(url_for('index'))

@app.route('/profile', methods=['GET','POST'])
@login_required
def profile():
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        image_url = request.form.get('image_url')
        post = Post(title=title, content=content, image_url=image_url, author=current_user)
        db.session.add(post)
        db.session.commit()
        flash("Post added!")
        return redirect(url_for('profile'))
    posts = current_user.posts
    return render_template_string("""
    <h2>Your Profile</h2>
    <p>Hello, {{ current_user.name or current_user.email }}! <a href="{{ url_for('index') }}">Home</a> | <a href="{{ url_for('logout') }}">Logout</a></p>

    <h3>Add a Post</h3>
    <form method="post">
        Title: <input name="title"><br>
        Content:<br>
        <textarea name="content" rows="4" cols="50"></textarea><br>
        Image URL (optional): <input name="image_url"><br>
        <input type="submit" value="Add Post">
    </form>

    <h3>Your Posts</h3>
    {% for post in posts %}
        <div style="border:1px solid #ccc; padding:10px; margin:10px 0;">
            <h4>{{ post.title }}</h4>
            <p>{{ post.content }}</p>
            {% if post.image_url %}<img src="{{ post.image_url }}" width="200">{% endif %}
        </div>
    {% else %}
        <p>No posts yet.</p>
    {% endfor %}
    """, posts=posts)

@app.route('/admin')
@login_required
def admin():
    if not current_user.is_admin:
        return "403 - Access Denied"
    users = User.query.all()
    posts = Post.query.all()
    return render_template_string("""
    <h2>Admin Panel</h2>
    <p><a href="{{ url_for('index') }}">Home</a></p>
    <h3>Users</h3>
    <ul>
    {% for u in users %}
        <li>{{ u.name or u.email }} ({{ u.email }}) {% if u.is_admin %}[Admin]{% endif %}</li>
    {% endfor %}
    </ul>

    <h3>All Posts</h3>
    {% for post in posts %}
        <div style="border:1px solid #ccc; padding:10px; margin:10px 0;">
            <h4>{{ post.title }}</h4>
            <p>{{ post.content }}</p>
            {% if post.image_url %}<img src="{{ post.image_url }}" width="200">{% endif %}
            <p>Author: {{ post.author.name or post.author.email }}</p>
        </div>
    {% else %}
        <p>No posts yet.</p>
    {% endfor %}
    """, users=users, posts=posts)

# --- CLI commands ---
@app.cli.command('init-db')
def init_db():
    db.create_all()
    print("DB created!")

@app.cli.command('create-admin')
def create_admin():
    email = input("Email: ").strip().lower()
    password = input("Password: ").strip()
    name = input("Name: ").strip()
    user = User(email=email, password=generate_password_hash(password), name=name, is_admin=True)
    db.session.add(user)
    db.session.commit()
    print("Admin created!")

if __name__ == '__main__':

    host = '127.0.0.1'
    port = 8000
    url = f"http://{host}:{port}"

    # Відкриває браузер автоматично
    webbrowser.open(url)

    # Запуск Flask без автоперезавантаження
    app.run(host=host, port=port, debug=True, use_reloader=False)
