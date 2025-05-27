# backend/products/routes.py
from flask import Blueprint, request, jsonify, current_app
import json
from ..database import get_db # Importation relative

products_bp = Blueprint('products_bp', __name__, url_prefix='/api/products')

@products_bp.route('', methods=['GET']) # Route pour /api/products
def get_all_products():
    db = None
    try:
        db = get_db()
        cursor = db.cursor()
        category_filter = request.args.get('category')
        
        query = "SELECT id, name, category, short_description, image_url_main, base_price, stock_quantity FROM products"
        params = []
        
        if category_filter:
            query += " WHERE category = ?"
            params.append(category_filter)
            
        cursor.execute(query, params)
        products_rows = cursor.fetchall()
        
        products_list = []
        for row in products_rows:
            product_dict = dict(row)
            # Si base_price est None (produits avec options de poids), calculer le prix de départ et le stock total des options
            if product_dict['base_price'] is None:
                cursor.execute("SELECT MIN(price) as min_price, SUM(stock_quantity) as total_stock FROM product_weight_options WHERE product_id = ?", (product_dict['id'],))
                option_info = cursor.fetchone()
                product_dict['starting_price'] = option_info['min_price'] if option_info and option_info['min_price'] is not None else "N/A"
                # Le stock pour les produits à options est la somme des stocks des options
                product_dict['stock_quantity'] = option_info['total_stock'] if option_info and option_info['total_stock'] is not None else 0
            else:
                 product_dict['starting_price'] = product_dict['base_price']
                 # stock_quantity est déjà correct depuis la table products pour les produits simples

            products_list.append(product_dict)
            
        return jsonify(products_list)
    except Exception as e:
        current_app.logger.error(f"Erreur lors de la récupération des produits : {e}")
        return jsonify({"success": False, "message": "Erreur serveur lors de la récupération des produits."}), 500
    finally:
        if db:
            db.close()

@products_bp.route('/<string:product_id>', methods=['GET']) # Route pour /api/products/<product_id>
def get_product_by_id(product_id):
    db = None
    try:
        db = get_db()
        cursor = db.cursor()
        cursor.execute("SELECT * FROM products WHERE id = ?", (product_id,))
        product_row = cursor.fetchone()

        if product_row is None:
            return jsonify({"success": False, "message": "Produit non trouvé"}), 404

        product_dict = dict(product_row)
        
        # Gérer les options de poids si c'est un produit concerné
        if product_dict['category'] == 'Fresh Truffles' or product_dict['base_price'] is None:
            cursor.execute("SELECT option_id, weight_grams, price, stock_quantity FROM product_weight_options WHERE product_id = ? ORDER BY weight_grams ASC", (product_id,))
            weight_options_rows = cursor.fetchall()
            product_dict['weight_options'] = [dict(row_option) for row_option in weight_options_rows]
            # Le stock total pour l'affichage principal est la somme des stocks des options
            product_dict['stock_quantity'] = sum(wo['stock_quantity'] for wo in product_dict['weight_options'])
        
        # Convertir la chaîne JSON des URLs des miniatures en liste Python
        if product_dict.get('image_urls_thumb'):
            try:
                product_dict['image_urls_thumb'] = json.loads(product_dict['image_urls_thumb']) 
            except (json.JSONDecodeError, TypeError):
                current_app.logger.warning(f"Impossible de parser image_urls_thumb pour le produit {product_id}")
                product_dict['image_urls_thumb'] = [] # Fallback en cas d'erreur de parsing

        return jsonify(product_dict)
    except Exception as e:
        current_app.logger.error(f"Erreur lors de la récupération du produit {product_id}: {e}")
        return jsonify({"success": False, "message": "Erreur serveur lors de la récupération du produit."}), 500
    finally:
        if db:
            db.close()
