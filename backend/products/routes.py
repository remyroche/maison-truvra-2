# backend/products/routes.py
from flask import Blueprint, request, jsonify, current_app
import json
from ..database import get_db # Importation relative

products_bp = Blueprint('products_bp', __name__, url_prefix='/api/products')

@products_bp.route('', methods=['GET']) # Route pour /api/products# backend/products/routes.py
from flask import Blueprint, request, jsonify, current_app# backend/products/routes.py
from flask import Blueprint, request, jsonify, g, current_app
import sqlite3
from ..auth.routes import login_required # Import the decorator

products_bp = Blueprint('products_bp', __name__)

# --- Database Helper ---
def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(current_app.config['DATABASE'])
        db.row_factory = sqlite3.Row
    return db

# --- Routes ---
@products_bp.route('/api/products', methods=['GET'])
def get_products():
    db = get_db()
    lang = request.args.get('lang', 'fr') # Default to French
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 10, type=int)
    category_key = request.args.get('category_key')
    search_term = request.args.get('search')
    sort_by = request.args.get('sort_by', 'name_asc') # e.g. name_asc, name_desc, price_asc, price_desc

    offset = (page - 1) * limit

    name_col = f"p.name_{lang}"
    short_desc_col = f"p.short_description_{lang}"
    long_desc_col = f"p.long_description_{lang}"
    category_name_col = f"c.name_{lang}"

    query = f"""
        SELECT 
            p.id, {name_col} AS name, {short_desc_col} AS short_description, 
            p.base_price, p.currency, p.image_url_main, p.image_urls_thumb, 
            p.category_id, {category_name_col} AS category_name, p.weight_g,
            p.stock_quantity, p.is_featured, p.is_available,
            GROUP_CONCAT(DISTINCT t.name_{lang}) as tags
        FROM products p
        LEFT JOIN product_categories c ON p.category_id = c.id
        LEFT JOIN product_tags_assoc pta ON p.id = pta.product_id
        LEFT JOIN tags t ON pta.tag_id = t.id
        WHERE p.is_available = 1
    """
    params = []

    if category_key and category_key != 'all':
        query += f" AND c.key = ?"
        params.append(category_key)
    
    if search_term:
        # Search in name, short description, tags
        # For simplicity, we use OR here. For better relevance, full-text search (FTS5) would be better.
        search_like = f"%{search_term}%"
        query += f""" 
            AND (
                {name_col} LIKE ? OR 
                {short_desc_col} LIKE ? OR
                EXISTS (
                    SELECT 1 FROM product_tags_assoc pta_s 
                    JOIN tags t_s ON pta_s.tag_id = t_s.id 
                    WHERE pta_s.product_id = p.id AND t_s.name_{lang} LIKE ?
                )
            )
        """
        params.extend([search_like, search_like, search_like])

    query += " GROUP BY p.id"


    # Sorting
    if sort_by == 'name_asc':
        query += f" ORDER BY {name_col} ASC"
    elif sort_by == 'name_desc':
        query += f" ORDER BY {name_col} DESC"
    elif sort_by == 'price_asc':
        query += " ORDER BY p.base_price ASC"
    elif sort_by == 'price_desc':
        query += " ORDER BY p.base_price DESC"
    else: # Default sort
        query += f" ORDER BY p.is_featured DESC, {name_col} ASC"


    # Count total products for pagination
    # Note: This count query should ideally reflect the same filters as the main query for accuracy.
    # For simplicity in this example, a simpler count might be used or the main query run twice (once for count).
    # A more accurate count query:
    count_query_base = query.replace(query[query.find("SELECT"):query.find("FROM")], "SELECT COUNT(DISTINCT p.id) AS total ")
    count_query_base = count_query_base.split("ORDER BY")[0] # Remove ORDER BY for count
    # print("COUNT QUERY:", count_query_base, params)
    total_products_row = db.execute(count_query_base, tuple(params)).fetchone()
    total_products = total_products_row['total'] if total_products_row else 0
    total_pages = (total_products + limit - 1) // limit


    query += " LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    
    # current_app.logger.debug(f"Executing product query: {query} with params: {params}")
    products_cursor = db.execute(query, tuple(params))
    products_list = [dict(row) for row in products_cursor.fetchall()]

    # For each product, fetch its variants if any
    for product in products_list:
        variants_cursor = db.execute(f"""
            SELECT id, name_{lang} AS name, price, weight_g, stock_quantity 
            FROM product_variants 
            WHERE product_id = ? AND is_active = 1
            ORDER BY weight_g ASC
        """, (product['id'],))
        product['variants'] = [dict(row) for row in variants_cursor.fetchall()]
        if product['tags']:
            product['tags'] = product['tags'].split(',')
        else:
            product['tags'] = []


    return jsonify({
        'products': products_list,
        'current_page': page,
        'total_pages': total_pages,
        'total_products': total_products
    })


