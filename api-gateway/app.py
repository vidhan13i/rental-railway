from flask import Flask, jsonify, request, Response
from flask_cors import CORS
import requests
import os

app = Flask(__name__)

# ✅ CORS FIX (GLOBAL)
CORS(app, supports_credentials=True)

@app.after_request
def after_request(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, PATCH, OPTIONS'
    return response


# ✅ HANDLE ALL PREFLIGHT REQUESTS
@app.route('/', defaults={'path': ''}, methods=['OPTIONS'])
@app.route('/<path:path>', methods=['OPTIONS'])
def options_handler(path):
    return '', 200


# ✅ SERVICES (NO DEFAULT FALLBACK)
SERVICES = {
    'users': os.getenv('USERS_SERVICE_URL'),
    'listings': os.getenv('LISTINGS_SERVICE_URL'),
    'bookings': os.getenv('BOOKINGS_SERVICE_URL'),
    'payments': os.getenv('PAYMENTS_SERVICE_URL'),
    'reviews': os.getenv('REVIEWS_SERVICE_URL'),
}


# 🚀 PROXY FUNCTION
def proxy(service_name, path):
    service_url = SERVICES.get(service_name)

    if not service_url:
        return jsonify({'error': f'{service_name} URL not configured'}), 500

    target_url = f"{service_url}{path}"

    if request.query_string:
        target_url += f"?{request.query_string.decode()}"

    # ✅ SAFE HEADERS
    headers = {
        key: value
        for key, value in request.headers
        if key.lower() not in ['host', 'content-length']
    }

    try:
        resp = requests.request(
            method=request.method,
            url=target_url,
            headers=headers,
            json=request.get_json(silent=True),
            timeout=10,
        )

        return Response(
            resp.content,
            status=resp.status_code,
            content_type=resp.headers.get('Content-Type', 'application/json')
        )

    except requests.exceptions.ConnectionError:
        return jsonify({'error': f'{service_name} service is unavailable'}), 503

    except requests.exceptions.Timeout:
        return jsonify({'error': f'{service_name} service timed out'}), 504


# ===================== ROUTES ===================== #

# USERS
@app.route('/users', methods=['GET', 'POST', 'OPTIONS'])
@app.route('/users/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS'])
def users_routes(path=''):
    if request.method == 'OPTIONS':
        return '', 200
    return proxy('users', f'/users/{path}' if path else '/users')


# LISTINGS
@app.route('/listings', methods=['GET', 'POST', 'OPTIONS'])
@app.route('/listings/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS'])
def listings_routes(path=''):
    if request.method == 'OPTIONS':
        return '', 200
    return proxy('listings', f'/listings/{path}' if path else '/listings')


# BOOKINGS
@app.route('/bookings', methods=['GET', 'POST', 'OPTIONS'])
@app.route('/bookings/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS'])
def bookings_routes(path=''):
    if request.method == 'OPTIONS':
        return '', 200
    return proxy('bookings', f'/bookings/{path}' if path else '/bookings')


# PAYMENTS (optional)
@app.route('/payments', methods=['GET', 'POST', 'OPTIONS'])
@app.route('/payments/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS'])
def payments_routes(path=''):
    if request.method == 'OPTIONS':
        return '', 200
    return proxy('payments', f'/payments/{path}' if path else '/payments')


# REVIEWS (optional)
@app.route('/reviews', methods=['GET', 'POST', 'OPTIONS'])
@app.route('/reviews/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS'])
def reviews_routes(path=''):
    if request.method == 'OPTIONS':
        return '', 200
    return proxy('reviews', f'/reviews/{path}' if path else '/reviews')


# ===================== HEALTH ===================== #

@app.route('/health')
def health():
    results = {}

    for name, url in SERVICES.items():
        if not url:
            results[name] = 'not configured'
            continue

        try:
            resp = requests.get(f'{url}/health', timeout=3)
            results[name] = 'healthy' if resp.status_code == 200 else 'unhealthy'
        except Exception:
            results[name] = 'unreachable'

    overall = 'healthy' if all(v == 'healthy' for v in results.values() if v != 'not configured') else 'degraded'

    return jsonify({
        'gateway': 'healthy',
        'services': results,
        'overall': overall
    })


# ROOT
@app.route('/')
def home():
    return {"message": "API Gateway running"}


# ===================== RUN ===================== #

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
