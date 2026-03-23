from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager, jwt_required, get_jwt_identity
from datetime import datetime, date
import os
import requests

app = Flask(__name__)
CORS(app)

# ---------------- DB CONFIG ----------------

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise Exception("DATABASE_URL is missing!")

# Fix Railway postgres issue
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# ---------------- JWT ----------------

app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET", "dev-secret")
jwt = JWTManager(app)

# ---------------- SERVICE URLS ----------------

LISTINGS_SERVICE_URL = os.getenv('LISTINGS_SERVICE_URL')
PAYMENTS_SERVICE_URL = os.getenv('PAYMENTS_SERVICE_URL')

# ---------------- MODEL ----------------

class Booking(db.Model):
    __tablename__ = 'bookings'

    id          = db.Column(db.Integer, primary_key=True)
    tenant_id   = db.Column(db.Integer, nullable=False)
    property_id = db.Column(db.Integer, nullable=False)
    check_in    = db.Column(db.Date, nullable=False)
    check_out   = db.Column(db.Date, nullable=False)
    guests      = db.Column(db.Integer, default=1)
    total_price = db.Column(db.Float, nullable=False)
    status      = db.Column(db.String(20), default='pending')
    payment_id  = db.Column(db.String(100))
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'tenant_id': self.tenant_id,
            'property_id': self.property_id,
            'check_in': self.check_in.isoformat(),
            'check_out': self.check_out.isoformat(),
            'guests': self.guests,
            'total_price': self.total_price,
            'status': self.status,
            'payment_id': self.payment_id,
            'created_at': self.created_at.isoformat(),
        }

# ---------------- HELPERS ----------------

def get_listing(property_id):
    try:
        resp = requests.get(f'{LISTINGS_SERVICE_URL}/listings/{property_id}', timeout=5)
        if resp.status_code == 200:
            return resp.json()
    except Exception:
        pass
    return None

def has_date_conflict(property_id, check_in, check_out, exclude_id=None):
    query = Booking.query.filter(
        Booking.property_id == property_id,
        Booking.status != 'cancelled',
        Booking.check_in < check_out,
        Booking.check_out > check_in,
    )
    if exclude_id:
        query = query.filter(Booking.id != exclude_id)
    return query.first() is not None

# ---------------- ROUTES ----------------

@app.route('/bookings', methods=['POST'])
@jwt_required()
def create_booking():
    tenant_id = int(get_jwt_identity())
    data = request.get_json()

    check_in  = date.fromisoformat(data['check_in'])
    check_out = date.fromisoformat(data['check_out'])

    listing = get_listing(data['property_id'])
    if not listing:
        return jsonify({'error': 'Property not found'}), 404

    nights = (check_out - check_in).days
    total_price = nights * listing['price_per_night']

    booking = Booking(
        tenant_id=tenant_id,
        property_id=data['property_id'],
        check_in=check_in,
        check_out=check_out,
        guests=data['guests'],
        total_price=total_price,
    )

    db.session.add(booking)
    db.session.commit()

    return jsonify({'booking': booking.to_dict()}), 201

@app.route('/bookings', methods=['GET'])
def get_bookings():
    bookings = Booking.query.all()
    return jsonify({'bookings': [b.to_dict() for b in bookings]})

@app.route('/health')
def health():
    return jsonify({'service': 'bookings', 'status': 'healthy'})

# ---------------- INIT DB ----------------

with app.app_context():
    db.create_all()

# ---------------- RUN ----------------

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8000))
    app.run(host='0.0.0.0', port=port)
