# Advanced Search and Analytics Features

from urllib import request
import app
from sqlalchemy import func, text
from datetime import datetime, timedelta
import json
from flask import jsonify, session

from app import db  # Make sure 'db' is imported from your app module

# Import or define the admin_required decorator
from app.auth import admin_required  # Adjust the import path as needed
from app.auth import login_required  # Import login_required decorator

# Import your models here
from models import Product, Category, Order, OrderItem, User, Review, Coupon  # Adjust the import path as needed

# Search functionality
@app.route('/api/search')
def search_products():
    query = request.args.get('q', '').strip()
    category_id = request.args.get('category_id', type=int)
    min_price = request.args.get('min_price', type=float)
    max_price = request.args.get('max_price', type=float)
    sort_by = request.args.get('sort_by', 'relevance')
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    if not query:
        return jsonify({'error': 'Search query is required'}), 400
    
    # Build search query
    search_query = Product.query.filter(Product.is_available == True)
    
    # Text search across multiple fields
    search_terms = query.split()
    for term in search_terms:
        search_query = search_query.filter(
            db.or_(
                Product.name.ilike(f'%{term}%'),
                Product.description.ilike(f'%{term}%'),
                Product.brand.ilike(f'%{term}%')
            )
        )
    
    # Apply filters
    if category_id:
        search_query = search_query.filter(Product.category_id == category_id)
    
    if min_price is not None:
        search_query = search_query.filter(Product.price >= min_price)
    
    if max_price is not None:
        search_query = search_query.filter(Product.price <= max_price)
    
    # Apply sorting
    if sort_by == 'price_low':
        search_query = search_query.order_by(Product.price.asc())
    elif sort_by == 'price_high':
        search_query = search_query.order_by(Product.price.desc())
    elif sort_by == 'rating':
        # Sort by average rating (would need a subquery for exact implementation)
        search_query = search_query.order_by(Product.name.asc())
    elif sort_by == 'newest':
        search_query = search_query.order_by(Product.created_at.desc())
    else:  # relevance
        search_query = search_query.order_by(Product.name.asc())
    
    # Paginate results
    results = search_query.paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    # Log search query for analytics
    if 'user_id' in session:
        log_search_query(session['user_id'], query, len(results.items))
    
    return jsonify({
        'query': query,
        'results': [{
            'id': p.id,
            'name': p.name,
            'description': p.description,
            'price': p.price,
            'original_price': p.original_price,
            'image_url': p.image_url,
            'stock_quantity': p.stock_quantity,
            'unit': p.unit,
            'brand': p.brand,
            'category_name': p.category.name,
            'average_rating': p.average_rating,
            'review_count': p.review_count
        } for p in results.items],
        'pagination': {
            'page': results.page,
            'pages': results.pages,
            'per_page': results.per_page,
            'total': results.total,
            'has_next': results.has_next,
            'has_prev': results.has_prev
        }
    })

@app.route('/api/search/suggestions')
def search_suggestions():
    query = request.args.get('q', '').strip()
    limit = request.args.get('limit', 10, type=int)
    
    if len(query) < 2:
        return jsonify([])
    
    # Get product name suggestions
    products = Product.query.filter(
        Product.name.ilike(f'%{query}%'),
        Product.is_available == True
    ).limit(limit).all()
    
    suggestions = []
    for product in products:
        suggestions.append({
            'type': 'product',
            'text': product.name,
            'id': product.id,
            'category': product.category.name
        })
    
    # Get category suggestions
    categories = Category.query.filter(
        Category.name.ilike(f'%{query}%'),
        Category.is_active == True
    ).limit(5).all()
    
    for category in categories:
        suggestions.append({
            'type': 'category',
            'text': category.name,
            'id': category.id
        })
    
    return jsonify(suggestions[:limit])

# Analytics and reporting
class SearchLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    query = db.Column(db.String(200), nullable=False)
    results_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

def log_search_query(user_id, query, results_count):
    """Log search query for analytics"""
    search_log = SearchLog(
        user_id=user_id,
        query=query.lower(),
        results_count=results_count
    )
    db.session.add(search_log)
    db.session.commit()

@app.route('/api/admin/analytics/dashboard')
@admin_required
def analytics_dashboard():
    # Get date range
    days = request.args.get('days', 30, type=int)
    start_date = datetime.utcnow() - timedelta(days=days)
    
    # Sales analytics
    total_orders = Order.query.filter(Order.created_at >= start_date).count()
    total_revenue = db.session.query(func.sum(Order.total_amount)).filter(
        Order.created_at >= start_date,
        Order.payment_status == 'paid'
    ).scalar() or 0
    
    # Product analytics
    top_products = db.session.query(
        Product.name,
        func.sum(OrderItem.quantity).label('total_sold')
    ).join(OrderItem).join(Order).filter(
        Order.created_at >= start_date,
        Order.payment_status == 'paid'
    ).group_by(Product.id, Product.name).order_by(
        func.sum(OrderItem.quantity).desc()
    ).limit(10).all()
    
    # Category analytics
    category_sales = db.session.query(
        Category.name,
        func.sum(OrderItem.total).label('revenue')
    ).join(Product).join(OrderItem).join(Order).filter(
        Order.created_at >= start_date,
        Order.payment_status == 'paid'
    ).group_by(Category.id, Category.name).order_by(
        func.sum(OrderItem.total).desc()
    ).all()
    
    # User analytics
    new_users = User.query.filter(User.created_at >= start_date).count()
    active_users = db.session.query(func.count(func.distinct(Order.user_id))).filter(
        Order.created_at >= start_date
    ).scalar() or 0
    
    # Search analytics
    top_searches = db.session.query(
        SearchLog.query,
        func.count(SearchLog.id).label('search_count')
    ).filter(
        SearchLog.created_at >= start_date
    ).group_by(SearchLog.query).order_by(
        func.count(SearchLog.id).desc()
    ).limit(10).all()
    
    # Low stock products
    low_stock_products = Product.query.filter(
        Product.stock_quantity <= Product.min_stock_level,
        Product.is_available == True
    ).all()
    
    return jsonify({
        'period_days': days,
        'sales': {
            'total_orders': total_orders,
            'total_revenue': float(total_revenue),
            'average_order_value': float(total_revenue / total_orders) if total_orders > 0 else 0
        },
        'products': {
            'top_selling': [{'name': name, 'quantity_sold': int(qty)} for name, qty in top_products],
            'low_stock_count': len(low_stock_products),
            'low_stock_products': [{
                'id': p.id,
                'name': p.name,
                'current_stock': p.stock_quantity,
                'min_level': p.min_stock_level
            } for p in low_stock_products[:5]]
        },
        'categories': {
            'sales_by_category': [{'name': name, 'revenue': float(revenue)} for name, revenue in category_sales]
        },
        'users': {
            'new_users': new_users,
            'active_users': active_users
        },
        'search': {
            'top_searches': [{'query': query, 'count': int(count)} for query, count in top_searches]
        }
    })

