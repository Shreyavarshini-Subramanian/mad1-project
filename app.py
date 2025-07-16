from flask import Flask, render_template, redirect, url_for, request, flash, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os
from pytz import timezone
import pytz
from zoneinfo import ZoneInfo

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.sqlite3'
app.config['SECRET_KEY'] = 'your_secret_key'
db = SQLAlchemy()
db.init_app(app)
base_dir=os.path.dirname(os.path.abspath(__file__))

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