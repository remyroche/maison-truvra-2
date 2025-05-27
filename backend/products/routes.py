# backend/products/routes.py
from flask import Blueprint, request, jsonify, current_app
import json
from ..database import get_db # Importation relative

products_bp = Blueprint('products_bp', __name__, url_prefix='/api/products')

@products_bp.route('', methods=['GET']) # Route pour /api/products# backend/products/routes.py
from flask import Blueprint, request, jsonify, current_app
import json
from ..database import get_db

products_bp = Blueprint('products_bp', __name__, url_prefix='/api/products')

def get_localized_field(lang, field_name_fr, field_name_en, row_data):
    """Helper to get localized field, defaulting to French if lang='en' is missing."""
    if lang == 'en' and row_data.get(field_name_en):
        return row_data[field_name_en]
    return row_data.get(field_name_fr) # Default to French


# Example for backend/products/routes.py
# Add to top: from ..auth.routes import professional_required (or a general login_required)

@products_bp.route('/<string:product_id>/reviews', methods=['GET'])
def get_product_reviews(product_id):
    # Fetch approved reviews for a product, with pagination
    db = get_db()
    cursor = db.cursor()
    # Add pagination later if needed
    cursor.execute("""
        SELECT pr.review_id, pr.rating, pr.comment_text, pr.review_date, u.prenom as user_prenom
        FROM product_reviews pr
        LEFT JOIN users u ON pr.user_id = u.id
        WHERE pr.product_id = ? AND pr.is_approved = TRUE
        ORDER BY pr.review_date DESC
    """, (product_id,))
    reviews = [dict(row) for row in cursor.fetchall()]
    db.close()
    return jsonify({"success": True, "reviews": reviews})

@products_bp.route('/<string:product_id>/reviews', methods=['POST'])
# @login_required # Decorator to ensure user is logged in (create this in auth/routes.py)
def submit_product_review(product_id):
    # Needs g.current_user_id from the login_required decorator
    user_id = getattr(g, 'current_user_id', None)
    if not user_id:
         return jsonify({"success": False, "message": "Vous devez être connecté pour laisser un avis."}), 401

    data = request.get_json()
    rating = data.get('rating')
    comment = data.get('comment_text', '')

    if not rating or not (1 <= int(rating) <= 5):
        return jsonify({"success": False, "message": "Une note entre 1 et 5 est requise."}), 400

    db = get_db()
    cursor = db.cursor()
    # Optional: Check if user already reviewed this product
    cursor.execute("INSERT INTO product_reviews (product_id, user_id, rating, comment_text) VALUES (?, ?, ?, ?)",
                   (product_id, user_id, int(rating), comment))
    db.commit()
    db.close()
    # In a real app, new reviews might go into a moderation queue (is_approved = FALSE by default)
    return jsonify({"success": True, "message": "Avis soumis avec succès. Il sera visible après approbation."}), 201
    
@products_bp.route('', methods=['GET'])
def get_all_products():
    db = None
    try:
        lang = request.args.get('lang', 'fr') # Default to French
        db = get_db()
        cursor = db.cursor()
        category_filter = request.args.get('category')

        # Select all necessary localized and non-localized fields
        query = f"""SELECT id, name_{lang} as name, category,
                    short_description_{lang} as short_description,
                    image_url_main, base_price, stock_quantity
                    FROM products"""
        params = []

        if category_filter:
            query += " WHERE category = ?"
            params.append(category_filter)

        cursor.execute(query, params)
        products_rows = cursor.fetchall()

        products_list = []
        for row in products_rows:
            product_dict = dict(row)
            if product_dict['base_price'] is None:
                cursor.execute("SELECT MIN(price) as min_price, SUM(stock_quantity) as total_stock FROM product_weight_options WHERE product_id = ?", (product_dict['id'],))
                option_info = cursor.fetchone()
                product_dict['starting_price'] = option_info['min_price'] if option_info and option_info['min_price'] is not None else "N/A"
                product_dict['stock_quantity'] = option_info['total_stock'] if option_info and option_info['total_stock'] is not None else 0
            else:
                product_dict['starting_price'] = product_dict['base_price']
            products_list.append(product_dict)

        return jsonify(products_list)
    except Exception as e:
        current_app.logger.error(f"Erreur lors de la récupération des produits (lang={lang}): {e}", exc_info=True)
        return jsonify({"success": False, "message": "Erreur serveur lors de la récupération des produits."}), 500
    finally:
        if db:
            db.close()

@products_bp.route('/<string:product_id>', methods=['GET'])
def get_product_by_id(product_id):
    db = None
    try:
        lang = request.args.get('lang', 'fr') # Default to French
        db = get_db()
        cursor = db.cursor()

        # Dynamically select localized fields
        fields_to_select = [
            "id", f"name_{lang} as name", "category",
            f"short_description_{lang} as short_description",
            f"long_description_{lang} as long_description",
            "image_url_main", "image_urls_thumb",
            f"species_{lang} as species", f"origin_{lang} as origin",
            f"seasonality_{lang} as seasonality", f"ideal_uses_{lang} as ideal_uses",
            f"sensory_description_{lang} as sensory_description",
            f"pairing_suggestions_{lang} as pairing_suggestions",
            "base_price", "stock_quantity", "is_published",
            "passport_url", "qr_code_path", "label_path"
        ]
        query = f"SELECT {', '.join(fields_to_select)} FROM products WHERE id = ?"
        cursor.execute(query, (product_id,))
        product_row = cursor.fetchone()

        if product_row is None:
            return jsonify({"success": False, "message": "Produit non trouvé"}), 404

        product_dict = dict(product_row)

        if product_dict['category'] == 'Fresh Truffles' or product_dict['base_price'] is None:
            cursor.execute("SELECT option_id, weight_grams, price, stock_quantity FROM product_weight_options WHERE product_id = ? ORDER BY weight_grams ASC", (product_id,))
            weight_options_rows = cursor.fetchall()
            product_dict['weight_options'] = [dict(row_option) for row_option in weight_options_rows]
            product_dict['stock_quantity'] = sum(wo['stock_quantity'] for wo in product_dict['weight_options'])

        if product_dict.get('image_urls_thumb'):
            try:
                product_dict['image_urls_thumb'] = json.loads(product_dict['image_urls_thumb'])
            except (json.JSONDecodeError, TypeError):
                product_dict['image_urls_thumb'] = []

        return jsonify(product_dict)
    except Exception as e:
        current_app.logger.error(f"Erreur lors de la récupération du produit {product_id} (lang={lang}): {e}", exc_info=True)
        return jsonify({"success": False, "message": "Erreur serveur lors de la récupération du produit."}), 500
    finally:
        if db:
            db.close()