# Reviews and ratings
@app.route('/api/reviews', methods=['POST'])
@login_required
def add_review():
    data = request.get_json()
    product_id = data.get('product_id')
    rating = data.get('rating')
    title = data.get('title', '')
    comment = data.get('comment', '')
    
    # Validate rating
    if not rating or rating < 1 or rating > 5:
        return jsonify({'error': 'Rating must be between 1 and 5'}), 400
    
    # Check if user has purchased this product
    has_purchased = db.session.query(OrderItem).join(Order).filter(
        Order.user_id == session['user_id'],
        OrderItem.product_id == product_id,
        Order.payment_status == 'paid'
    ).first() is not None
    
    # Check if user already reviewed this product
    existing_review = Review.query.filter_by(
        user_id=session['user_id'],
        product_id=product_id
    ).first()
    
    if existing_review:
        return jsonify({'error': 'You have already reviewed this product'}), 400
    
    review = Review(
        user_id=session['user_id'],
        product_id=product_id,
        rating=rating,
        title=title,
        comment=comment,
        is_verified_purchase=has_purchased
    )
    
    db.session.add(review)
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Review added successfully'})

@app.route('/api/products/<int:product_id>/reviews')
def get_product_reviews(product_id):
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    sort_by = request.args.get('sort_by', 'newest')
    
    query = Review.query.filter_by(product_id=product_id)
    
    if sort_by == 'oldest':
        query = query.order_by(Review.created_at.asc())
    elif sort_by == 'rating_high':
        query = query.order_by(Review.rating.desc())
    elif sort_by == 'rating_low':
        query = query.order_by(Review.rating.asc())
    else:  # newest
        query = query.order_by(Review.created_at.desc())
    
    reviews = query.paginate(page=page, per_page=per_page, error_out=False)
    
    return jsonify({
        'reviews': [{
            'id': r.id,
            'user_name': f"{r.user.first_name} {r.user.last_name[0]}." if r.user.last_name else r.user.first_name,
            'rating': r.rating,
            'title': r.title,
            'comment': r.comment,
            'is_verified_purchase': r.is_verified_purchase,
            'created_at': r.created_at.isoformat()
        } for r in reviews.items],
        'pagination': {
            'page': reviews.page,
            'pages': reviews.pages,
            'per_page': reviews.per_page,
            'total': reviews.total,
            'has_next': reviews.has_next,
            'has_prev': reviews.has_prev
        }
    })

# Coupon system
@app.route('/api/coupons/validate', methods=['POST'])
@login_required
def validate_coupon():
    data = request.get_json()
    coupon_code = data.get('coupon_code', '').upper()
    cart_total = data.get('cart_total', 0)
    
    coupon = Coupon.query.filter_by(code=coupon_code, is_active=True).first()
    
    if not coupon:
        return jsonify({'valid': False, 'message': 'Invalid coupon code'})
    
    if coupon.valid_until and coupon.valid_until < datetime.utcnow():
        return jsonify({'valid': False, 'message': 'Coupon has expired'})
    
    if coupon.usage_limit and coupon.used_count >= coupon.usage_limit:
        return jsonify({'valid': False, 'message': 'Coupon usage limit reached'})
    
    if cart_total < coupon.min_order_amount:
        return jsonify({
            'valid': False,
            'message': f'Minimum order amount is ${coupon.min_order_amount:.2f}'
        })
    
    # Calculate discount
    if coupon.discount_type == 'percentage':
        discount_amount = cart_total * (coupon.discount_value / 100)
        if coupon.max_discount_amount:
            discount_amount = min(discount_amount, coupon.max_discount_amount)
    else:  # fixed amount
        discount_amount = min(coupon.discount_value, cart_total)
    
    return jsonify({
        'valid': True,
        'discount_amount': discount_amount,
        'discount_type': coupon.discount_type,
        'discount_value': coupon.discount_value,
        'description': coupon.description
    })

print("Advanced search and analytics features loaded!")
print("New endpoints:")
print("- /api/search - Advanced product search")
print("- /api/search/suggestions - Search autocomplete")
print("- /api/admin/analytics/dashboard - Analytics dashboard")
print("- /api/reviews - Add product reviews")
print("- /api/products/<id>/reviews - Get product reviews")
print("- /api/coupons/validate - Validate coupon codes")