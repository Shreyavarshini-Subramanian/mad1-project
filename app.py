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

@app.route('/admin_dashboard', methods=['GET', 'POST'])
def admin_dashboard():
    lots = ParkingLot.query.all()
    parking_lots = []
    for lot in lots:
        spots = ParkingSpot.query.filter_by(lot_id=lot.lot_id).all()
        total = len(spots)  
        occupied = 0
        for s in spots:
            if s.status=='O':
                occupied=occupied+1

        parking_lots.append({
            'id': lot.lot_id,
            'name': lot.prime_location_name,
            'occupied': occupied,
            'total': total,
            'spots': spots  
        })
    return render_template('admin_dashboard.html', parking_lots=parking_lots)

@app.route('/add_parking_lot', methods=['GET', 'POST'])
def add_parking_lot():
    if request.method == 'POST':
        name = request.form['name']
        address = request.form['address']
        pincode = request.form['pincode']
        price = request.form['price']
        max_spots = int(request.form['max_spots'])
        new_lot = ParkingLot(
            prime_location_name=name,
            address=address,
            pincode=pincode,
            price_per_hour=float(price),
            max_spots=max_spots
        )
        db.session.add(new_lot)
        db.session.commit()
        for i in range(1, max_spots + 1):
            new_spot = ParkingSpot(
                lot_id=new_lot.lot_id,
                status='A'
            )
            db.session.add(new_spot)
        db.session.commit()
        flash('Parking lot added successfully with spots', 'success')
        return redirect(url_for('admin_dashboard'))
    return render_template('add_parking_lot.html')

@app.route('/edit_parking_lot/<int:lot_id>', methods=['GET', 'POST'])
def edit_parking_lot(lot_id):
    lot = ParkingLot.query.get_or_404(lot_id)
    if request.method == 'POST':
        new_max_spots = int(request.form['max_spots'])
        lot.prime_location_name = request.form['prime_location_name']
        lot.address = request.form['address']
        lot.pincode = request.form['pincode']
        lot.price_per_hour = float(request.form['price_per_hour'])
        current_spots = ParkingSpot.query.filter_by(lot_id=lot_id).all()
        current_count = len(current_spots)

        if new_max_spots > current_count:
            for i in range(current_count + 1, new_max_spots + 1):
                new_spot = ParkingSpot(
                    lot_id=lot.lot_id,
                    status='A'
                )
                db.session.add(new_spot)
        elif new_max_spots < current_count:
            removable_spots = ParkingSpot.query.filter_by(lot_id=lot_id, status='A').order_by(ParkingSpot.spot_id.desc()).all()
            to_remove = current_count - new_max_spots
            count = 0
            for spot in removable_spots:
                if count >= to_remove:
                    break
                db.session.delete(spot)
                count += 1
        lot.max_spots = new_max_spots
        db.session.commit()
        flash('Parking lot updated successfully', 'success')
        return redirect(url_for('admin_dashboard'))
    return render_template('edit_parking_lot.html', lot=lot)

@app.route('/delete_parking_lot/<int:lot_id>', methods=['POST'])
def delete_parking_lot(lot_id):
    lot = ParkingLot.query.get_or_404(lot_id)
    o_spots = ParkingSpot.query.filter_by(lot_id=lot.lot_id, status='O').count()
    if o_spots > 0:
        flash('Cannot delete: This parking lot has reserved spots!', 'danger')
        return redirect(url_for('admin_dashboard'))
    try:
        ParkingSpot.query.filter_by(lot_id=lot.lot_id).delete()
        db.session.delete(lot)
        db.session.commit()
        flash('Parking Lot deleted successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error: {str(e)}', 'danger')
    return redirect(url_for('admin_dashboard'))

@app.route('/view_delete_parking_spot/<int:spot_id>', methods=['GET', 'POST'])
def view_delete_parking_spot(spot_id):
    spot = ParkingSpot.query.get_or_404(spot_id)
    if request.method == 'POST':
        if spot.status == 'A':  
            db.session.delete(spot)
            lot=ParkingLot.query.get(spot.lot_id)
            if lot.max_spots>0:
                lot.max_spots-=1
            db.session.commit()
            flash('Spot deleted successfully', 'success')
        else:
            flash('Cannot delete an occupied spot!', 'danger')
        return redirect(url_for('admin_dashboard'))
    return render_template('view_delete_parking_spot.html', spot=spot)

