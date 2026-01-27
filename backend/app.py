from flask import Flask, request, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from cryptography.fernet import Fernet
from datetime import datetime
import os
import json

app = Flask(__name__, template_folder='../', static_folder='../')

# Sicherheitsschlüssel (für Adress-Daten Verschlüsselung)
SECRET_KEY = b'Yiv7xtGkDk1bnlDo2wIhLlXeMbhsfRa4ZI4T52ovF-Y='
cipher = Fernet(SECRET_KEY)

base_dir = os.path.abspath(os.path.dirname(__file__))
db_path = os.path.join(base_dir, '../data/users.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

UPLOAD_FOLDER = os.path.join(base_dir, '../static/uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

db = SQLAlchemy(app)

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'avif'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Hilfsfunktionen für Verschlüsselung
def encrypt_data(data):
    if not data: return None
    return cipher.encrypt(data.encode()).decode()

def decrypt_data(data):
    if not data: return None
    try:
        return cipher.decrypt(data.encode()).decode()
    except:
        return "Fehler bei Entschlüsselung"

# --- Datenbank Modell ---
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), nullable=False) # Voller Name
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    
    # Adresse (Verschlüsselt gespeichert, hier vereinfacht Text)
    street = db.Column(db.Text)
    house_number = db.Column(db.Text)
    zip_code = db.Column(db.Text)
    city = db.Column(db.Text)
    
    # NEU: Telefon
    phone = db.Column(db.String(50)) 

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

with app.app_context():
    db.create_all()

# --- HTML Routen ---
@app.route('/')
def index(): return render_template('index.html')


# shop routing
@app.route('/shop')
def shop(): return render_template('shop/shop.html')

@app.route('/detail')  
def detail(): 
    return render_template('shop/detail.html')

@app.route('/cart')
def cart(): return render_template('shop/cart.html')

@app.route('/checkout')
def checkout_page(): return render_template('shop/checkout.html')

@app.route('/success')
def success_page(): return render_template('shop/success.html')


#sell routing
@app.route('/sell')
def sell(): return render_template('sell/sell.html')


#Account routing
@app.route('/register')
def register_page(): return render_template('account/account.html')

@app.route('/login')
def login_page(): return render_template('account/account.html')

@app.route('/userpage')
def userpage_page(): return render_template('account/userpage.html')

@app.route('/register-success')
def register_success_page(): return render_template('account/register_success.html')


# Admin routing
@app.route('/admin')
def admin_dashboard(): return render_template('admin/admin.html')

@app.route('/admin/inventory')
def admin_inventory(): return render_template('admin/inventory_admin.html')

@app.route('/admin/orders')
def admin_orders(): return render_template('admin/orders_admin.html')

@app.route('/orders') # Alias für Admin Orders
def orders_page(): return render_template('admin/orders_admin.html')

@app.route('/admin/sales')
def admin_sales(): return render_template('admin/sales_admin.html')


# --- API ROUTEN (User & Shop) ---

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    user = User.query.filter_by(email=data['email']).first()
    
    if user and user.check_password(data['password']):
        return jsonify({
            "message": "Login erfolgreich",
            "username": user.username,     # Voller Name (für Anzeige oben)
            "firstname": getattr(user, 'firstname', '') or user.username.split(' ')[0], # Fallback
            "second_name": getattr(user, 'second_name', ''),
            "lastname": getattr(user, 'lastname', '') or user.username.split(' ')[-1], # Fallback
            "email": user.email,
            "phone": user.phone,           # <--- Telefonnummer
            "street": decrypt_data(user.street),
            "house_number": decrypt_data(user.house_number),
            "zip_code": decrypt_data(user.zip_code),
            "city": decrypt_data(user.city)
        }), 200
        
    return jsonify({"message": "E-Mail oder Passwort falsch"}), 401