@products_bp.route('/api/products/<int:product_id>', methods=['GET'])
def get_product_detail(product_id):
    db = get_db()
    lang = request.args.get('lang', 'fr')

    name_col = f"name_{lang}"
    short_desc_col = f"short_description_{lang}"
    long_desc_col = f"long_description_{lang}"
    category_name_col = f"c.name_{lang}"

    product_row = db.execute(f"""
        SELECT 
            p.id, {name_col} AS name, 
            p.name_en, p.name_fr, /* include base names for fallback */
            {short_desc_col} AS short_description, 
            p.short_description_en, p.short_description_fr,
            {long_desc_col} AS long_description, 
            p.long_description_en, p.long_description_fr,
            p.base_price, p.currency, p.image_url_main, p.image_urls_thumb, 
            p.category_id, {category_name_col} AS category_name, c.key as category_key, p.weight_g,
            p.stock_quantity, p.is_featured, p.is_available,
            GROUP_CONCAT(DISTINCT t.name_{lang}) as tags
        FROM products p
        LEFT JOIN product_categories c ON p.category_id = c.id
        LEFT JOIN product_tags_assoc pta ON p.id = pta.product_id
        LEFT JOIN tags t ON pta.tag_id = t.id
        WHERE p.id = ? AND p.is_available = 1
        GROUP BY p.id
    """, (product_id,)).fetchone()

    if product_row is None:
        return jsonify({'message': 'Product not found or not available'}), 404

    product = dict(product_row)
    
    # Fetch variants
    variants_cursor = db.execute(f"""
        SELECT id, name_{lang} AS name, name_fr, name_en, price, weight_g, stock_quantity 
        FROM product_variants 
        WHERE product_id = ? AND is_active = 1
        ORDER BY weight_g ASC
    """, (product_id,))
    product['variants'] = [dict(row) for row in variants_cursor.fetchall()]
    
    if product['tags']:
        product['tags'] = product['tags'].split(',')
    else:
        product['tags'] = []

    return jsonify(product)

@products_bp.route('/api/products/<int:product_id>/reviews', methods=['GET'])
def get_product_reviews(product_id):
    db = get_db()
    # We can add pagination later if needed
    reviews_cursor = db.execute("""
        SELECT pr.id, pr.user_id, u.name AS user_name, pr.rating, pr.comment, pr.created_at, pr.is_approved
        FROM product_reviews pr
        LEFT JOIN users_b2c u ON pr.user_id = u.id -- Assuming reviews are by B2C users
        WHERE pr.product_id = ? 
        ORDER BY pr.created_at DESC
    """, (product_id,))
    reviews = [dict(row) for row in reviews_cursor.fetchall()]
    return jsonify({'reviews': reviews})


@products_bp.route('/api/products/<int:product_id>/reviews', methods=['POST'])
@login_required # Ensures user is logged in, g.current_user_id and g.current_user_role are set
def submit_product_review(product_id):
    db = get_db()
    user_id = g.current_user_id
    user_role = g.current_user_role # g.current_user set by login_required

    # Typically, only B2C users might leave reviews, or any authenticated user.
    # Let's assume B2C for now, but you can adjust this.
    if user_role != 'b2c':
         # Or if you want to allow B2B to review, you might need a different user_name source
        return jsonify({'message': 'Only registered customers can submit reviews.'}), 403
    
    # Check if the product exists
    product = db.execute("SELECT id FROM products WHERE id = ? AND is_available = 1", (product_id,)).fetchone()
    if not product:
        return jsonify({'message': 'Product not found or not available for review.'}), 404

    data = request.get_json()
    rating = data.get('rating')
    comment = data.get('comment')

    if not rating or not isinstance(rating, int) or not (1 <= rating <= 5):
        return jsonify({'message': 'Rating must be an integer between 1 and 5.'}), 400
    if not comment or len(comment.strip()) < 5:
        return jsonify({'message': 'Comment must be at least 5 characters long.'}), 400
    
    # Check if user already reviewed this product (optional, depends on policy)
    # existing_review = db.execute("SELECT id FROM product_reviews WHERE product_id = ? AND user_id = ?", (product_id, user_id)).fetchone()
    # if existing_review:
    #     return jsonify({'message': 'You have already reviewed this product.'}), 409

    try:
        # user_name is fetched from users_b2c table via JOIN in GET, not stored directly in product_reviews
        cursor = db.execute("""
            INSERT INTO product_reviews (product_id, user_id, rating, comment, is_approved)
            VALUES (?, ?, ?, ?, ?)
        """, (product_id, user_id, rating, comment, False)) # Reviews are not approved by default
        db.commit()
        review_id = cursor.lastrowid
        # The AuditLogService should be used here if available
        # AuditLogService().log_action(user_id, 'SUBMIT_REVIEW', f"Product ID: {product_id}, Review ID: {review_id}", role=user_role)
        return jsonify({'message': 'Review submitted successfully. It will be visible after approval.', 'review_id': review_id}), 201
    except Exception as e:
        current_app.logger.error(f"Error submitting review: {e}")
        return jsonify({'message': 'Failed to submit review due to a server error.'}), 500


@products_bp.route('/api/product-categories', methods=['GET'])
def get_product_categories():
    db = get_db()
    lang = request.args.get('lang', 'fr')
    name_col = f"name_{lang}"
    
    categories_cursor = db.execute(f"SELECT id, key, {name_col} AS name, description_{lang} AS description FROM product_categories ORDER BY display_order ASC, {name_col} ASC")
    categories = [dict(row) for row in categories_cursor.fetchall()]
    return jsonify({'categories': categories})

@products_bp.route('/api/tags', methods=['GET'])
def get_tags():
    db = get_db()
    lang = request.args.get('lang', 'fr')
    name_col = f"name_{lang}"

    tags_cursor = db.execute(f"SELECT id, {name_col} AS name FROM tags ORDER BY {name_col} ASC")
    tags = [dict(row) for row in tags_cursor.fetchall()]
    return jsonify({'tags': tags})