@app.route('/occupied_parking_spot_details/<int:spot_id>')
def occupied_parking_spot_details(spot_id):
    spot = ParkingSpot.query.get_or_404(spot_id)
    if spot.status != 'O':
        flash('This spot is not currently occupied.', 'info')
        return redirect(url_for('admin_dashboard'))
    reservation = Reservation.query.filter_by(spot_id=spot.spot_id, leaving_timestamp=None).first()
    if not reservation:
        flash('No active reservation found for this spot.', 'info')
        return redirect(url_for('admin_dashboard'))
    lot = ParkingLot.query.get(spot.lot_id)
    ist = timezone('Asia/Kolkata')
    utc_time = reservation.parking_timestamp
    if utc_time.tzinfo is None:
        utc_time = pytz.utc.localize(utc_time)
    ist_time = utc_time.astimezone(ist)
    now_ist = datetime.utcnow().replace(tzinfo=pytz.utc).astimezone(ist)
    duration = (now_ist - ist_time).total_seconds() / 3600  
    cost = round(duration * lot.price_per_hour, 2)

    data = {
        'spot_id': spot.spot_id,
        'customer_id': reservation.user_id,
        'vehicle_no': reservation.vehicle_no,
        'timestamp': ist_time.strftime('%Y-%m-%d %H:%M'),
        'cost': cost
    }
    return render_template('occupied_parking_spot.html', spot=data)

@app.route('/admin/users')
def view_users():
    users = User.query.all()
    return render_template('view_users.html', users=users)

@app.route('/admin/search', methods=['GET'])
def admin_search():
    filter_by = request.args.get('filter_by')
    search_query = request.args.get('search_query')
    results = []
    if filter_by and search_query:
        if filter_by == "location":
            results = ParkingLot.query.filter(ParkingLot.prime_location_name.ilike(f"%{search_query}%")).all()
        elif filter_by == "pincode":
            results = ParkingLot.query.filter(ParkingLot.pincode.ilike(f"%{search_query}%")).all()
    return render_template('admin_search.html', results=results)

@app.route('/admin/summary')
def admin_summary():
    lots = ParkingLot.query.all()
    total_spots = 0
    total_occupied = 0
    total_revenue = 0.0
    summary = []
    ist = pytz.timezone('Asia/Kolkata')
    now = datetime.utcnow().replace(tzinfo=pytz.utc).astimezone(ist)
    for lot in lots:
        occupied = 0
        available = 0
        for s in lot.spots:
            if s.status=='O':
                occupied=occupied+1
            else:
                available=available+1
        total = occupied + available
        reservations = Reservation.query.join(ParkingSpot).filter(ParkingSpot.lot_id == lot.lot_id).all()
        revenue = 0.0
        for res in reservations:
            if res.total_cost:
                revenue += res.total_cost
            elif res.parking_timestamp:
                parked_time = res.parking_timestamp.replace(tzinfo=pytz.utc).astimezone(ist)
                if res.leaving_timestamp:
                    left_time = res.leaving_timestamp.replace(tzinfo=pytz.utc).astimezone(ist)
                else:
                    left_time = now  
                duration = (left_time - parked_time).total_seconds() / 3600
                estimated_cost = round(duration * lot.price_per_hour, 2)
                revenue += estimated_cost
        total_spots += total
        total_occupied += occupied
        total_revenue += revenue
        summary.append({
            'lot_id': lot.lot_id,
            'name': lot.prime_location_name,
            'rate': lot.price_per_hour,
            'occupied': occupied,
            'available': available,
            'total': total,
            'revenue': round(revenue, 2)
        })
    total_available = total_spots - total_occupied
    return render_template("admin_summary.html",
                           summary=summary,
                           total_lots=len(lots),
                           total_spots=total_spots,
                           total_occupied=total_occupied,
                           total_available=total_available,
                           total_revenue=round(total_revenue, 2))

def get_current_user():
    u_id = session.get('u_id')
    if u_id:
        return User.query.filter_by(u_id=u_id).first()
    return None

def get_parking_history(user_id):
    history = Reservation.query.filter_by(user_id=user_id).order_by(Reservation.parking_timestamp.desc()).all()
    for res in history:
        res.parking_timestamp = res.parking_timestamp.replace(tzinfo=ZoneInfo("UTC")).astimezone(ZoneInfo("Asia/Kolkata"))
    return history or []

def get_lots_by_location(location):
    lots = ParkingLot.query.filter(ParkingLot.prime_location_name.ilike(f"%{location}%")).all()
    return lots or []

@app.route('/user')
def user_dashboard():
    user = get_current_user()
    if not user:
        flash("Please log in to continue.", "warning")
        return redirect(url_for('login')) 
    history = get_parking_history(user.u_id)
    location = request.args.get("location", "")
    lots = get_lots_by_location(location)
    return render_template("user_dashboard.html", user=user, history=history, location=location, lots=lots)

