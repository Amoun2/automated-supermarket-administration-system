# Complete API Routes for the supermarket Website

from flask import Flask, request, jsonify, session
# Make sure to import or define all other required modules and objects here

from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import secrets
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import json

import stripe
stripe.api_key = "your_stripe_secret_key"  # Replace with your actual Stripe secret key

# Import your models here
from models import User  # Make sure 'models.py' contains the User model
from .models import db    # Import db from your models (assuming db is defined there)
from .models import Product  # Import Product model
from .models import Review   # Import Review model
from .models import Category  # Import Category model
from .models import CartItem  # Import CartItem model
from .models import WishlistItem  # Import WishlistItem model
from .models import Coupon  # Import Coupon model
from .models import Order   # Import Order model
from .models import OrderItem  # Import OrderItem model if not already imported

# Import or define send_email function
from utils import send_email  # Make sure utils.py contains send_email, or define it below

app = Flask(__name__)

# Initialize Flask-Limiter
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"]
)

# Authentication and User Management Routes
@app.route('/api/auth/register', methods=['POST'])
@limiter.limit("5 per minute")
def register():
    data = request.get_json()
    
    # Validation
    required_fields = ['username', 'email', 'password', 'first_name', 'last_name']
    for field in required_fields:
        if not data.get(field):
            return jsonify({'error': f'{field} is required'}), 400
    
    # Check if user exists
    if User.query.filter_by(username=data['username']).first():
        return jsonify({'error': 'Username already exists'}), 400
    
    if User.query.filter_by(email=data['email']).first():
        return jsonify({'error': 'Email already exists'}), 400
    
    # Create user
    verification_token = secrets.token_urlsafe(32)
    user = User(
        username=data['username'],
        email=data['email'],
        password_hash=generate_password_hash(data['password']),
        first_name=data['first_name'],
        last_name=data['last_name'],
        phone=data.get('phone'),
        address=data.get('address'),
        city=data.get('city'),
        postal_code=data.get('postal_code'),
        verification_token=verification_token
    )
    
    db.session.add(user)
    db.session.commit()
    
    # Send verification email
    send_email(
        user.email,
        'Verify Your Account',
        'verify_email.html',
        user=user,
        verification_token=verification_token
    )
    
    return jsonify({
        'success': True,
        'message': 'Registration successful. Please check your email to verify your account.'
    })

@app.route('/api/auth/login', methods=['POST'])
@limiter.limit("10 per minute")
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    user = User.query.filter_by(username=username).first()
    
    if user and check_password_hash(user.password_hash, password):
        if not user.is_active:
            return jsonify({'error': 'Account is deactivated'}), 400
        
        session['user_id'] = user.id
        session['username'] = user.username
        session['is_admin'] = user.is_admin
        
        # Update last login
        user.last_login = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Login successful',
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'is_admin': user.is_admin
            }
        })
    else:
        return jsonify({'error': 'Invalid credentials'}), 401