@app.route('/api/register', methods=['POST'])
def register_user():
    data = request.json
    
    # 1. Prüfen ob E-Mail existiert
    if User.query.filter_by(email=data['email']).first():
        return jsonify({"message": "E-Mail bereits registriert"}), 400

    # 2. Namen zusammenbauen
    first = data.get('firstname', '')
    second = data.get('second_name', '')
    last = data.get('lastname', '')
    
    if second:
        full_name = f"{first} {second} {last}"
    else:
        full_name = f"{first} {last}"

    # 3. User erstellen (Daten verschlüsseln wo nötig)
    new_user = User(
        username=full_name,
        email=data['email'],
        phone=data.get('phone'),
        street=encrypt_data(data.get('street')),
        house_number=encrypt_data(data.get('house_number')),
        zip_code=encrypt_data(data.get('zip') or data.get('zip_code')),
        city=encrypt_data(data.get('city'))
    )
    
    new_user.set_password(data['password'])

    try:
        db.session.add(new_user)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": "Datenbank Fehler: " + str(e)}), 500

    # 4. Antwort für Frontend
    user_data = {
        "username": new_user.username,
        "email": new_user.email,
        "phone": new_user.phone,
        "street": data.get('street'),
        "house_number": data.get('house_number'),
        "zip_code": data.get('zip') or data.get('zip_code'),
        "city": data.get('city')
    }

    return jsonify({"message": "Erfolgreich registriert", "user": user_data}), 201

@app.route('/api/my-orders', methods=['POST'])
def my_orders():
    user_email = request.json.get('email')
    orders_path = os.path.join(base_dir, '../data/orders.json')
    my_orders_list = []

    if os.path.exists(orders_path):
        with open(orders_path, 'r', encoding='utf-8') as f:
            all_orders = json.load(f)
            
        for order in all_orders:
            cust_email = order.get('customer', {}).get('email')
            if cust_email == user_email:
                my_orders_list.append(order)

    return jsonify(my_orders_list)

@app.route('/api/my-sales', methods=['POST'])
def my_sales():
    email = request.json.get('email')
    sales_path = os.path.join(base_dir, '../data/sales.json')
    
    my_list = []
    if os.path.exists(sales_path):
        with open(sales_path, 'r', encoding='utf-8') as f:
            all_sales = json.load(f)
            my_list = [s for s in all_sales if s.get('user_email') == email]
            
    return jsonify(my_list)


# --- CHECKOUT LOGIK ---
@app.route('/api/checkout', methods=['POST'])
def checkout():
    data = request.json
    cart_items = data.get('cart', [])
    
    billing_address = data.get('billingAddress', {})
    shipping_address = data.get('shippingAddress', {})
    payment_method = data.get('paymentMethod', 'unknown')
    has_insurance = data.get('insurance', False)

    if not cart_items:
        return jsonify({"message": "Warenkorb leer"}), 400

    json_path = os.path.join(base_dir, '../data/data.json')
    orders_path = os.path.join(base_dir, '../data/orders.json')
    
    with open(json_path, 'r', encoding='utf-8') as f:
        shop_data = json.load(f)
    
    if os.path.exists(orders_path):
        with open(orders_path, 'r', encoding='utf-8') as f:
            orders = json.load(f)
    else:
        orders = []

    items_bought = []
    items_total_price = 0

    # Inventar abziehen
    for cart_item in cart_items:
        found = False
        target_id = str(cart_item['id'])
        for brand in shop_data:
            for product in shop_data[brand]['products']:
                if 'inventory' in product:
                    original_len = len(product['inventory'])
                    product['inventory'] = [i for i in product['inventory'] if str(i['id']) != target_id]
                    if len(product['inventory']) < original_len:
                        found = True
                        items_bought.append(cart_item)
                        items_total_price += float(cart_item['price'])
                        break 
            if found: break
        
        if not found:
            return jsonify({"message": f"Gerät #{target_id} ist nicht mehr verfügbar!"}), 409

    shipping_cost = 10.0 if has_insurance else 0.0
    final_total = items_total_price + shipping_cost

    new_order = {
        "order_id": f"ORD-{int(datetime.now().timestamp())}",
        "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "status": "Offen",
        "customer": billing_address,
        "shipping_address": shipping_address,
        "payment": payment_method,
        "insurance": has_insurance,
        "items": items_bought,
        "subtotal": items_total_price,
        "shipping_cost": shipping_cost,
        "total": final_total
    }
    orders.insert(0, new_order)

    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(shop_data, f, indent=2, ensure_ascii=False)
    with open(orders_path, 'w', encoding='utf-8') as f:
        json.dump(orders, f, indent=2, ensure_ascii=False)

    return jsonify({"message": "Erfolg", "order_id": new_order['order_id']}), 200


# --- ADMIN API ROUTEN ---

@app.route('/api/admin/data', methods=['GET', 'POST'])
def admin_data_handler():
    json_path = os.path.join(base_dir, '../data/data.json')

    if request.method == 'POST':
        try:
            new_data = request.json
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(new_data, f, indent=2, ensure_ascii=False)
            return jsonify({"message": "Gespeichert"}), 200
        except Exception as e:
            return jsonify({"message": "Fehler beim Speichern"}), 500
    else:
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return jsonify(data)
        except Exception as e:
            return jsonify({"error": "Konnte Datei nicht lesen"}), 500

