from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager, jwt_required, get_jwt_identity
import os

app = Flask(__name__)
CORS(app)

# -------------------------
# DATABASE CONFIG
# -------------------------
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise Exception("DATABASE_URL is missing!")

# Fix Railway postgres issue
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# -------------------------
# JWT CONFIG
# -------------------------
app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET")

# -------------------------
# INIT EXTENSIONS
# -------------------------
db = SQLAlchemy(app)
jwt = JWTManager(app)

# -------------------------
# MODEL
# -------------------------
class Property(db.Model):
    __tablename__ = 'properties'

    id = db.Column(db.Integer, primary_key=True)
    landlord_id = db.Column(db.Integer, nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    address = db.Column(db.String(300), nullable=False)
    city = db.Column(db.String(100), nullable=False)
    state = db.Column(db.String(100), nullable=False)
    country = db.Column(db.String(100), default='India')
    price_per_night = db.Column(db.Float, nullable=False)
    bedrooms = db.Column(db.Integer, default=1)
    bathrooms = db.Column(db.Integer, default=1)
    max_guests = db.Column(db.Integer, default=2)
    amenities = db.Column(db.Text)
    images = db.Column(db.Text)
    is_available = db.Column(db.Boolean, default=True)

    def to_dict(self):
        return {
            'id': self.id,
            'landlord_id': self.landlord_id,
            'title': self.title,
            'description': self.description,
            'address': self.address,
            'city': self.city,
            'state': self.state,
            'country': self.country,
            'price_per_night': self.price_per_night,
            'bedrooms': self.bedrooms,
            'bathrooms': self.bathrooms,
            'max_guests': self.max_guests,
            'amenities': self.amenities.split(',') if self.amenities else [],
            'images': self.images.split(',') if self.images else [],
            'is_available': self.is_available,
        }

# -------------------------
# ROUTES
# -------------------------
@app.route('/listings', methods=['GET'])
def get_listings():
    query = Property.query.filter_by(is_available=True)

    city = request.args.get('city')
    if city:
        query = query.filter(Property.city.ilike(f'%{city}%'))

    return jsonify({'listings': [p.to_dict() for p in query.all()]})


@app.route('/listings/<int:property_id>', methods=['GET'])
def get_listing(property_id):
    return jsonify(Property.query.get_or_404(property_id).to_dict())


@app.route('/listings', methods=['POST'])
@jwt_required()
def create_listing():
    landlord_id = get_jwt_identity()
    data = request.get_json()

    prop = Property(
        landlord_id=landlord_id,
        title=data['title'],
        address=data['address'],
        city=data['city'],
        state=data['state'],
        price_per_night=data['price_per_night']
    )

    db.session.add(prop)
    db.session.commit()

    return jsonify({'message': 'Created', 'listing': prop.to_dict()}), 201


@app.route('/health')
def health():
    return jsonify({'service': 'listings', 'status': 'healthy'})


# -------------------------
# CREATE TABLES
# -------------------------
with app.app_context():
    db.create_all()

# -------------------------
# RUN APP
# -------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