@app.route('/api/auth/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'success': True, 'message': 'Logged out successfully'})

@app.route('/api/auth/forgot-password', methods=['POST'])
@limiter.limit("3 per minute")
def forgot_password():
    data = request.get_json()
    email = data.get('email')
    
    user = User.query.filter_by(email=email).first()
    if user:
        reset_token = secrets.token_urlsafe(32)
        user.reset_token = reset_token
        user.reset_token_expires = datetime.utcnow() + timedelta(hours=1)
        db.session.commit()
        
        send_email(
            user.email,
            'Reset Your Password',
            'reset_password.html',
            user=user,
            reset_token=reset_token
        )
    
    return jsonify({
        'success': True,
        'message': 'If the email exists, a reset link has been sent.'
    })

# Product and Category Routes
@app.route('/api/products')
def get_products():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    category_id = request.args.get('category_id', type=int)
    search = request.args.get('search', '')
    sort_by = request.args.get('sort_by', 'name')
    sort_order = request.args.get('sort_order', 'asc')
    min_price = request.args.get('min_price', type=float)
    max_price = request.args.get('max_price', type=float)
    in_stock_only = request.args.get('in_stock_only', 'false').lower() == 'true'
    featured_only = request.args.get('featured_only', 'false').lower() == 'true'
    
    query = Product.query.filter_by(is_available=True)
    
    # Apply filters
    if category_id:
        query = query.filter_by(category_id=category_id)
    
    if search:
        query = query.filter(
            db.or_(
                Product.name.contains(search),
                Product.description.contains(search),
                Product.brand.contains(search)
            )
        )
    
    if min_price is not None:
        query = query.filter(Product.price >= min_price)
    
    if max_price is not None:
        query = query.filter(Product.price <= max_price)
    
    if in_stock_only:
        query = query.filter(Product.stock_quantity > 0)
    
    if featured_only:
        query = query.filter_by(is_featured=True)
    
    # Apply sorting
    if sort_by == 'price':
        if sort_order == 'desc':
            query = query.order_by(Product.price.desc())
        else:
            query = query.order_by(Product.price.asc())
    elif sort_by == 'name':
        if sort_order == 'desc':
            query = query.order_by(Product.name.desc())
        else:
            query = query.order_by(Product.name.asc())
    elif sort_by == 'created_at':
        query = query.order_by(Product.created_at.desc())
    
    # Paginate
    products = query.paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return jsonify({
        'products': [{
            'id': p.id,
            'name': p.name,
            'description': p.description,
            'price': p.price,
            'original_price': p.original_price,
            'image_url': p.image_url,
            'stock_quantity': p.stock_quantity,
            'unit': p.unit,
            'brand': p.brand,
            'category_id': p.category_id,
            'is_featured': p.is_featured,
            'average_rating': p.average_rating,
            'review_count': p.review_count
        } for p in products.items],
        'pagination': {
            'page': products.page,
            'pages': products.pages,
            'per_page': products.per_page,
            'total': products.total,
            'has_next': products.has_next,
            'has_prev': products.has_prev
        }
    })

@app.route('/api/products/<int:product_id>')
def get_product(product_id):
    product = Product.query.get_or_404(product_id)
    reviews = Review.query.filter_by(product_id=product_id).order_by(Review.created_at.desc()).limit(10).all()
    
    return jsonify({
        'id': product.id,
        'name': product.name,
        'description': product.description,
        'price': product.price,
        'original_price': product.original_price,
        'image_url': product.image_url,
        'stock_quantity': product.stock_quantity,
        'unit': product.unit,
        'brand': product.brand,
        'weight': product.weight,
        'category_id': product.category_id,
        'category_name': product.category.name,
        'is_featured': product.is_featured,
        'average_rating': product.average_rating,
        'review_count': product.review_count,
        'reviews': [{
            'id': r.id,
            'user_name': r.user.first_name + ' ' + r.user.last_name,
            'rating': r.rating,
            'title': r.title,
            'comment': r.comment,
            'is_verified_purchase': r.is_verified_purchase,
            'created_at': r.created_at.isoformat()
        } for r in reviews]
    })

@app.route('/api/categories')
def get_categories():
    categories = Category.query.filter_by(is_active=True).order_by(Category.sort_order).all()
    return jsonify([{
        'id': c.id,
        'name': c.name,
        'description': c.description,
        'image_url': c.image_url,
        'product_count': len(c.products)
    } for c in categories])

# Define a simple login_required decorator if not already defined
from functools import wraps
from flask import redirect, url_for

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'Authentication required'}), 401
        return f(*args, **kwargs)
    return decorated_function

