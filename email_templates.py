# Email Templates for the Grocery Website

email_templates = {
    'verify_email.html': '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Verify Your Email</title>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: #4CAF50; color: white; padding: 20px; text-align: center; }
        .content { padding: 20px; background: #f9f9f9; }
        .button { display: inline-block; padding: 12px 24px; background: #4CAF50; color: white; text-decoration: none; border-radius: 4px; }
        .footer { text-align: center; padding: 20px; color: #666; font-size: 12px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Welcome indho snack bar!</h1>
        </div>
        <div class="content">
            <h2>Hi {{ user.first_name }},</h2>
            <p>Thank you for registering with our grocery store. To complete your registration, please verify your email address by clicking the button below:</p>
            <p style="text-align: center;">
                <a href="{{ url_for('verify_email', token=verification_token, _external=True) }}" class="button">Verify Email Address</a>
            </p>
            <p>If the button doesn't work, you can copy and paste this link into your browser:</p>
            <p>{{ url_for('verify_email', token=verification_token, _external=True) }}</p>
            <p>This verification link will expire in 24 hours.</p>
        </div>
        <div class="footer">
            <p>If you didn't create an account with us, please ignore this email.</p>
            <p>&copy; 2024 Grocery Store. All rights reserved.</p>
        </div>
    </div>
</body>
</html>
    ''',
    
    'order_confirmation.html': '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Order Confirmation</title>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: #4CAF50; color: white; padding: 20px; text-align: center; }
        .content { padding: 20px; }
        .order-details { background: #f9f9f9; padding: 15px; margin: 15px 0; border-radius: 4px; }
        .item { border-bottom: 1px solid #ddd; padding: 10px 0; }
        .total { font-weight: bold; font-size: 18px; color: #4CAF50; }
        .footer { text-align: center; padding: 20px; color: #666; font-size: 12px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Order Confirmation</h1>
            <p>Order #{{ order.order_number }}</p>
        </div>
        <div class="content">
            <h2>Hi {{ user.first_name }},</h2>
            <p>Thank you for your order! We've received your order and it's being processed.</p>
            
            <div class="order-details">
                <h3>Order Details:</h3>
                <p><strong>Order Number:</strong> {{ order.order_number }}</p>
                <p><strong>Order Date:</strong> {{ order.created_at.strftime('%B %d, %Y at %I:%M %p') }}</p>
                <p><strong>Delivery Address:</strong> {{ order.delivery_address }}</p>
                {% if order.delivery_date %}
                <p><strong>Delivery Date:</strong> {{ order.delivery_date.strftime('%B %d, %Y') }}</p>
                {% endif %}
                {% if order.delivery_time_slot %}
                <p><strong>Delivery Time:</strong> {{ order.delivery_time_slot }}</p>
                {% endif %}
            </div>
            
            <div class="order-details">
                <h3>Items Ordered:</h3>
                {% for item in order.order_items %}
                <div class="item">
                    <p><strong>{{ item.product.name }}</strong></p>
                    <p>Quantity: {{ item.quantity }} × ${{ "%.2f"|format(item.price) }} = ${{ "%.2f"|format(item.total) }}</p>
                </div>
                {% endfor %}
                
                <div style="margin-top: 15px; padding-top: 15px; border-top: 2px solid #4CAF50;">
                    <p>Subtotal: ${{ "%.2f"|format(order.total_amount - order.tax_amount - order.delivery_fee + order.discount_amount) }}</p>
                    {% if order.discount_amount > 0 %}
                    <p>Discount: -${{ "%.2f"|format(order.discount_amount) }}</p>
                    {% endif %}
                    <p>Tax: ${{ "%.2f"|format(order.tax_amount) }}</p>
                    <p>Delivery Fee: ${{ "%.2f"|format(order.delivery_fee) }}</p>
                    <p class="total">Total: ${{ "%.2f"|format(order.total_amount) }}</p>
                </div>
            </div>
            
            <p>We'll send you another email when your order is ready for delivery.</p>
            <p>You can track your order status by logging into your account on our website.</p>
        </div>
        <div class="footer">
            <p>Thank you for shopping with us!</p>
            <p>&copy; 2024 Grocery Store. All rights reserved.</p>
        </div>
    </div>
</body>
</html>
    ''',
    
    'low_stock_alert.html': '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Low Stock Alert</title>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: #ff9800; color: white; padding: 20px; text-align: center; }
        .content { padding: 20px; }
        .alert { background: #fff3cd; border: 1px solid #ffeaa7; padding: 15px; border-radius: 4px; margin: 15px 0; }
        .footer { text-align: center; padding: 20px; color: #666; font-size: 12px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>⚠️ Low Stock Alert</h1>
        </div>
        <div class="content">
            <div class="alert">
                <h3>{{ product.name }}</h3>
                <p><strong>Current Stock:</strong> {{ product.stock_quantity }} {{ product.unit }}</p>
                <p><strong>Minimum Level:</strong> {{ product.min_stock_level }} {{ product.unit }}</p>
                <p><strong>Category:</strong> {{ product.category.name }}</p>
                <p><strong>Brand:</strong> {{ product.brand or 'N/A' }}</p>
            </div>
            <p>This product is running low on stock and needs to be restocked soon.</p>
            <p>Please update the inventory as soon as possible to avoid stockouts.</p>
        </div>
        <div class="footer">
            <p>Grocery Store Inventory Management System</p>
        </div>
    </div>
</body>
</html>
    '''
}

# Save email templates to files
import os

def create_email_templates():
    """Create email template files"""
    templates_dir = 'templates/emails'
    if not os.path.exists(templates_dir):
        os.makedirs(templates_dir)
    
    for filename, content in email_templates.items():
        filepath = os.path.join(templates_dir, filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
    
    print(f"Created {len(email_templates)} email templates in {templates_dir}/")

# Additional utility functions for email management
from models import Newsletter, User, Order  # Make sure this import matches your project structure

# Import or define send_email function
# Define a dummy send_email function if utils.email_utils is not available
def send_email(to, subject, template, **kwargs):
    print(f"Sending email to {to} with subject '{subject}' using template '{template}' and context {kwargs}")

def send_newsletter(subject, content, recipient_list=None):
    """Send newsletter to subscribers"""
    if recipient_list is None:
        subscribers = Newsletter.query.filter_by(is_active=True).all()
        recipient_list = [sub.email for sub in subscribers]
    
    for email in recipient_list:
        send_email(email, subject, 'newsletter.html', content=content)
    
    return len(recipient_list)

def send_order_status_update(order_id, new_status):
    """Send order status update email"""
    order = Order.query.get(order_id)
    if order:
        user = User.query.get(order.user_id)
        send_email(
            user.email,
            f'Order Update - {order.order_number}',
            'order_status_update.html',
            user=user,
            order=order,
            new_status=new_status
        )

def send_welcome_email(user_id):
    """Send welcome email to new users"""
    user = User.query.get(user_id)
    if user:
        send_email(
            user.email,
            'Welcome to Our Grocery Store!',
            'welcome_email.html',
            user=user
        )

print("Email templates and utilities created!")
print("Templates available:")
for template_name in email_templates.keys():
    print(f"- {template_name}")