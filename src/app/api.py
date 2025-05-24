from flask import Blueprint, jsonify, request, current_app
from src.app.models import Stock, Cluster, PriceHistory
from src.app import db
from sqlalchemy import func
import datetime
import os
import hashlib
import hmac
import time
import threading
import collections

# API TOKEN settings - in real application, get from config or environment file
API_SECRET = os.environ.get('API_SECRET', 'bist_profiling_secret_key_change_in_production')
TOKEN_EXPIRY = 3600  # 1 hour

# Rate limiting settings
RATE_LIMIT = 60  # Number of requests
RATE_PERIOD = 60  # Duration in seconds (1 minute)

# Request counter for each API key and IP
request_counts = collections.defaultdict(list)
request_lock = threading.Lock()

# API Blueprint
api_bp = Blueprint('api', __name__)

def generate_token(api_key, expires=None):
    """
    Generates HMAC-based API token
    """
    if expires is None:
        expires = int(time.time()) + TOKEN_EXPIRY
    
    # String formatted timestamp
    expires_str = str(expires)
    
    # Create HMAC-SHA256 signature
    signature = hmac.new(
        API_SECRET.encode('utf-8'),
        f"{api_key}:{expires_str}".encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    # Token format: api_key:expires:signature
    token = f"{api_key}:{expires_str}:{signature}"
    return token

def verify_token(token):
    """
    Verifies API token
    """
    try:
        # Split token components
        api_key, expires_str, signature = token.split(':')
        expires = int(expires_str)
        
        # Has the token expired?
        if expires < time.time():
            return False, "Token has expired"
        
        # Verify signature
        expected_signature = hmac.new(
            API_SECRET.encode('utf-8'),
            f"{api_key}:{expires_str}".encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        if signature != expected_signature:
            return False, "Invalid token signature"
            
        return True, api_key
    except Exception as e:
        return False, f"Token verification error: {str(e)}"

# Helper function for API key checking
def check_api_token():
    """
    Verifies API token, returns error if unsuccessful
    """
    # Check "Authorization: Bearer <token>" header
    auth_header = request.headers.get('Authorization', '')
    if not auth_header.startswith('Bearer '):
        return handle_api_error("Authorization header missing or invalid format (Bearer token required)", 401)
    
    token = auth_header[7:]  # Remove "Bearer " part
    is_valid, message = verify_token(token)
    
    if not is_valid:
        return handle_api_error(f"Token verification failed: {message}", 401)
    
    # Backward compatibility for original API key checking
    # New applications should only use tokens
    api_key = request.headers.get('API_KEY') or request.args.get('api_key')
    if api_key and api_key != os.environ.get('API_KEY', 'bist_profiling_api_key'):
        return handle_api_error("Invalid API key", 401)
    
    return None

# Rate Limiting function
def check_rate_limit(key):
    """
    Performs rate limiting check
    key: API key or IP address
    """
    now = time.time()
    
    with request_lock:
        # Clean expired records
        request_counts[key] = [t for t in request_counts[key] if t > now - RATE_PERIOD]
        
        # Current request count
        count = len(request_counts[key])
        
        # Is limit exceeded?
        if count >= RATE_LIMIT:
            return False, count
        
        # Record new request
        request_counts[key].append(now)
        return True, count

# Rate limiting decorator
def rate_limit(f):
    """
    Decorator for rate limiting
    """
    from functools import wraps
    
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Get API key or IP address
        auth_header = request.headers.get('Authorization', '')
        
        if auth_header.startswith('Bearer '):
            token = auth_header[7:]
            is_valid, api_key = verify_token(token)
            
            # If token is invalid, use IP address
            if not is_valid:
                key = request.remote_addr
            else:
                key = api_key
        else:
            # If no API key, use IP address
            key = request.remote_addr
        
        # Rate limit check
        is_allowed, count = check_rate_limit(key)
        
        if not is_allowed:
            response = jsonify({
                "error": "Rate limit exceeded",
                "limit": RATE_LIMIT,
                "period": RATE_PERIOD,
                "retry_after": RATE_PERIOD - (time.time() % RATE_PERIOD)
            })
            response.headers["Retry-After"] = str(int(RATE_PERIOD - (time.time() % RATE_PERIOD)))
            response.status_code = 429
            return response
        
        # Add rate limit headers
        response = f(*args, **kwargs)
        
        # If JsonResponse is returned
        if hasattr(response, 'headers'):
            response.headers["X-RateLimit-Limit"] = str(RATE_LIMIT)
            response.headers["X-RateLimit-Remaining"] = str(RATE_LIMIT - count - 1)
            response.headers["X-RateLimit-Reset"] = str(int(RATE_PERIOD - (time.time() % RATE_PERIOD)))
        
        return response
    
    return decorated_function

# Token creation endpoint
@api_bp.route('/token', methods=['POST'])
def get_token():
    """
    Creates token for API usage
    """
    api_key = request.headers.get('API_KEY') or request.json.get('api_key')
    
    if not api_key or api_key != os.environ.get('API_KEY', 'bist_profiling_api_key'):
        return handle_api_error("Invalid API key", 401)
    
    # Optional expiration time
    expires = request.json.get('expires')
    if expires:
        try:
            expires = int(expires)
        except ValueError:
            return handle_api_error("expires value must be a valid integer", 400)
    
    token = generate_token(api_key, expires)
    return api_response({
        "token": token,
        "expires": int(time.time()) + TOKEN_EXPIRY if not expires else expires,
        "type": "Bearer"
    })

@api_bp.route('/stocks', methods=['GET'])
@rate_limit
def get_stocks():
    """Returns all stocks."""
    # API key check
    auth_error = check_api_token()
    if auth_error:
        return auth_error
    
    stocks = db.session.query(Stock).all()
    
    result = []
    for stock in stocks:
        result.append({
            'id': stock.id,
            'code': stock.code,
            'name': stock.name,
            'avg_price': stock.avg_price,
            'volatility': stock.volatility,
            'avg_change': stock.avg_change,
            'beta': stock.beta,
            'risk_return_ratio': stock.risk_return_ratio,
            'cluster_id': stock.cluster_id,
            'cluster': {
                'id': stock.cluster.id,
                'name': stock.cluster.name,
                'color': stock.cluster.color
            }
        })
    
    return jsonify(result)

@api_bp.route('/stocks/<stock_code>', methods=['GET'])
@rate_limit
def get_stock(stock_code):
    """Returns details of a specific stock."""
    # API key check
    auth_error = check_api_token()
    if auth_error:
        return auth_error
    
    stock = db.session.query(Stock).filter_by(code=stock_code).first_or_404()
    
    # Get last 30 days price history
    end_date = datetime.date.today()
    start_date = end_date - datetime.timedelta(days=30)
    price_history = db.session.query(PriceHistory)\
        .filter(PriceHistory.stock_id == stock.id)\
        .filter(PriceHistory.date >= start_date)\
        .filter(PriceHistory.date <= end_date)\
        .order_by(PriceHistory.date).all()
    
    # Format price history
    price_data = {
        'dates': [ph.date.strftime('%d.%m.%Y') for ph in price_history],
        'prices': [ph.close_price for ph in price_history]
    }
    
    result = {
        'id': stock.id,
        'code': stock.code,
        'name': stock.name,
        'avg_price': stock.avg_price,
        'volatility': stock.volatility,
        'avg_change': stock.avg_change,
        'beta': stock.beta,
        'risk_return_ratio': stock.risk_return_ratio,
        'max_gain': stock.max_gain,
        'max_loss': stock.max_loss,
        'cluster_id': stock.cluster_id,
        'cluster': {
            'id': stock.cluster.id,
            'name': stock.cluster.name,
            'color': stock.cluster.color
        },
        'price_history': price_data
    }
    
    return jsonify(result)

@api_bp.route('/clusters', methods=['GET'])
@rate_limit
def get_clusters():
    """Returns all clusters."""
    # API key check
    auth_error = check_api_token()
    if auth_error:
        return auth_error
        
    clusters = db.session.query(Cluster).all()
    
    result = []
    for cluster in clusters:
        # Get stocks belonging to cluster
        stocks = db.session.query(Stock).filter_by(cluster_id=cluster.id).all()
        
        result.append({
            'id': cluster.id,
            'name': cluster.name,
            'color': cluster.color,
            'avg_volatility': cluster.avg_volatility,
            'avg_change': cluster.avg_change,
            'avg_beta': cluster.avg_beta,
            'risk_return_ratio': cluster.risk_return_ratio,
            'summary': cluster.summary,
            'investor_profile': cluster.investor_profile,
            'stocks': [stock.code for stock in stocks]
        })
    
    return jsonify(result)

@api_bp.route('/clusters/<int:cluster_id>', methods=['GET'])
@rate_limit
def get_cluster(cluster_id):
    """Returns details of a specific cluster."""
    # API key check
    auth_error = check_api_token()
    if auth_error:
        return auth_error
        
    cluster = db.session.query(Cluster).filter_by(id=cluster_id).first_or_404()
    
    # Get stocks belonging to cluster
    stocks = db.session.query(Stock).filter_by(cluster_id=cluster.id).all()
    
    result = {
        'id': cluster.id,
        'name': cluster.name,
        'color': cluster.color,
        'avg_volatility': cluster.avg_volatility,
        'avg_change': cluster.avg_change,
        'avg_beta': cluster.avg_beta,
        'risk_return_ratio': cluster.risk_return_ratio,
        'summary': cluster.summary,
        'investor_profile': cluster.investor_profile,
        'stocks': [{'code': stock.code, 'name': stock.name} for stock in stocks]
    }
    
    return jsonify(result)

@api_bp.route('/stats/overview', methods=['GET'])
@rate_limit
def get_overview_stats():
    """Returns general statistics."""
    # API key check
    auth_error = check_api_token()
    if auth_error:
        return auth_error
        
    # Average values
    avg_change = db.session.query(func.avg(Stock.avg_change)).scalar() or 0
    avg_volatility = db.session.query(func.avg(Stock.volatility)).scalar() or 0
    avg_beta = db.session.query(func.avg(Stock.beta)).scalar() or 0
    
    # Highest gain and loss
    max_gain_stock = db.session.query(Stock).order_by(Stock.max_gain.desc()).first()
    max_loss_stock = db.session.query(Stock).order_by(Stock.max_loss).first()
    
    # Total stock and cluster counts
    stock_count = db.session.query(func.count(Stock.id)).scalar() or 0
    cluster_count = db.session.query(func.count(Cluster.id)).scalar() or 0
    
    result = {
        'avg_change': avg_change,
        'avg_volatility': avg_volatility,
        'avg_beta': avg_beta,
        'max_gain': {
            'value': max_gain_stock.max_gain if max_gain_stock else 0,
            'stock_code': max_gain_stock.code if max_gain_stock else None
        },
        'max_loss': {
            'value': max_loss_stock.max_loss if max_loss_stock else 0,
            'stock_code': max_loss_stock.code if max_loss_stock else None
        },
        'stock_count': stock_count,
        'cluster_count': cluster_count,
        'last_update': datetime.date.today().strftime('%d.%m.%Y')
    }
    
    return jsonify(result)

def api_response(data, status=200, headers=None):
    """
    Creates standardized API response
    
    Args:
        data: Response data object
        status: HTTP status code
        headers: Optional HTTP headers
        
    Returns:
        Flask response object
    """
    response = jsonify(data)
    response.status_code = status
    
    # Add optional headers
    if headers:
        for key, value in headers.items():
            response.headers[key] = value
            
    return response

def handle_api_error(error_message, status_code=400):
    """
    Helper function for error responses
    
    Args:
        error_message: Error message
        status_code: HTTP status code
        
    Returns:
        Flask response object
    """
    return api_response({"error": error_message}, status=status_code)

# API key endpoint (requires authentication)
@api_bp.route('/auth/get-api-key', methods=['GET'])
def get_api_key():
    """
    Returns API key - In real application requires authentication
    """
    # User authentication should be performed
    # This is a simple example, should definitely not be done this way in real applications!
    # In a real application, API key should be user-specific and stored securely
    if 'user_id' in request.cookies:
        # We're simulating user authentication - in reality session control should be performed
        return api_response({
            "api_key": os.environ.get('API_KEY', 'bist_profiling_api_key')
        })
    else:
        return handle_api_error("Unauthorized", 401) 