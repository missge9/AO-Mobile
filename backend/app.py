from flask import Flask, request, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import os

# WICHTIG: Wir sagen Flask, dass HTML und statische Dateien eine Ebene höher liegen (..)
app = Flask(__name__, template_folder='../', static_folder='../')

# Pfad zur Datenbank im 'data' Ordner festlegen
base_dir = os.path.abspath(os.path.dirname(__file__))
db_path = os.path.join(base_dir, '../data/users.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# --- Datenbank Modell ---
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# Erstellt die Tabellen im 'data' Ordner
with app.app_context():
    db.create_all()

# --- Routen für die HTML-Seiten ---
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/shop')
def shop():
    return render_template('shop.html')

@app.route('/sell')
def sell():
    return render_template('sell.html')

@app.route('/login')
def login_page():
    return render_template('account.html')

@app.route('/detail')
def detail():
    return render_template('detail.html')

@app.route('/cart')
def cart():
    return render_template('cart.html')


# --- API Routen für Nutzer ---
@app.route('/api/register', methods=['POST'])
def register():
    data = request.json
    if User.query.filter_by(username=data['username']).first():
        return jsonify({"message": "Nutzername bereits vergeben"}), 400
    
    user = User(username=data['username'], email=data['email'])
    user.set_password(data['password'])
    db.session.add(user)
    db.session.commit()
    return jsonify({"message": "Konto erfolgreich erstellt"}), 201

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    user = User.query.filter_by(username=data['username']).first()
    
    if user and user.check_password(data['password']):
        return jsonify({
            "message": "Login erfolgreich",
            "username": user.username,
            "email": user.email
        }), 200
        
    return jsonify({"message": "Nutzername oder Passwort falsch"}), 401

if __name__ == '__main__':
    app.run(debug=True)