@app.route('/api/admin/orders', methods=['GET', 'POST'])
def orders_api():
    orders_path = os.path.join(base_dir, '../data/orders.json')
    
    if request.method == 'GET':
        if os.path.exists(orders_path):
            with open(orders_path, 'r', encoding='utf-8') as f:
                return jsonify(json.load(f))
        return jsonify([])
    
    if request.method == 'POST':
        req = request.json
        if os.path.exists(orders_path):
            with open(orders_path, 'r', encoding='utf-8') as f:
                orders = json.load(f)
            
            for o in orders:
                if o['order_id'] == req['order_id']:
                    o['status'] = req['status']
                    if req['status'] == 'Versendet':
                        o['shipped_date'] = datetime.now().strftime("%d.%m.%Y")
                    break
            
            with open(orders_path, 'w', encoding='utf-8') as f:
                json.dump(orders, f, indent=2, ensure_ascii=False)
            return jsonify({"message": "Status aktualisiert"})
        return jsonify({"error": "Fehler"}), 404

# --- API für Ankauf (Sell) ---

@app.route('/api/sell', methods=['POST'])
def register_sale():
    data = request.json
    sales_path = os.path.join(base_dir, '../data/sales.json')
    
    if os.path.exists(sales_path):
        with open(sales_path, 'r', encoding='utf-8') as f:
            try:
                sales = json.load(f)
            except:
                sales = []
    else:
        sales = []
        
    new_sale = {
        "sale_id": f"SELL-{int(datetime.now().timestamp())}",
        "date": datetime.now().strftime("%d.%m.%Y"),
        "user_email": data.get('email'),
        "device": data.get('device'),
        "specs": data.get('specs'),
        "offer_price": data.get('price'),
        "status": "In Prüfung"
    }
    
    sales.insert(0, new_sale)
    
    with open(sales_path, 'w', encoding='utf-8') as f:
        json.dump(sales, f, indent=2, ensure_ascii=False)
        
    return jsonify({"message": "Verkauf registriert", "id": new_sale['sale_id']}), 200

@app.route('/api/admin/sales', methods=['GET', 'POST'])
def admin_sales_api():
    sales_path = os.path.join(base_dir, '../data/sales.json')
    
    if request.method == 'GET':
        if os.path.exists(sales_path):
            with open(sales_path, 'r', encoding='utf-8') as f:
                return jsonify(json.load(f))
        return jsonify([])
    
    if request.method == 'POST':
        req = request.json
        target_id = req.get('sale_id')
        new_status = req.get('status')
        
        if os.path.exists(sales_path):
            with open(sales_path, 'r', encoding='utf-8') as f:
                sales = json.load(f)
            
            for s in sales:
                if s['sale_id'] == target_id:
                    s['status'] = new_status
                    break
            
            with open(sales_path, 'w', encoding='utf-8') as f:
                json.dump(sales, f, indent=2, ensure_ascii=False)
            return jsonify({"message": "Status aktualisiert"})
        return jsonify({"error": "Datei nicht gefunden"}), 404

@app.route('/api/admin/upload', methods=['POST'])
def upload_files():
    # Prüfen, ob Dateien im Request sind
    if 'files' not in request.files:
        return jsonify({'error': 'Keine Dateien gefunden'}), 400
    
    # WICHTIG: .getlist() verwenden statt nur brackets []
    files = request.files.getlist('files')
    uploaded_urls = []

    for file in files:
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            # Hier dein Speicher-Pfad
            save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(save_path)
            
            # URL zur Liste hinzufügen
            uploaded_urls.append(f"/static/uploads/{filename}")
    
    # Gibt eine Liste aller hochgeladenen URLs zurück
    return jsonify({'urls': uploaded_urls})

@app.route('/api/admin/delete-image', methods=['POST'])
def delete_image():
    data = request.json
    image_url = data.get('url')
    
    if not image_url:
        return jsonify({'message': 'Keine URL übergeben'}), 400

    # Aus "/static/uploads/bild.jpg" machen wir den echten Pfad
    filename = os.path.basename(image_url)
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)

    if os.path.exists(file_path):
        os.remove(file_path)
        return jsonify({'message': 'Datei gelöscht'}), 200
    else:
        return jsonify({'message': 'Datei nicht gefunden (aber aus DB entfernt)'}), 200

if __name__ == '__main__':
    app.run(debug=True,port=8000)