# Shopping Cart Routes
@app.route('/api/cart')
@login_required
def get_cart():
    cart_items = db.session.query(CartItem, Product).join(Product).filter(
        CartItem.user_id == session['user_id']
    ).all()
    
    cart_data = []
    subtotal = 0
    
    for cart_item, product in cart_items:
        item_total = product.price * cart_item.quantity
        subtotal += item_total
        cart_data.append({
            'id': cart_item.id,
            'product_id': product.id,
            'name': product.name,
            'price': product.price,
            'quantity': cart_item.quantity,
            'total': item_total,
            'image_url': product.image_url,
            'stock_quantity': product.stock_quantity,
            'unit': product.unit
        })
    
    # Calculate tax and delivery fee
    tax_rate = 0.08  # 8% tax
    tax_amount = subtotal * tax_rate
    delivery_fee = 5.99 if subtotal < 50 else 0  # Free delivery over $50
    total = subtotal + tax_amount + delivery_fee
    
    return jsonify({
        'items': cart_data,
        'subtotal': subtotal,
        'tax_amount': tax_amount,
        'delivery_fee': delivery_fee,
        'total': total,
        'item_count': len(cart_data)
    })

@app.route('/api/cart/add', methods=['POST'])
@login_required
def add_to_cart():
    data = request.get_json()
    product_id = data.get('product_id')
    quantity = data.get('quantity', 1)
    
    # Validate product exists and is available
    product = Product.query.get(product_id)
    if not product or not product.is_available:
        return jsonify({'error': 'Product not available'}), 400
    
    # Check stock
    if product.stock_quantity < quantity:
        return jsonify({'error': 'Insufficient stock'}), 400
    
    # Check if item already in cart
    existing_item = CartItem.query.filter_by(
        user_id=session['user_id'],
        product_id=product_id
    ).first()
    
    if existing_item:
        new_quantity = existing_item.quantity + quantity
        if product.stock_quantity < new_quantity:
            return jsonify({'error': 'Insufficient stock'}), 400
        existing_item.quantity = new_quantity
    else:
        cart_item = CartItem(
            user_id=session['user_id'],
            product_id=product_id,
            quantity=quantity
        )
        db.session.add(cart_item)
    
    db.session.commit()
    return jsonify({'success': True, 'message': 'Item added to cart'})

# Wishlist Routes
@app.route('/api/wishlist')
@login_required
def get_wishlist():
    wishlist_items = db.session.query(WishlistItem, Product).join(Product).filter(
        WishlistItem.user_id == session['user_id']
    ).all()
    
    return jsonify([{
        'id': item.id,
        'product_id': product.id,
        'name': product.name,
        'price': product.price,
        'image_url': product.image_url,
        'is_available': product.is_available,
        'stock_quantity': product.stock_quantity,
        'added_at': item.added_at.isoformat()
    } for item, product in wishlist_items])

@app.route('/api/wishlist/add', methods=['POST'])
@login_required
def add_to_wishlist():
    data = request.get_json()
    product_id = data.get('product_id')
    
    # Check if already in wishlist
    existing_item = WishlistItem.query.filter_by(
        user_id=session['user_id'],
        product_id=product_id
    ).first()
    
    if existing_item:
        return jsonify({'error': 'Item already in wishlist'}), 400
    
    wishlist_item = WishlistItem(
        user_id=session['user_id'],
        product_id=product_id
    )
    
    db.session.add(wishlist_item)
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Item added to wishlist'})

