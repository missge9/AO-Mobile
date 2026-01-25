from flask import Flask, request, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import os

# App Konfiguration
app = Flask(__name__, template_folder='../', static_folder='../')

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
    # Adressfelder
    street = db.Column(db.String(100))
    house_number = db.Column(db.String(20))
    zip_code = db.Column(db.String(20))
    city = db.Column(db.String(100))

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# Tabellen erstellen
with app.app_context():
    db.create_all()

# --- HTML Routen (Seiten) ---
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/shop')
def shop():
    return render_template('shop.html')

@app.route('/sell')
def sell():
    return render_template('sell.html')

@app.route('/register')
def register_page():  # WICHTIG: Heisst jetzt anders als die API-Funktion!
    return render_template('account.html')

@app.route('/login')
def login_page():
    return render_template('account.html')

@app.route('/detail')
def detail():
    return render_template('detail.html')

@app.route('/cart')
def cart():
    return render_template('cart.html')


# --- API Routen (Logik) ---

@app.route('/api/register', methods=['POST'])
def register():
    data = request.json
    
    # Validierung
    if User.query.filter_by(username=data['username']).first():
        return jsonify({"message": "Nutzername bereits vergeben"}), 400
    
    if User.query.filter_by(email=data['email']).first():
        return jsonify({"message": "E-Mail bereits vergeben"}), 400
    
    # User anlegen
    user = User(
        username=data['username'], 
        email=data['email'],
        street=data.get('street'),
        house_number=data.get('house_number'),
        zip_code=data.get('zip'), # Achte darauf, dass im Frontend auch 'zip' gesendet wird
        city=data.get('city')
    )
    user.set_password(data['password'])
    
    try:
        db.session.add(user)
        db.session.commit()
        return jsonify({"message": "Konto erfolgreich erstellt"}), 201
    except Exception as e:
        print(f"Fehler: {e}")
        return jsonify({"message": "Datenbankfehler"}), 500

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