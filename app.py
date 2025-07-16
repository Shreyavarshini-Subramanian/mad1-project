from flask import Flask, render_template, redirect, url_for, request, flash, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from pytz import timezone
import pytz
from zoneinfo import ZoneInfo

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.sqlite3'
app.config['SECRET_KEY'] = 'your_secret_key'
db = SQLAlchemy()
db.init_app(app)

class User(db.Model):
    __tablename__ = 'user'
    u_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    email = db.Column(db.String(20), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    name = db.Column(db.String(30), nullable=False)
    address= db.Column(db.Text, nullable=False)
    pincode=db.Column(db.Integer, nullable=False)
    reservations = db.relationship('Reservation', backref='user', lazy=True)

class Admin(db.Model):
    __tablename__ = 'admin'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    email = db.Column(db.String(20), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    name = db.Column(db.String(30), nullable=False)

class ParkingLot(db.Model):
    __tablename__ = 'parking_lot'
    lot_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    prime_location_name = db.Column(db.String(50), nullable=False)
    price_per_hour = db.Column(db.Float, nullable=False)
    address = db.Column(db.String(100), nullable=False)
    pincode = db.Column(db.String(10), nullable=False)
    max_spots = db.Column(db.Integer, nullable=False)
    spots = db.relationship('ParkingSpot', backref='lot', lazy=True, cascade="all, delete")

class ParkingSpot(db.Model):
    __tablename__ = 'parking_spot'
    spot_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    lot_id = db.Column(db.Integer, db.ForeignKey('parking_lot.lot_id', ondelete='CASCADE'), nullable=False)
    status = db.Column(db.String(1), nullable=False, default='A')  
    reservations = db.relationship('Reservation', backref='spot', lazy=True)

class Reservation(db.Model):
    __tablename__ = 'reservation'
    res_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    spot_id = db.Column(db.Integer, db.ForeignKey('parking_spot.spot_id', ondelete='CASCADE'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.u_id', ondelete='CASCADE'), nullable=False)
    parking_timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    leaving_timestamp = db.Column(db.DateTime, nullable=True)
    total_cost = db.Column(db.Float, nullable=True)  
    vehicle_no = db.Column(db.String(20), nullable=False)

@app.before_request
def create_tables():
    db.create_all()
    if not Admin.query.filter_by(email="abc@gmail.com").first():
        admin=Admin(email="abc@gmail.com",password=generate_password_hash("Shreya@123"),name="Admin")
        db.session.add(admin)
        db.session.commit()

@app.route('/clear_flash_messages', methods=['POST'])
def clear_flash_messages():
    session.pop('_flashes', None) 
    return '', 204

@app.route('/')
def start():
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method=='POST':
        email=request.form.get('email')
        password=request.form.get('password')
        name=request.form.get('name')
        address=request.form.get('address')
        pincode=request.form.get('pincode')
        if not email or not password or not name or not address or not pincode:
            flash("All fields are required!", "danger")
        else:
            exist=User.query.filter_by(email=email).first()
            if exist:
                flash("User already registered!","warning")
                return redirect(url_for('register'))
            else:
                p=generate_password_hash(password)
                new=User(email=email, password=p,name=name, address=address, pincode=pincode)
                try:
                    db.session.add(new)
                    db.session.commit()
                    flash("Registered successfully!","success!!")
                    return redirect(url_for('login'))
                except Exception as x:
                    db.session.rollback()
                    flash(f"{str(x)}")
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        if not email or not password:
            flash("All fields are required!", "danger")
        else:
            admin = Admin.query.filter_by(email=email).first()
            if admin and check_password_hash(admin.password, password):
                session['admin_id'] = admin.id
                session['name'] = admin.name
                session['user_role'] = 'admin'
                flash("Admin login successful", "success")
                return redirect(url_for('admin_dashboard'))
            user = User.query.filter_by(email=email).first()
            if user and check_password_hash(user.password, password):
                session['u_id'] = user.u_id
                session['name'] = user.name
                flash("User login successful", "success")
                return redirect(url_for('user_dashboard'))
            flash("Invalid login credentials!", "warning")
    return render_template('login.html')

@app.route('/logout')
def logout():
    if 'admin_id' in session:
        admin_or_not = True
    elif 'u_id' in session:
        admin_or_not = False
    else:
        flash("No active session found", "info")
        return redirect(url_for('login'))
    session.clear()
    return render_template('logout.html', admin=admin_or_not)