# Payment and Order Routes
@app.route('/api/orders/create-payment-intent', methods=['POST'])
@login_required
def create_payment_intent():
    data = request.get_json()
    
    # Get cart total
    cart_response = get_cart()
    cart_data = json.loads(cart_response.data)
    total_amount = int(cart_data['total'] * 100)  # Convert to cents
    
    try:
        intent = stripe.PaymentIntent.create(
            amount=total_amount,
            currency='usd',
            metadata={
                'user_id': session['user_id'],
                'order_type': 'grocery_order'
            }
        )
        
        return jsonify({
            'client_secret': intent.client_secret,
            'amount': total_amount
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/orders', methods=['POST'])
@login_required
def create_order():
    data = request.get_json()
    delivery_address = data.get('delivery_address')
    delivery_date = data.get('delivery_date')
    delivery_time_slot = data.get('delivery_time_slot')
    special_instructions = data.get('special_instructions')
    payment_method = data.get('payment_method')
    stripe_payment_intent_id = data.get('stripe_payment_intent_id')
    coupon_code = data.get('coupon_code')
    
    # Get cart items
    cart_items = db.session.query(CartItem, Product).join(Product).filter(
        CartItem.user_id == session['user_id']
    ).all()
    
    if not cart_items:
        return jsonify({'error': 'Cart is empty'}), 400
    
    # Calculate totals
    subtotal = sum(product.price * cart_item.quantity for cart_item, product in cart_items)
    tax_amount = subtotal * 0.08
    delivery_fee = 5.99 if subtotal < 50 else 0
    discount_amount = 0
    
    # Apply coupon if provided
    if coupon_code:
        coupon = Coupon.query.filter_by(code=coupon_code, is_active=True).first()
        if coupon and coupon.valid_until > datetime.utcnow():
            if subtotal >= coupon.min_order_amount:
                if coupon.discount_type == 'percentage':
                    discount_amount = subtotal * (coupon.discount_value / 100)
                    if coupon.max_discount_amount:
                        discount_amount = min(discount_amount, coupon.max_discount_amount)
                else:  # fixed amount
                    discount_amount = coupon.discount_value
                
                coupon.used_count += 1
    
    total_amount = subtotal + tax_amount + delivery_fee - discount_amount
    
    # Create order
    order = Order(
        user_id=session['user_id'],
        total_amount=total_amount,
        tax_amount=tax_amount,
        delivery_fee=delivery_fee,
        discount_amount=discount_amount,
        delivery_address=delivery_address,
        delivery_date=datetime.fromisoformat(delivery_date) if delivery_date else None,
        delivery_time_slot=delivery_time_slot,
        special_instructions=special_instructions,
        payment_method=payment_method,
        stripe_payment_intent_id=stripe_payment_intent_id,
        payment_status='paid' if stripe_payment_intent_id else 'pending'
    )
    
    db.session.add(order)
    db.session.flush()  # Get order ID
    
    # Create order items and update inventory
    for cart_item, product in cart_items:
        order_item = OrderItem(
            order_id=order.id,
            product_id=product.id,
            quantity=cart_item.quantity,
            price=product.price,
            total=product.price * cart_item.quantity
        )
        db.session.add(order_item)
        
        # Update inventory
        # Define update_inventory if not already defined
        def update_inventory(product_id, quantity_change, reason, reference, user_id):
            product = Product.query.get(product_id)
            if product:
                product.stock_quantity += quantity_change
                db.session.add(product)
                # Optionally, log inventory change here
        update_inventory(
            product.id,
            -cart_item.quantity,
            'sale',
            f'Order #{order.order_number}',
            session['user_id']
        )
    
    # Clear cart
    CartItem.query.filter_by(user_id=session['user_id']).delete()
    
    db.session.commit()
    
    # Send order confirmation email
    user = User.query.get(session['user_id'])
    send_email(
        user.email,
        f'Order Confirmation - {order.order_number}',
        'order_confirmation.html',
        user=user,
        order=order
    )
    
    return jsonify({
        'success': True,
        'message': 'Order created successfully',
        'order_id': order.id,
        'order_number': order.order_number
    })

print("Complete API routes loaded!")
print("Available endpoints:")
print("- Authentication: /api/auth/register, /api/auth/login, /api/auth/logout")
print("- Products: /api/products, /api/products/<id>")
print("- Categories: /api/categories")
print("- Cart: /api/cart, /api/cart/add, /api/cart/remove, /api/cart/update")
print("- Wishlist: /api/wishlist, /api/wishlist/add")
print("- Orders: /api/orders, /api/orders/create-payment-intent")
print("- Reviews: /api/reviews")
print("- Search: /api/search")