def reserve_spot(user_id, spot_id, lot_id, vehicle_no):
    spot = ParkingSpot.query.get(spot_id)
    if spot:
        spot.status = 'O'
        reservation = Reservation(
            user_id=user_id,
            spot_id=spot_id,
            vehicle_no=vehicle_no,
            parking_timestamp=datetime.utcnow()
        )
        db.session.add(reservation)
        db.session.commit()

def get_available_spot(lot_id):
    return ParkingSpot.query.filter_by(lot_id=lot_id, status='A').first()

@app.route('/user/book/<int:lot_id>', methods=['GET', 'POST'])
def book_parking_spot(lot_id):
    user = get_current_user()
    spot = get_available_spot(lot_id)
    if not spot:
        flash("No available spots in this lot!", "warning")
        return redirect('/user')
    if request.method == 'POST':
        vehicle_no = request.form['vehicle_no']
        reserve_spot(user.u_id, spot.spot_id, lot_id, vehicle_no)
        return redirect('/user')
    return render_template("book_parking_spot.html", user=user, spot=spot)

def release_spot(booking_id):
    reservation = Reservation.query.get(booking_id)
    if reservation and not reservation.leaving_timestamp:
        spot = ParkingSpot.query.get(reservation.spot_id)
        lot = ParkingLot.query.get(spot.lot_id)
        now = datetime.utcnow()
        duration = (now - reservation.parking_timestamp).total_seconds() / 3600
        cost = round(duration * lot.price_per_hour, 2)
        reservation.leaving_timestamp = now
        reservation.total_cost = cost
        spot.status = 'A'  
        db.session.commit()

def get_release_details(booking_id):
    reservation = Reservation.query.get(booking_id)
    if reservation:
        spot = ParkingSpot.query.get(reservation.spot_id)
        lot = ParkingLot.query.get(spot.lot_id)
        ist = pytz.timezone('Asia/Kolkata')
        now = datetime.utcnow().replace(tzinfo=pytz.utc).astimezone(ist)
        parked_time = parked_time = reservation.parking_timestamp.replace(tzinfo=pytz.utc).astimezone(ist)
        duration = (now - parked_time).total_seconds() / 3600  
        cost = round(duration * lot.price_per_hour, 2)
        return {
                'spot_id': spot.spot_id,
                'vehicle_no': reservation.vehicle_no,
                'park_time': parked_time.strftime('%Y-%m-%d %H:%M:%S'),
                'release_time': now.strftime('%Y-%m-%d %H:%M:%S'),
                'cost': cost
               }
    return None
      
@app.route('/user/release/<int:booking_id>', methods=['GET', 'POST'])
def release_parking_spot(booking_id):
    data = get_release_details(booking_id)
    if request.method == 'POST':
        release_spot(booking_id)
        return redirect('/user')
    return render_template("release_parking_spot.html", data=data)

@app.route('/edit_profile', methods=['GET', 'POST'])
def edit_profile():
    user = get_current_user()
    if not user:
        flash("Please log in first.", "warning")
        return redirect(url_for('login'))
    if request.method == 'POST':
        name = request.form.get('name')
        address = request.form.get('address')
        pincode = request.form.get('pincode')
        password = request.form.get('password')
        if not name or not address or not pincode:
            flash("All fields except password are required.", "danger")
        else:
            user.name = name
            user.address = address
            user.pincode = pincode
            if password:
                user.password = generate_password_hash(password)
            try:
                db.session.commit()
                flash("Profile updated successfully!","success")
                return redirect(url_for('user_dashboard'))
            except Exception as e:
                db.session.rollback()
                flash(f"Error updating profile:{str(e)}","danger")
    return render_template('edit_profile.html', user=user)

@app.route('/user/summary')
def user_summary():
    if 'u_id' not in session:
        flash("Please log in to view summary", "warning")
        return redirect(url_for('login'))
    user_id = session['u_id']
    user = User.query.get(user_id) 
    reservations = Reservation.query.filter_by(user_id=user_id).all()
    total_bookings = len(reservations)
    total_spent = 0
    for r in reservations:
        if r.total_cost:
            total_spent=total_spent+r.total_cost
        else:
            total_spent=total_spent
    lot_usage = {}
    for r in reservations:
        lot = r.spot.lot
        if lot.lot_id not in lot_usage:
            lot_usage[lot.lot_id] = {
                'location': lot.prime_location_name,
                'count': 1
            }
        else:
            lot_usage[lot.lot_id]['count'] += 1
    return render_template('user_summary.html',
                           user=user, 
                           total_bookings=total_bookings,
                           total_spent=round(total_spent, 2),
                           lot_usage=lot_usage)

if __name__ == '__main__':
   app.run(debug=True)