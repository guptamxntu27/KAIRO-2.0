from flask import Flask, render_template, redirect, url_for, request, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'kairo-secret-key-2026-default')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///kairo.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'admin_login'

# --- Database Models ---
class Admin(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

class Anime(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    poster_url = db.Column(db.String(500), nullable=False)
    description = db.Column(db.Text, nullable=True)
    episodes = db.relationship('Episode', backref='anime', cascade='all, delete-orphan', lazy=True)

class Episode(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    anime_id = db.Column(db.Integer, db.ForeignKey('anime.id'), nullable=False)
    episode_number = db.Column(db.Integer, nullable=False)
    title = db.Column(db.String(200), nullable=False)
    hindi_url = db.Column(db.String(500), nullable=True)
    english_url = db.Column(db.String(500), nullable=True)

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(Admin, int(user_id))

# --- Public Routes ---
@app.route('/')
def index():
    animes = Anime.query.all()
    return render_template('index.html', animes=animes)

@app.route('/anime/<int:anime_id>')
def anime_detail(anime_id):
    anime = Anime.query.get_or_404(anime_id)
    episodes = Episode.query.filter_by(anime_id=anime_id).order_by(Episode.episode_number.asc()).all()
    return render_template('anime_detail.html', anime=anime, episodes=episodes)

@app.route('/watch/<int:episode_id>')
def watch(episode_id):
    episode = Episode.query.get_or_404(episode_id)
    anime = Anime.query.get(episode.anime_id)
    all_episodes = Episode.query.filter_by(anime_id=episode.anime_id).order_by(Episode.episode_number.asc()).all()
    return render_template('watch.html', episode=episode, anime=anime, all_episodes=all_episodes)

# --- Admin Authentication ---
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if current_user.is_authenticated:
        return redirect(url_for('admin_dashboard'))
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        admin = Admin.query.filter_by(username=username).first()
        if admin and check_password_hash(admin.password, password):
            login_user(admin)
            return redirect(url_for('admin_dashboard'))
        flash('Sahi Username ya Password dalein!', 'error')
    return render_template('auth.html')

@app.route('/admin/logout')
@login_required
def admin_logout():
    logout_user()
    return redirect(url_for('admin_login'))

@app.route('/admin/change-password', methods=['POST'])
@login_required
def change_password():
    old_pw = request.form.get('old_password')
    new_pw = request.form.get('new_password')
    if check_password_hash(current_user.password, old_pw):
        current_user.password = generate_password_hash(new_pw, method='pbkdf2:sha256')
        db.session.commit()
        flash('Password safaltapurvak badal gaya!', 'success')
    else:
        flash('Purana Password galat hai!', 'error')
    return redirect(url_for('admin_dashboard'))

# --- Admin CRUD Operations ---
@app.route('/admin')
@login_required
def admin_dashboard():
    animes = Anime.query.all()
    return render_template('admin.html', animes=animes)

@app.route('/admin/anime/add', methods=['POST'])
@login_required
def add_anime():
    title = request.form.get('title')
    poster_url = request.form.get('poster_url')
    description = request.form.get('description')
    if title and poster_url:
        new_anime = Anime(title=title, poster_url=poster_url, description=description)
        db.session.add(new_anime)
        db.session.commit()
        flash('Anime add ho gaya!', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/anime/delete/<int:anime_id>')
@login_required
def delete_anime(anime_id):
    anime = Anime.query.get_or_404(anime_id)
    db.session.delete(anime)
    db.session.commit()
    flash('Anime aur uske episodes delete ho gaye!', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/episode/add/<int:anime_id>', methods=['POST'])
@login_required
def add_episode(anime_id):
    ep_num = request.form.get('episode_number')
    title = request.form.get('title')
    hindi_url = request.form.get('hindi_url')
    english_url = request.form.get('english_url')
    
    new_ep = Episode(
        anime_id=anime_id,
        episode_number=ep_num,
        title=title,
        hindi_url=hindi_url,
        english_url=english_url
    )
    db.session.add(new_ep)
    db.session.commit()
    flash('Episode add ho gaya!', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/episode/delete/<int:episode_id>')
@login_required
def delete_episode(episode_id):
    ep = Episode.query.get_or_404(episode_id)
    db.session.delete(ep)
    db.session.commit()
    flash('Episode delete ho gaya!', 'success')
    return redirect(url_for('admin_dashboard'))

# Database Initialization
with app.app_context():
    db.create_all()
    if not Admin.query.filter_by(username='admin').first():
        default_admin = Admin(
            username='admin',
            password=generate_password_hash('admin123', method='pbkdf2:sha256')
        )
        db.session.add(default_admin)
        db.session.commit()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
