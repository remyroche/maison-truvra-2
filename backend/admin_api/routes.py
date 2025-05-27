# backend/admin_api/routes.py
from flask import Blueprint, request, jsonify, current_app, g, send_file
import sqlite3
import os
import datetime
from ..database import get_db
from ..auth.routes import admin_required # Decorator from auth_bp
from ..utils import log_error, is_valid_email # Assuming you have these
# New Imports
from ..email_utils import send_b2b_approval_email # Placeholder for email sending
from ..services.audit_service import AuditLogService # Placeholder for audit logging
# Import the invoice generation function and calculation
from ...generate_professional_invoice import generate_invoice_pdf, calculate_invoice_totals # Adjusted path assuming generate_professional_invoice.py is in the root
from werkzeug.utils import secure_filename # For file uploads

admin_api_bp = Blueprint('admin_api_bp', __name__)

ALLOWED_EXTENSIONS = {'pdf'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Helper to get full URL for static assets
def get_static_url(filename, dir_name):
    if not filename:
        return None
    # Constructs URL like /static_assets/dir_name/filename
    return url_for('static', filename=os.path.join(dir_name, filename), _external=True)

@admin_api_bp_for_app.route('/products', methods=['POST'])
@admin_required
def create_product():
    data = request.form.to_dict()
    current_app.logger.info(f"Received data for new product: {data}")

    required_fields = ['name_fr', 'name_en', 'sku', 'category_fr', 'category_en', 'base_price']
    for field in required_fields:
        if field not in data or not data[field]:
            return jsonify({'success': False, 'message': f'Missing required field: {field}'}), 400

    try:
        base_price = float(data['base_price'])
        initial_stock_quantity = int(data.get('initial_stock_quantity', 0))
    except ValueError:
        return jsonify({'success': False, 'message': 'Invalid number format for price or stock.'}), 400

    new_product = Product(
        name_fr=data['name_fr'], name_en=data['name_en'],
        description_fr=data.get('description_fr'), description_en=data.get('description_en'),
        sku=data['sku'], category_fr=data['category_fr'], category_en=data['category_en'],
        base_price=base_price if not data.get('has_variants') == 'true' else None, # Nullify if has variants
        is_featured=data.get('is_featured') == 'true',
        is_active=data.get('is_active', 'true') == 'true', # Default to active
        meta_title_fr=data.get('meta_title_fr'), meta_title_en=data.get('meta_title_en'),
        meta_description_fr=data.get('meta_description_fr'), meta_description_en=data.get('meta_description_en'),
        slug_fr=data.get('slug_fr'), slug_en=data.get('slug_en'),
        species_fr=data.get('species_fr'), species_en=data.get('species_en'),
        origin_fr=data.get('origin_fr'), origin_en=data.get('origin_en'),
        quality_grade_fr=data.get('quality_grade_fr'), quality_grade_en=data.get('quality_grade_en'),
        nett_weight_g=data.get('nett_weight_g', type=int),
        harvest_date=datetime.strptime(data['harvest_date'], '%Y-%m-%d').date() if data.get('harvest_date') else None,
        best_before_date=datetime.strptime(data['best_before_date'], '%Y-%m-%d').date() if data.get('best_before_date') else None,
        has_variants=data.get('has_variants') == 'true',
        generate_assets_on_update = data.get('generate_assets_on_update', 'true') == 'true'
    )

    # Handle image uploads (main and thumbnail)
    uploaded_image_paths = []
    uploaded_thumb_paths = []

    if 'images' in request.files:
        for file in request.files.getlist('images'):
            if file and file.filename != '':
                filename = secure_filename(file.filename)
                # Save to a main images directory, e.g., static_assets/products/main/
                # This path needs to be configured and directory created
                main_image_dir_name = 'products/main'
                save_dir = os.path.join(current_app.static_folder, main_image_dir_name)
                if not os.path.exists(save_dir):
                    os.makedirs(save_dir)
                file_path = os.path.join(save_dir, filename)
                file.save(file_path)
                uploaded_image_paths.append(os.path.join(main_image_dir_name, filename)) # Store relative path for URL

    if 'thumbnails' in request.files:
        for file in request.files.getlist('thumbnails'):
            if file and file.filename != '':
                filename = secure_filename(file.filename)
                thumb_image_dir_name = 'products/thumbnails'
                save_dir = os.path.join(current_app.static_folder, thumb_image_dir_name)
                if not os.path.exists(save_dir):
                    os.makedirs(save_dir)
                file_path = os.path.join(save_dir, filename)
                file.save(file_path)
                uploaded_thumb_paths.append(os.path.join(thumb_image_dir_name, filename))


    new_product.image_urls = json.dumps(uploaded_image_paths) if uploaded_image_paths else None
    new_product.image_urls_thumb = json.dumps(uploaded_thumb_paths) if uploaded_thumb_paths else None
    
    db.session.add(new_product)
    db.session.flush() # Get new_product.id

    # Handle variants if any
    if new_product.has_variants:
        weight_options_str = data.get('weight_options', '[]')
        try:
            weight_options = json.loads(weight_options_str)
            for option in weight_options:
                variant = ProductVariant(
                    product_id=new_product.id,
                    weight_grams=int(option['weight']),
                    price=float(option['price']),
                    stock_quantity=int(option.get('stock', 0))
                )
                db.session.add(variant)
                # Record initial stock for variant
                if variant.stock_quantity > 0:
                    stock_movement = StockMovement(
                        product_id=new_product.id,
                        variant_id=variant.id, # Link to variant
                        quantity_change=variant.stock_quantity,
                        reason="initial_stock_variant",
                        notes=f"Initial stock for variant {variant.weight_grams}g"
                    )
                    db.session.add(stock_movement)
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            db.session.rollback()
            current_app.logger.error(f"Error processing product variants: {e}", exc_info=True)
            return jsonify({'success': False, 'message': f'Invalid format for weight options: {e}'}), 400
    elif initial_stock_quantity > 0: # Stock for non-variant product
        new_product.stock_quantity = initial_stock_quantity
        stock_movement = StockMovement(
            product_id=new_product.id,
            quantity_change=initial_stock_quantity,
            reason="initial_stock",
            notes="Initial stock for product"
        )
        db.session.add(stock_movement)

    # Generate assets
    if new_product.generate_assets_on_update: # Also use this for creation
        try:
            # Prepare data for asset generation (ensure all fields are present)
            asset_product_data_fr = new_product.to_dict(lang='fr') # Use to_dict for consistency
            asset_product_data_en = new_product.to_dict(lang='en')
            
            # QR Code
            qr_filename = f"qr_{new_product.sku}.png"
            qr_code_content = f"{current_app.config['APP_BASE_URL']}/produit/{new_product.slug_fr or new_product.id}"
            qr_code_path_abs = os.path.join(current_app.root_path, current_app.config['QR_CODES_OUTPUT_DIR'], qr_filename)
            generate_product_qr_code_image(qr_code_content, qr_code_path_abs)
            new_product.qr_code_path = os.path.join(current_app.config['QR_CODES_DIR_NAME'], qr_filename) # Relative path for URL

            # Passport
            passport_html_fr, passport_html_en = generate_product_passport_html_content(asset_product_data_fr, asset_product_data_en)
            passport_filename_fr = f"passport_{new_product.sku}_fr.html"
            passport_filename_en = f"passport_{new_product.sku}_en.html"
            save_product_passport_html_to_file(passport_html_fr, passport_filename_fr, lang='fr', product_id=new_product.id)
            save_product_passport_html_to_file(passport_html_en, passport_filename_en, lang='en', product_id=new_product.id)
            new_product.passport_path_fr = os.path.join(current_app.config['PASSPORTS_DIR_NAME'], passport_filename_fr)
            new_product.passport_path_en = os.path.join(current_app.config['PASSPORTS_DIR_NAME'], passport_filename_en)
            
            # Label
            label_filename = f"label_{new_product.sku}.png"
            label_image_path_abs = os.path.join(current_app.root_path, current_app.config['LABELS_OUTPUT_DIR'], label_filename)
            # Pass both lang dicts if your label generator can use them, or pick primary
            generate_product_label_image(asset_product_data_fr, asset_product_data_en, label_image_path_abs, new_product.qr_code_path) # Pass QR path
            new_product.label_image_path = os.path.join(current_app.config['LABELS_DIR_NAME'], label_filename)

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error generating assets for new product {new_product.sku}: {e}", exc_info=True)
            return jsonify({'success': False, 'message': f'Product saved, but asset generation failed: {e}'}), 500

    try:
        db.session.commit()
        return jsonify({'success': True, 'message': 'Product created successfully', 'product_id': new_product.id}), 201
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error saving product to database: {e}", exc_info=True)
        return jsonify({'success': False, 'message': f'Database error: {e}'}), 500


@admin_api_bp_for_app.route('/products/<int:product_id>', methods=['PUT'])
@admin_required
def update_product(product_id):
    product = Product.query.get_or_404(product_id)
    data = request.form.to_dict()
    current_app.logger.info(f"Received data for updating product {product_id}: {data}")

    # Update fields
    product.name_fr = data.get('name_fr', product.name_fr)
    product.name_en = data.get('name_en', product.name_en)
    product.description_fr = data.get('description_fr', product.description_fr)
    product.description_en = data.get('description_en', product.description_en)
    product.sku = data.get('sku', product.sku)
    product.category_fr = data.get('category_fr', product.category_fr)
    product.category_en = data.get('category_en', product.category_en)
    
    product.is_featured = data.get('is_featured') == 'true'
    product.is_active = data.get('is_active', product.is_active if product.is_active is not None else True) == 'true' # Handle existing boolean
    
    product.meta_title_fr = data.get('meta_title_fr', product.meta_title_fr)
    product.meta_title_en = data.get('meta_title_en', product.meta_title_en)
    product.meta_description_fr = data.get('meta_description_fr', product.meta_description_fr)
    product.meta_description_en = data.get('meta_description_en', product.meta_description_en)
    product.slug_fr = data.get('slug_fr', product.slug_fr)
    product.slug_en = data.get('slug_en', product.slug_en)
    product.species_fr = data.get('species_fr', product.species_fr)
    product.species_en = data.get('species_en', product.species_en)
    product.origin_fr = data.get('origin_fr', product.origin_fr)
    product.origin_en = data.get('origin_en', product.origin_en)
    product.quality_grade_fr = data.get('quality_grade_fr', product.quality_grade_fr)
    product.quality_grade_en = data.get('quality_grade_en', product.quality_grade_en)
    
    if data.get('nett_weight_g'): product.nett_weight_g = int(data['nett_weight_g'])
    if data.get('harvest_date'): product.harvest_date = datetime.strptime(data['harvest_date'], '%Y-%m-%d').date()
    if data.get('best_before_date'): product.best_before_date = datetime.strptime(data['best_before_date'], '%Y-%m-%d').date()
    
    product.has_variants = data.get('has_variants') == 'true'
    if product.has_variants:
        product.base_price = None # Nullify base_price if variants are now active
        product.stock_quantity = 0 # Stock is managed by variants
    else:
        if data.get('base_price'): product.base_price = float(data['base_price'])
        if data.get('initial_stock_quantity'): # This might be current stock for non-variant
             # For stock updates, use a dedicated stock adjustment endpoint or handle carefully here
             # For simplicity, if not has_variants, this could update the main stock.
            product.stock_quantity = int(data['initial_stock_quantity'])


    product.generate_assets_on_update = data.get('generate_assets_on_update', product.generate_assets_on_update if product.generate_assets_on_update is not None else True) == 'true'

    # Image handling (replace or append logic might be needed)
    # For simplicity, this example replaces images if new ones are uploaded.
    if 'images' in request.files:
        uploaded_image_paths = []
        for file in request.files.getlist('images'):
            if file and file.filename != '':
                filename = secure_filename(file.filename)
                main_image_dir_name = 'products/main'
                save_dir = os.path.join(current_app.static_folder, main_image_dir_name)
                if not os.path.exists(save_dir): os.makedirs(save_dir)
                file_path = os.path.join(save_dir, filename)
                file.save(file_path)
                uploaded_image_paths.append(os.path.join(main_image_dir_name, filename))
        if uploaded_image_paths: product.image_urls = json.dumps(uploaded_image_paths)

    if 'thumbnails' in request.files:
        uploaded_thumb_paths = []
        for file in request.files.getlist('thumbnails'):
            if file and file.filename != '':
                filename = secure_filename(file.filename)
                thumb_image_dir_name = 'products/thumbnails'
                save_dir = os.path.join(current_app.static_folder, thumb_image_dir_name)
                if not os.path.exists(save_dir): os.makedirs(save_dir)
                file_path = os.path.join(save_dir, filename)
                file.save(file_path)
                uploaded_thumb_paths.append(os.path.join(thumb_image_dir_name, filename))
        if uploaded_thumb_paths: product.image_urls_thumb = json.dumps(uploaded_thumb_paths)

    # Handle variants update
    if product.has_variants:
        weight_options_str = data.get('weight_options', '[]')
        try:
            weight_options = json.loads(weight_options_str)
            existing_variants = {v.weight_grams: v for v in product.variants}
            new_variant_weights = []

            for option in weight_options:
                weight = int(option['weight'])
                price = float(option['price'])
                stock = int(option.get('stock', 0))
                new_variant_weights.append(weight)

                if weight in existing_variants: # Update existing variant
                    variant = existing_variants[weight]
                    if variant.stock_quantity != stock: # Record stock movement if changed
                        quantity_change = stock - variant.stock_quantity
                        stock_movement = StockMovement(product_id=product.id, variant_id=variant.id, quantity_change=quantity_change, reason="manual_update_variant", notes=f"Stock updated for variant {weight}g")
                        db.session.add(stock_movement)
                    variant.price = price
                    variant.stock_quantity = stock
                else: # Add new variant
                    variant = ProductVariant(product_id=product.id, weight_grams=weight, price=price, stock_quantity=stock)
                    db.session.add(variant)
                    if stock > 0: # Initial stock for new variant
                        stock_movement = StockMovement(product_id=product.id, variant_id=variant.id, quantity_change=stock, reason="initial_stock_variant", notes=f"Initial stock for new variant {weight}g")
                        db.session.add(stock_movement)
            
            # Remove variants not in the new list
            for weight, variant in existing_variants.items():
                if weight not in new_variant_weights:
                    # Optionally, record stock movement if removing stock
                    if variant.stock_quantity > 0:
                         stock_movement = StockMovement(product_id=product.id, variant_id=variant.id, quantity_change=-variant.stock_quantity, reason="variant_deleted", notes=f"Stock removed for deleted variant {weight}g")
                         db.session.add(stock_movement)
                    db.session.delete(variant)

        except (json.JSONDecodeError, ValueError, KeyError) as e:
            db.session.rollback()
            current_app.logger.error(f"Error updating product variants for {product_id}: {e}", exc_info=True)
            return jsonify({'success': False, 'message': f'Invalid format for weight options: {e}'}), 400

    db.session.flush() # Apply changes before asset generation

    if product.generate_assets_on_update:
        try:
            # Ensure all necessary data is fresh from the product object after updates
            asset_product_data_fr = product.to_dict(lang='fr') # Use the updated product object
            asset_product_data_en = product.to_dict(lang='en')

            # QR Code (regenerate if slug/ID changes or just always)
            qr_filename = f"qr_{product.sku}.png"
            qr_code_content = f"{current_app.config['APP_BASE_URL']}/produit/{product.slug_fr or product.id}"
            qr_code_path_abs = os.path.join(current_app.root_path, current_app.config['QR_CODES_OUTPUT_DIR'], qr_filename)
            generate_product_qr_code_image(qr_code_content, qr_code_path_abs)
            product.qr_code_path = os.path.join(current_app.config['QR_CODES_DIR_NAME'], qr_filename)

            # Passport
            passport_html_fr, passport_html_en = generate_product_passport_html_content(asset_product_data_fr, asset_product_data_en)
            passport_filename_fr = f"passport_{product.sku}_fr.html"
            passport_filename_en = f"passport_{product.sku}_en.html"
            save_product_passport_html_to_file(passport_html_fr, passport_filename_fr, lang='fr', product_id=product.id)
            save_product_passport_html_to_file(passport_html_en, passport_filename_en, lang='en', product_id=product.id)
            product.passport_path_fr = os.path.join(current_app.config['PASSPORTS_DIR_NAME'], passport_filename_fr)
            product.passport_path_en = os.path.join(current_app.config['PASSPORTS_DIR_NAME'], passport_filename_en)
            
            # Label
            label_filename = f"label_{product.sku}.png"
            label_image_path_abs = os.path.join(current_app.root_path, current_app.config['LABELS_OUTPUT_DIR'], label_filename)
            generate_product_label_image(asset_product_data_fr, asset_product_data_en, label_image_path_abs, product.qr_code_path)
            product.label_image_path = os.path.join(current_app.config['LABELS_DIR_NAME'], label_filename)

        except Exception as e:
            # Don't rollback product data changes, but log asset error
            current_app.logger.error(f"Error regenerating assets for product {product.sku}: {e}", exc_info=True)
            # Optionally, set product.generate_assets_on_update to False or add a status field

    try:
        db.session.commit()
        return jsonify({'success': True, 'message': 'Product updated successfully', 'product': product.to_dict(lang='fr')}), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error committing product update {product_id}: {e}", exc_info=True)
        return jsonify({'success': False, 'message': f'Database error on commit: {e}'}), 500


@admin_api_bp_for_app.route('/products/<int:product_id>', methods=['DELETE'])
@admin_required
def delete_product(product_id):
    product = Product.query.get_or_404(product_id)
    try:
        # Add logic to handle related entities if needed (e.g., order items, stock movements)
        # For now, direct delete. Consider soft delete by setting is_active = False.
        
        # Delete associated assets from filesystem (optional, can lead to clutter if not done)
        # Example for QR code:
        if product.qr_code_path:
            qr_abs_path = os.path.join(current_app.root_path, current_app.config['QR_CODES_OUTPUT_DIR'], os.path.basename(product.qr_code_path))
            if os.path.exists(qr_abs_path): os.remove(qr_abs_path)
        # Add similar for passport and label files...

        db.session.delete(product)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Product deleted successfully'}), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting product {product_id}: {e}", exc_info=True)
        return jsonify({'success': False, 'message': f'Error deleting product: {e}'}), 500


@admin_api_bp_for_app.route('/products', methods=['GET'])
@admin_required
def get_products():
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        lang = request.args.get('lang', current_app.config.get('DEFAULT_LANGUAGE', 'fr'))

        products_query = Product.query.order_by(Product.created_at.desc())
        products_pagination = products_query.paginate(page=page, per_page=per_page, error_out=False)
        
        products_data = [p.to_dict(lang=lang) for p in products_pagination.items]
        
        return jsonify({
            'success': True,
            'products': products_data,
            'total': products_pagination.total,
            'pages': products_pagination.pages,
            'current_page': products_pagination.page
        })
    except Exception as e:
        current_app.logger.error(f"Error fetching products: {e}", exc_info=True)
        return jsonify({'success': False, 'message': str(e)}), 500

@admin_api_bp_for_app.route('/products/<int:product_id>', methods=['GET'])
@admin_required
def get_admin_product_details(product_id):
    product = Product.query.get_or_404(product_id)
    lang = request.args.get('lang', current_app.config.get('DEFAULT_LANGUAGE', 'fr'))
    product_dict = product.to_dict(lang=lang, include_variants=True, include_stock_movements=True)

    # Ensure image_urls and image_urls_thumb are lists (they are stored as JSON strings)
    for key in ['image_urls', 'image_urls_thumb']:
        raw_val = product_dict.get(key)
        if isinstance(raw_val, str):
            try:
                product_dict[key] = json.loads(raw_val)
            except json.JSONDecodeError:
                product_dict[key] = [] # Default to empty list on error
        elif not isinstance(raw_val, list):
             product_dict[key] = [] # Default if not string and not list

    return jsonify({'success': True, 'product': product_dict})


@admin_api_bp_for_app.route('/users', methods=['GET'])
@admin_required
def get_users():
    try:
        user_type_filter = request.args.get('user_type')
        status_filter = request.args.get('status') # For filtering by status e.g. 'pending_approval'
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)

        query = User.query

        if user_type_filter:
            if user_type_filter.lower() == 'b2b' or user_type_filter.lower() == 'professional':
                query = query.filter(User.user_type == 'professional')
            elif user_type_filter.lower() == 'b2c':
                query = query.filter(User.user_type == 'b2c')
            # Add more conditions if other types exist
        
        if status_filter:
            query = query.filter(User.status == status_filter.lower())

        users_pagination = query.order_by(User.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
        
        users_data = [user.to_dict(include_sensitive=True) for user in users_pagination.items] # Be cautious with include_sensitive

        return jsonify({
            'success': True,
            'users': users_data,
            'total': users_pagination.total,
            'pages': users_pagination.pages,
            'current_page': users_pagination.page
        })
    except Exception as e:
        current_app.logger.error(f"Error fetching users: {e}", exc_info=True)
        return jsonify({'success': False, 'message': str(e)}), 500


@admin_api_bp_for_app.route('/users/<int:user_id>/approve', methods=['POST'])
@admin_required
def approve_professional_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.user_type != 'professional':
        return jsonify({'success': False, 'message': 'User is not a professional type.'}), 400
    
    user.is_approved = True
    user.status = 'active' # Or 'approved'
    try:
        db.session.commit()
        # TODO: Send notification email to user
        return jsonify({'success': True, 'message': 'Professional user approved successfully.'})
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error approving user {user_id}: {e}", exc_info=True)
        return jsonify({'success': False, 'message': f'Database error: {e}'}), 500

@admin_api_bp_for_app.route('/users/<int:user_id>/status', methods=['PUT'])
@admin_required
def update_user_status(user_id):
    user = User.query.get_or_404(user_id)
    data = request.get_json()
    new_status = data.get('status')

    if not new_status or new_status not in ['active', 'inactive', 'pending_approval', 'rejected', 'suspended']: # Add valid statuses
        return jsonify({'success': False, 'message': 'Invalid or missing status.'}), 400

    user.status = new_status
    if new_status == 'active':
        user.is_approved = True # Typically if active, they are approved
    elif new_status in ['pending_approval', 'rejected', 'suspended', 'inactive']:
        user.is_approved = False


    try:
        db.session.commit()
        return jsonify({'success': True, 'message': f'User status updated to {new_status}.'})
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error updating status for user {user_id}: {e}", exc_info=True)
        return jsonify({'success': False, 'message': f'Database error: {e}'}), 500


@admin_api_bp_for_app.route('/orders', methods=['GET'])
@admin_required
def get_orders():
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        orders_pagination = Order.query.order_by(Order.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
        
        orders_data = []
        for order in orders_pagination.items:
            order_dict = order.to_dict()
            order_dict['user'] = order.user.to_dict() if order.user else None
            order_dict['items'] = [item.to_dict() for item in order.items]
            orders_data.append(order_dict)

        return jsonify({
            'success': True,
            'orders': orders_data,
            'total': orders_pagination.total,
            'pages': orders_pagination.pages,
            'current_page': orders_pagination.page
        })
    except Exception as e:
        current_app.logger.error(f"Error fetching orders: {e}", exc_info=True)
        return jsonify({'success': False, 'message': str(e)}), 500

@admin_api_bp_for_app.route('/orders/<int:order_id>/status', methods=['PUT'])
@admin_required
def update_order_status(order_id):
    order = Order.query.get_or_404(order_id)
    data = request.get_json()
    new_status = data.get('status')

    if not new_status: # Add validation for allowed statuses
        return jsonify({'success': False, 'message': 'New status not provided.'}), 400
    
    order.status = new_status
    # Potentially add more logic here, e.g., if status is 'shipped', update shipping info, send email.
    try:
        db.session.commit()
        return jsonify({'success': True, 'message': f'Order {order_id} status updated to {new_status}.'})
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error updating status for order {order_id}: {e}", exc_info=True)
        return jsonify({'success': False, 'message': f'Database error: {e}'}), 500


@admin_api_bp_for_app.route('/stock-movements', methods=['POST'])
@admin_required
def add_stock_movement():
    data = request.get_json()
    product_id = data.get('product_id')
    variant_id = data.get('variant_id') # Optional
    quantity_change = data.get('quantity_change')
    reason = data.get('reason')
    notes = data.get('notes')

    if not product_id or quantity_change is None or not reason:
        return jsonify({'success': False, 'message': 'Missing required fields: product_id, quantity_change, reason.'}), 400
    
    try:
        quantity_change = int(quantity_change)
    except ValueError:
        return jsonify({'success': False, 'message': 'quantity_change must be an integer.'}), 400

    product = Product.query.get(product_id)
    if not product:
        return jsonify({'success': False, 'message': 'Product not found.'}), 404
    
    target_variant = None
    if variant_id:
        target_variant = ProductVariant.query.filter_by(id=variant_id, product_id=product_id).first()
        if not target_variant:
            return jsonify({'success': False, 'message': 'Variant not found for this product.'}), 404
    elif product.has_variants:
        return jsonify({'success': False, 'message': 'This product has variants. Please specify a variant_id for stock adjustment.'}), 400


    movement = StockMovement(
        product_id=product_id,
        variant_id=variant_id,
        quantity_change=quantity_change,
        reason=reason,
        notes=notes
    )
    db.session.add(movement)

    # Update product or variant stock
    if target_variant:
        target_variant.stock_quantity += quantity_change
    else: # Non-variant product
        product.stock_quantity += quantity_change
    
    try:
        db.session.commit()
        return jsonify({'success': True, 'message': 'Stock movement recorded successfully.'}), 201
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error recording stock movement: {e}", exc_info=True)
        return jsonify({'success': False, 'message': f'Database error: {e}'}), 500


@admin_api_bp_for_app.route('/invoices/upload', methods=['POST'])
@admin_required
def upload_invoice():
    if 'invoice_file' not in request.files:
        return jsonify({'success': False, 'message': 'No invoice file part'}), 400
    file = request.files['invoice_file']
    if file.filename == '':
        return jsonify({'success': False, 'message': 'No selected invoice file'}), 400

    user_id = request.form.get('user_id') # B2B User ID
    order_id = request.form.get('order_id') # Optional, if linked to a specific order
    invoice_number = request.form.get('invoice_number')
    issue_date_str = request.form.get('issue_date')
    due_date_str = request.form.get('due_date')
    total_amount = request.form.get('total_amount')

    if not all([user_id, invoice_number, issue_date_str, total_amount]):
         return jsonify({'success': False, 'message': 'Missing required fields: user_id, invoice_number, issue_date, total_amount'}), 400

    if file and allowed_file(file.filename):
        filename = secure_filename(f"{invoice_number}_{user_id}_{file.filename}")
        
        upload_dir_abs = os.path.abspath(os.path.join(current_app.root_path, current_app.config['INVOICES_UPLOAD_DIR']))
        if not os.path.exists(upload_dir_abs):
            os.makedirs(upload_dir_abs)
        
        file_path_abs = os.path.join(upload_dir_abs, filename)
        file.save(file_path_abs)
        
        file_path_relative = os.path.join(current_app.config['INVOICES_DIR_NAME'], filename) # For URL and DB storage

        try:
            new_invoice = Invoice(
                user_id=int(user_id),
                order_id=int(order_id) if order_id else None,
                invoice_number=invoice_number,
                issue_date=datetime.strptime(issue_date_str, '%Y-%m-%d').date(),
                due_date=datetime.strptime(due_date_str, '%Y-%m-%d').date() if due_date_str else None,
                total_amount=float(total_amount),
                status='unpaid', # Default status
                file_path=file_path_relative, # Store relative path
                is_uploaded=True
            )
            db.session.add(new_invoice)
            db.session.commit()
            return jsonify({'success': True, 'message': 'Invoice uploaded successfully', 'invoice_id': new_invoice.id, 'file_path': file_path_relative}), 201
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error saving uploaded invoice to DB: {e}", exc_info=True)
            # Clean up uploaded file if DB save fails
            if os.path.exists(file_path_abs):
                os.remove(file_path_abs)
            return jsonify({'success': False, 'message': f'Database error: {e}'}), 500
    else:
        return jsonify({'success': False, 'message': 'File type not allowed. Only PDF is accepted.'}), 400


@admin_api_bp_for_app.route('/invoices/generate', methods=['POST'])
@admin_required
def generate_and_save_invoice():
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': 'No data provided for invoice generation.'}), 400

    user_id = data.get('user_id')
    order_id = data.get('order_id') # Optional, if generating from an order
    client_details = data.get('client_details') # Expects dict: {'name', 'address', 'vat_number'}
    invoice_items = data.get('items') # Expects list of dicts: {'description', 'quantity', 'unit_price'}
    invoice_number = data.get('invoice_number') # Can be auto-generated or provided
    issue_date_str = data.get('issue_date', datetime.utcnow().strftime('%Y-%m-%d'))
    due_date_str = data.get('due_date')

    if not user_id or not client_details or not invoice_items:
        return jsonify({'success': False, 'message': 'Missing required fields for invoice generation.'}), 400

    user = User.query.get(user_id)
    if not user:
        return jsonify({'success': False, 'message': 'Client user not found.'}), 404

    # Auto-generate invoice number if not provided
    if not invoice_number:
        last_invoice = Invoice.query.order_by(Invoice.id.desc()).first()
        next_id = (last_invoice.id + 1) if last_invoice else 1
        invoice_number = f"INV-{datetime.utcnow().year}-{next_id:04d}"
    
    # Check for duplicate invoice number for this user
    if Invoice.query.filter_by(user_id=user_id, invoice_number=invoice_number).first():
        return jsonify({'success': False, 'message': f'Invoice number {invoice_number} already exists for this user.'}), 409


    invoice_data_for_pdf = {
        'invoice_number': invoice_number,
        'issue_date': issue_date_str,
        'due_date': due_date_str,
        'client_name': client_details.get('name', user.company_name or f"{user.first_name} {user.last_name}"),
        'client_address': client_details.get('address', user.address), # Assuming user model has address
        'client_vat': client_details.get('vat_number', user.vat_number), # Assuming user model has vat_number
        'items': invoice_items,
        # Company details will be taken from config in invoice_service
    }
    
    # Calculate totals
    totals = calculate_invoice_totals_service(invoice_items)
    invoice_data_for_pdf.update(totals) # Add subtotal, tax_amount, grand_total to PDF data

    filename = f"{invoice_number.replace('/', '-')}_{user_id}.pdf"
    
    upload_dir_abs = os.path.abspath(os.path.join(current_app.root_path, current_app.config['INVOICES_UPLOAD_DIR']))
    if not os.path.exists(upload_dir_abs):
        os.makedirs(upload_dir_abs)
    pdf_path_abs = os.path.join(upload_dir_abs, filename)

    try:
        generate_invoice_pdf_to_file(pdf_path_abs, invoice_data_for_pdf)
        
        file_path_relative = os.path.join(current_app.config['INVOICES_DIR_NAME'], filename)

        new_invoice = Invoice(
            user_id=int(user_id),
            order_id=int(order_id) if order_id else None,
            invoice_number=invoice_number,
            issue_date=datetime.strptime(issue_date_str, '%Y-%m-%d').date(),
            due_date=datetime.strptime(due_date_str, '%Y-%m-%d').date() if due_date_str else None,
            total_amount=totals['grand_total'],
            status='unpaid', # Default status
            file_path=file_path_relative,
            is_generated=True
        )
        db.session.add(new_invoice)
        db.session.commit()
        
        # Construct the download URL
        # download_url = url_for('static', filename=file_path_relative, _external=True)
        # The above might not work if INVOICES_DIR_NAME is not directly under static_folder root for url_for
        # A more robust way if files are served via a dedicated route or if INVOICES_UPLOAD_DIR is the static folder itself:
        download_url = f"{current_app.config['INVOICE_DOWNLOAD_BASE_URL']}{filename}"


        return jsonify({
            'success': True, 
            'message': 'Invoice generated and saved successfully', 
            'invoice_id': new_invoice.id,
            'file_path': file_path_relative,
            'download_url': download_url
        }), 201

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error generating or saving invoice: {e}", exc_info=True)
        # Clean up generated PDF if DB save fails or PDF generation failed mid-way
        if os.path.exists(pdf_path_abs):
            os.remove(pdf_path_abs)
        return jsonify({'success': False, 'message': f'Error during invoice process: {e}'}), 500


@admin_api_bp_for_app.route('/invoices', methods=['GET'])
@admin_required
def get_invoices():
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        user_id_filter = request.args.get('user_id', type=int)

        query = Invoice.query
        if user_id_filter:
            query = query.filter_by(user_id=user_id_filter)
        
        invoices_pagination = query.order_by(Invoice.issue_date.desc()).paginate(page=page, per_page=per_page, error_out=False)
        
        invoices_data = []
        for inv in invoices_pagination.items:
            inv_dict = inv.to_dict()
            inv_dict['user'] = inv.user.to_dict() if inv.user else None
            # Construct download URL
            inv_dict['download_url'] = f"{current_app.config['INVOICE_DOWNLOAD_BASE_URL']}{os.path.basename(inv.file_path)}" if inv.file_path else None
            invoices_data.append(inv_dict)

        return jsonify({
            'success': True,
            'invoices': invoices_data,
            'total': invoices_pagination.total,
            'pages': invoices_pagination.pages,
            'current_page': invoices_pagination.page
        })
    except Exception as e:
        current_app.logger.error(f"Error fetching invoices: {e}", exc_info=True)
        return jsonify({'success': False, 'message': str(e)}), 500


@admin_api_bp_for_app.route('/dashboard-stats', methods=['GET'])
@admin_required
def get_dashboard_stats():
    try:
        product_count = Product.query.count()
        
        # Recent orders (e.g., last 7 days)
        seven_days_ago = datetime.utcnow() - timedelta(days=7)
        recent_orders_count = Order.query.filter(Order.created_at >= seven_days_ago).count()
        
        # New users (e.g., last 7 days)
        new_users_count = User.query.filter(User.created_at >= seven_days_ago).count()

        # Total Sales (sum of total_amount for 'completed' or 'paid' orders)
        # Ensure Order model has 'total_amount' and 'status'
        total_sales_query = db.session.query(func.sum(Order.total_amount)).filter(
            or_(Order.status == 'completed', Order.status == 'paid') # Adjust statuses as per your system
        ).scalar()
        total_sales = float(total_sales_query) if total_sales_query else 0.0

        # Pending B2B Approvals
        pending_b2b_approvals = User.query.filter_by(user_type='professional', status='pending_approval').count()

        return jsonify({
            'success': True,
            'stats': {
                'total_products': product_count,
                'recent_orders_count': recent_orders_count,
                'new_users_count': new_users_count,
                'total_sales': total_sales,
                'pending_b2b_approvals': pending_b2b_approvals
            }
        })
    except Exception as e:
        current_app.logger.error(f"Error fetching dashboard stats: {e}", exc_info=True)
        return jsonify({'success': False, 'message': f'Error fetching stats: {str(e)}'}), 500



# --- B2B User Management ---
@admin_api_bp.route('/users/b2b/pending', methods=['GET'])
@admin_required
def get_pending_b2b_users():
    db = None
    try:
        db = get_db()
        cursor = db.cursor()
        cursor.execute("""
            SELECT id, email, company_name, nom, prenom, phone_number, created_at 
            FROM users 
            WHERE user_type = 'b2b' AND status = 'pending_approval' 
            ORDER BY created_at DESC
        """)
        pending_users = [dict(row) for row in cursor.fetchall()]
        AuditLogService.log_event(action="ADMIN_VIEWED_PENDING_B2B_USERS", target_type="ADMIN_PANEL")
        return jsonify({"success": True, "users": pending_users}), 200
    except Exception as e:
        log_error(f"Erreur récupération utilisateurs B2B en attente: {e}")
        AuditLogService.log_event(action="ADMIN_VIEW_PENDING_B2B_ERROR", details={"error": str(e)}, success=False)
        return jsonify({"success": False, "message": "Erreur serveur."}), 500
    finally:
        if db: db.close()

@admin_api_bp.route('/users/b2b/<int:user_id>/approve', methods=['POST'])
@admin_required
def approve_b2b_user(user_id):
    db = None
    try:
        db = get_db()
        cursor = db.cursor()
        cursor.execute("SELECT email, company_name, status FROM users WHERE id = ? AND user_type = 'b2b'", (user_id,))
        user = cursor.fetchone()

        if not user:
            AuditLogService.log_event(action="ADMIN_APPROVE_B2B_NOT_FOUND", target_type="USER", target_id=user_id, success=False)
            return jsonify({"success": False, "message": "Utilisateur B2B non trouvé."}), 404
        if user['status'] == 'active':
            AuditLogService.log_event(action="ADMIN_APPROVE_B2B_ALREADY_ACTIVE", target_type="USER", target_id=user_id, success=False)
            return jsonify({"success": False, "message": "Ce compte est déjà actif."}), 400

        cursor.execute("UPDATE users SET status = 'active' WHERE id = ?", (user_id,))
        db.commit()

        if cursor.rowcount > 0:
            # Send approval email to B2B user
            email_sent = send_b2b_approval_email(user['email'], user['company_name'])
            if email_sent:
                AuditLogService.log_event(action="ADMIN_APPROVED_B2B_USER", target_type="USER", target_id=user_id, details={"email": user['email'], "email_notification_sent": True})
                return jsonify({"success": True, "message": f"Compte B2B pour {user['company_name']} approuvé. Email de notification envoyé."}), 200
            else:
                AuditLogService.log_event(action="ADMIN_APPROVED_B2B_USER", target_type="USER", target_id=user_id, details={"email": user['email'], "email_notification_failed": True})
                # Still success for approval, but note email failure
                return jsonify({"success": True, "message": f"Compte B2B pour {user['company_name']} approuvé, mais l'email de notification n'a pas pu être envoyé."}), 200 # Or 207 Multi-Status
        else:
            AuditLogService.log_event(action="ADMIN_APPROVE_B2B_NO_UPDATE", target_type="USER", target_id=user_id, success=False)
            return jsonify({"success": False, "message": "Échec de l'approbation du compte."}), 500

    except Exception as e:
        if db: db.rollback()
        log_error(f"Erreur lors de l'approbation du compte B2B {user_id}: {e}")
        AuditLogService.log_event(action="ADMIN_APPROVE_B2B_ERROR", target_type="USER", target_id=user_id, details={"error": str(e)}, success=False)
        return jsonify({"success": False, "message": "Erreur serveur."}), 500
    finally:
        if db: db.close()

@admin_api_bp.route('/users/b2b/<int:user_id>/status', methods=['PUT'])
@admin_required
def update_b2b_user_status(user_id):
    data = request.get_json()
    new_status = data.get('status')

    if not new_status or new_status not in ['active', 'suspended', 'pending_approval']: # Add other valid statuses if any
        return jsonify({"success": False, "message": "Statut invalide fourni."}), 400

    db = None
    try:
        db = get_db()
        cursor = db.cursor()
        cursor.execute("SELECT status, email, company_name FROM users WHERE id = ? AND user_type = 'b2b'", (user_id,))
        user = cursor.fetchone()
        if not user:
            return jsonify({"success": False, "message": "Utilisateur B2B non trouvé."}), 404

        old_status = user['status']
        if old_status == new_status:
            return jsonify({"success": True, "message": "Le statut est déjà à jour."}), 200

        cursor.execute("UPDATE users SET status = ? WHERE id = ?", (new_status, user_id))
        db.commit()

        AuditLogService.log_event(
            action="ADMIN_UPDATED_B2B_USER_STATUS",
            target_type="USER", target_id=user_id,
            details={"email": user['email'], "old_status": old_status, "new_status": new_status, "admin_id": g.current_user_id}
        )
        # Optionally send notification to user if status changes to 'suspended' or back to 'active'
        return jsonify({"success": True, "message": f"Statut du compte pour {user['company_name']} mis à jour à '{new_status}'."}), 200
    except Exception as e:
        if db: db.rollback()
        log_error(f"Erreur MAJ statut B2B user {user_id}: {e}")
        return jsonify({"success": False, "message": "Erreur serveur."}), 500
    finally:
        if db: db.close()


# --- B2B Invoice Management ---
@admin_api_bp.route('/invoices/b2b', methods=['POST'])
@admin_required
def create_b2b_invoice():
    data = request.form # Using request.form for potential file upload later
    
    # --- Extract and Validate Data ---
    user_id = data.get('user_id_for_creation')
    invoice_number = data.get('invoice_number_create')
    invoice_date_str = data.get('invoice_date_create')
    invoice_due_date_str = data.get('invoice_due_date_create')
    
    client_company_name = data.get('client_company_name') # Should be fetched from user_id ideally
    client_contact_person = data.get('client_contact_person') # Should be fetched
    client_address_lines_str = data.get('client_address_lines', '')
    client_vat_number = data.get('client_vat_number', '')
    
    discount_percentage_str = data.get('discount_percentage_create', "0")
    vat_rate_percent_str = data.get('vat_rate_percent_create', "20")

    # Basic validation
    if not all([user_id, invoice_number, invoice_date_str, invoice_due_date_str]):
        return jsonify({"success": False, "message": "Champs de facture requis manquants."}), 400
    try:
        user_id = int(user_id)
        # Validate dates
        invoice_date = datetime.datetime.strptime(invoice_date_str, '%Y-%m-%d').date()
        invoice_due_date = datetime.datetime.strptime(invoice_due_date_str, '%Y-%m-%d').date()
    except ValueError:
        return jsonify({"success": False, "message": "Format de date invalide (AAAA-MM-JJ attendu)."}), 400

    # --- Line Items ---
    items_data = []
    item_index = 0
    while True:
        desc = data.get(f'items[{item_index}][description]')
        qty_str = data.get(f'items[{item_index}][quantity]')
        price_str = data.get(f'items[{item_index}][unit_price_ht]')
        if not desc: break # No more items
        try:
            qty = int(qty_str)
            price = float(price_str)
            if qty <= 0 or price < 0:
                return jsonify({"success": False, "message": f"Quantité ou prix invalide pour l'article '{desc}'."}), 400
            items_data.append({
                "description": desc,
                "quantity": qty,
                "unit_price_ht": price,
                "total_ht": qty * price
            })
        except (ValueError, TypeError):
            return jsonify({"success": False, "message": f"Données d'article invalides pour '{desc}'."}), 400
        item_index += 1
    
    if not items_data:
        return jsonify({"success": False, "message": "Au moins un article est requis pour la facture."}), 400

    # --- Calculate Totals (using the function from generate_professional_invoice.py) ---
    calculated_totals = calculate_invoice_totals(items_data, discount_percentage_str, vat_rate_percent_str)

    # --- Prepare data for PDF generation ---
    # Fetch B2B user details for the invoice header
    db_conn = get_db()
    cursor = db_conn.cursor()
    cursor.execute("SELECT company_name, nom, prenom, email FROM users WHERE id = ? AND user_type = 'b2b'", (user_id,))
    b2b_user = cursor.fetchone()
    if not b2b_user:
        db_conn.close()
        return jsonify({"success": False, "message": "Client B2B non trouvé."}), 404
    
    # Use B2B user's actual company name and contact if not overridden by form
    client_data_for_pdf = {
        "company_name": client_company_name or b2b_user['company_name'],
        "contact_person": client_contact_person or f"{b2b_user['prenom']} {b2b_user['nom']}",
        "address_lines": [line.strip() for line in client_address_lines_str.split('\n') if line.strip()],
        "vat_number": client_vat_number
    }
    
    invoice_data_for_pdf = {
        "number": invoice_number,
        "date": invoice_date_str,
        "due_date": invoice_due_date_str,
        "total_ht": calculated_totals['total_ht_before_discount'], # Sum of line items
        "discount_percent": calculated_totals['discount_percent'],
        "discount_amount_ht": calculated_totals['discount_amount_ht'],
        "total_ht_after_discount": calculated_totals['total_ht_after_discount'],
        "vat_rate_percent": calculated_totals['vat_rate_percent'],
        "vat_amount": calculated_totals['vat_amount'],
        "total_ttc": calculated_totals['total_ttc']
    }

    # --- Generate PDF ---
    invoices_dir = current_app.config.get('INVOICES_UPLOAD_DIR')
    if not invoices_dir:
        log_error("INVOICES_UPLOAD_DIR n'est pas configuré.")
        db_conn.close()
        return jsonify({"success": False, "message": "Configuration serveur incorrecte pour les factures."}), 500
    os.makedirs(invoices_dir, exist_ok=True)
    
    # Sanitize invoice number for filename
    safe_invoice_filename_base = secure_filename(f"Facture_{invoice_number.replace('/', '-')}")
    pdf_filename = f"{safe_invoice_filename_base}.pdf"
    pdf_filepath = os.path.join(invoices_dir, pdf_filename)

    # Get configurable invoice template data from app_settings or config
    # For simplicity, using hardcoded values from generate_professional_invoice.py for now
    # In a real app, fetch these from DB (app_settings table) or app.config
    # company_info_for_pdf = { ... load from config/DB ... }
    # generate_invoice_pdf(pdf_filepath, client_data_for_pdf, invoice_data_for_pdf, items_data, company_info_for_pdf)
    
    # Using the generate_invoice_pdf that reads its own constants for company info
    try:
        generate_invoice_pdf(pdf_filepath, client_data_for_pdf, invoice_data_for_pdf, items_data)
    except Exception as e:
        log_error(f"Erreur lors de la génération du PDF de la facture {invoice_number}: {e}")
        db_conn.close()
        return jsonify({"success": False, "message": f"Erreur lors de la génération du PDF: {str(e)}"}), 500

    # --- Save Invoice to Database ---
    try:
        cursor.execute(
            """INSERT INTO invoices (user_id, invoice_number, invoice_date, due_date, 
                                  total_amount_ht, total_amount_ttc, vat_amount, discount_amount,
                                  status, file_path, created_by_admin_id)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (user_id, invoice_number, invoice_date, invoice_due_date,
             calculated_totals['total_ht_after_discount'], calculated_totals['total_ttc'],
             calculated_totals['vat_amount'], calculated_totals['discount_amount_ht'],
             'pending', # Default status
             pdf_filename, # Store only filename, not full path
             g.current_user_id)
        )
        invoice_id = cursor.lastrowid
        db_conn.commit()
        AuditLogService.log_event(
            action="ADMIN_CREATED_B2B_INVOICE", target_type="INVOICE", target_id=invoice_id,
            details={"user_id": user_id, "invoice_number": invoice_number, "total_ttc": calculated_totals['total_ttc'], "admin_id": g.current_user_id}
        )
        return jsonify({
            "success": True, 
            "message": "Facture B2B créée et PDF généré avec succès.",
            "invoice_id": invoice_id,
            "pdf_filename": pdf_filename, # Frontend can use this to construct download URL
            "pdf_download_url": url_for('professional_bp_routes.download_professional_invoice', invoice_id=invoice_id, _external=False) # Relative URL for professional to download
        }), 201

    except sqlite3.IntegrityError as ie: # e.g. duplicate invoice_number for user
        if db_conn: db_conn.rollback()
        log_error(f"Erreur d'intégrité DB création facture B2B: {ie}")
        # Clean up generated PDF if DB insert fails
        if os.path.exists(pdf_filepath): os.remove(pdf_filepath)
        return jsonify({"success": False, "message": "Erreur de base de données: Le numéro de facture existe peut-être déjà pour ce client."}), 409
    except Exception as e:
        if db_conn: db_conn.rollback()
        log_error(f"Erreur sauvegarde facture B2B en DB: {e}")
        if os.path.exists(pdf_filepath): os.remove(pdf_filepath)
        return jsonify({"success": False, "message": "Erreur serveur lors de la sauvegarde de la facture."}), 500
    finally:
        if db_conn: db_conn.close()


@admin_api_bp.route('/invoices/b2b/<int:invoice_id>/status', methods=['PUT'])
@admin_required
def update_b2b_invoice_status(invoice_id):
    data = request.get_json()
    new_status = data.get('status')
    paid_date_str = data.get('paid_date') # Optional

    valid_statuses = ['pending', 'paid', 'overdue', 'cancelled'] # Define your statuses
    if not new_status or new_status not in valid_statuses:
        return jsonify({"success": False, "message": f"Statut invalide. Doit être l'un de: {', '.join(valid_statuses)}."}), 400

    paid_date = None
    if new_status == 'paid':
        if paid_date_str:
            try:
                paid_date = datetime.datetime.strptime(paid_date_str, '%Y-%m-%d').date()
            except ValueError:
                return jsonify({"success": False, "message": "Format de date de paiement invalide (AAAA-MM-JJ)."}), 400
        else: # If marking as paid, default paid_date to today if not provided
            paid_date = datetime.date.today()
    
    db = None
    try:
        db = get_db()
        cursor = db.cursor()
        cursor.execute("SELECT status, user_id, invoice_number FROM invoices WHERE invoice_id = ?", (invoice_id,))
        invoice = cursor.fetchone()
        if not invoice:
            return jsonify({"success": False, "message": "Facture non trouvée."}), 404

        old_status = invoice['status']
        if old_status == new_status and (new_status != 'paid' or (new_status == 'paid' and not paid_date_str)): # no change if status same unless it's paid and paid_date is being explicitly set
            return jsonify({"success": True, "message": "Le statut de la facture est déjà à jour."}), 200

        if new_status == 'paid':
            cursor.execute("UPDATE invoices SET status = ?, paid_date = ?, last_updated_by_admin_id = ?, last_updated_at = CURRENT_TIMESTAMP WHERE invoice_id = ?", 
                           (new_status, paid_date, g.current_user_id, invoice_id))
        else: # For other statuses, nullify paid_date
            cursor.execute("UPDATE invoices SET status = ?, paid_date = NULL, last_updated_by_admin_id = ?, last_updated_at = CURRENT_TIMESTAMP WHERE invoice_id = ?", 
                           (new_status, g.current_user_id, invoice_id))
        db.commit()

        AuditLogService.log_event(
            action="ADMIN_UPDATED_INVOICE_STATUS",
            target_type="INVOICE", target_id=invoice_id,
            details={
                "invoice_number": invoice['invoice_number'], "user_id": invoice['user_id'],
                "old_status": old_status, "new_status": new_status, 
                "paid_date_set": str(paid_date) if paid_date else None,
                "admin_id": g.current_user_id
            }
        )
        # Optionally, send notification to B2B user about invoice status change (e.g., if paid)
        return jsonify({"success": True, "message": f"Statut de la facture {invoice['invoice_number']} mis à jour à '{new_status}'."}), 200
    except Exception as e:
        if db: db.rollback()
        log_error(f"Erreur MAJ statut facture {invoice_id}: {e}")
        return jsonify({"success": False, "message": "Erreur serveur."}), 500
    finally:
        if db: db.close()

@admin_api_bp.route('/invoices/b2b/for-user/<int:user_id>', methods=['GET'])
@admin_required
def get_b2b_invoices_for_user(user_id):
    db = None
    try:
        db = get_db()
        cursor = db.cursor()
        cursor.execute(
            """SELECT invoice_id, invoice_number, invoice_date, due_date, total_amount_ttc, status, paid_date, file_path 
               FROM invoices 
               WHERE user_id = ? 
               ORDER BY invoice_date DESC""", (user_id,))
        invoices = [dict(row) for row in cursor.fetchall()]
        return jsonify({"success": True, "invoices": invoices}), 200
    except Exception as e:
        log_error(f"Erreur récupération factures pour B2B user {user_id}: {e}")
        return jsonify({"success": False, "message": "Erreur serveur."}), 500
    finally:
        if db: db.close()

# --- Endpoint for getting invoice template settings (Conceptual) ---
@admin_api_bp.route('/settings/invoice-template', methods=['GET'])
@admin_required
def get_invoice_template_settings():
    # In a real app, fetch these from the 'app_settings' table or a config file
    settings = {
        "company_name": current_app.config.get('INVOICE_COMPANY_NAME', "Maison Trüvra SARL (Default)"),
        "company_address_lines": current_app.config.get('INVOICE_COMPANY_ADDRESS_LINES', ["123 Rue de la Truffe", "75001 Paris, France"]),
        "company_siret": current_app.config.get('INVOICE_COMPANY_SIRET', "SIRET: 123 456 789 00012"),
        "company_vat_number": current_app.config.get('INVOICE_COMPANY_VAT_NUMBER', "TVA: FR 00 123456789"),
        "company_contact_info": current_app.config.get('INVOICE_COMPANY_CONTACT_INFO', "contact@maisontruvra.com | +33 1 23 45 67 89"),
        "company_logo_path": current_app.config.get('INVOICE_COMPANY_LOGO_PATH', "../website/image_6be700.png"), # Path relative to generate_professional_invoice.py
        "invoice_footer_text": current_app.config.get('INVOICE_FOOTER_TEXT', "Merci de votre confiance. Conditions de paiement : 30 jours net."),
        "bank_details": current_app.config.get('INVOICE_BANK_DETAILS', "Banque: XYZ | IBAN: FR76 ... | BIC: ...")
    }
    AuditLogService.log_event(action="ADMIN_VIEWED_INVOICE_TEMPLATE_SETTINGS", target_type="ADMIN_PANEL")
    return jsonify({"success": True, "settings": settings}), 200

@admin_api_bp.route('/settings/invoice-template', methods=['POST'])
@admin_required
def update_invoice_template_settings():
    data = request.get_json()
    # In a real app, validate and save these to the 'app_settings' table or update a config file (requires app restart for config file)
    # For simplicity, this is conceptual.
    # Example:
    # for key, value in data.items():
    #     if key in VALID_INVOICE_SETTINGS_KEYS:
    #         save_setting_to_db(key, value) # Your function to update DB
    AuditLogService.log_event(action="ADMIN_UPDATED_INVOICE_TEMPLATE_SETTINGS", target_type="ADMIN_PANEL", details=data)
    return jsonify({"success": True, "message": "Paramètres du modèle de facture (conceptuellement) mis à jour."}), 200


# Add other admin API routes (products, orders, inventory, dashboard data) here...
# Remember to add @admin_required and AuditLogService calls


