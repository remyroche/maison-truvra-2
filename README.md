# Maison Trüvra E-Commerce Project

Maison Trüvra is a Flask and JavaScript-based e-commerce web application designed for selling truffles and related luxury food products. This project includes a backend API for managing products, inventory, users, orders, and newsletter subscriptions, as well as a frontend website for customer interaction.

## Features

**Backend (Flask):**
* **Product Management:** API endpoints for listing products, viewing product details (including variants like different weights).
* **Inventory Tracking:** Detailed inventory movements (additions, sales, adjustments) are recorded. Stock levels are updated automatically upon sales or manual adjustments.
* **User Authentication:** User registration and login with password hashing. JWT (JSON Web Tokens) are used for session management.
* **Order Processing:** Checkout process that validates stock, calculates totals, and records customer orders.
* **Newsletter Subscription:** Allows users to subscribe to a newsletter.
* **Database:** Uses SQLite for data persistence. Includes tables for products, product options, users, orders, order items, newsletter subscriptions, and inventory movements.
* **Structure:** Organized using Flask Blueprints for modularity (auth, products, orders, newsletter, inventory).
* **CORS:** Configured for handling cross-origin requests.

**Frontend (HTML, Tailwind CSS, JavaScript):**
* **Customer-Facing Website:**
    * Homepage, Product Listing (with category filtering), Product Detail pages.
    * Shopping Cart functionality (add, update quantity, remove items).
    * Checkout process (simulated payment).
    * User Account page (login, registration placeholders, basic dashboard for logged-in users).
    * Informational pages: "Notre Histoire", "Professionnels", "Politique de Confidentialité".
* **Dynamic Content:** JavaScript is used to fetch data from the backend API and render it dynamically on the pages.
* **Styling:** Utilizes Tailwind CSS for a modern and responsive design.
* **User Experience:** Includes mobile-friendly navigation, global notifications/toasts, and modals.

**Supporting Scripts:**
* `generate_label.py`: Generates PNG product labels with product information and a QR code area using the Pillow library.
* `generate_passport_html.py`: Creates HTML "passports" for products, providing detailed traceability and information, intended to be linked from QR codes.

## Project Structure
maison-truvra-project/
├── backend/                    # Flask backend application
│   ├── auth/                   # Authentication blueprint
│   ├── inventory/              # Inventory management blueprint
│   ├── newsletter/             # Newsletter subscription blueprint
│   ├── orders/                 # Order processing blueprint
│   ├── products/               # Product management blueprint
│   ├── static/                 # (Optional) Static files for backend if any
│   ├── templates/              # (Optional) Templates for backend if any
│   ├── init.py             # Application factory
│   ├── config.py               # Configuration settings
│   ├── database.py             # Database initialization and helpers
│   └── run.py                  # Script to run the Flask development server
│   └── utils.py                # Backend utility functions
├── website/                    # Frontend HTML, CSS, JS
│   ├── css/                    # (Optional) Custom CSS files
│   ├── images/                 # Static images for the website (e.g., logo)
│   ├── js/                     # (Could move scripts.js here)
│   │   └── scripts.js          # Main JavaScript file for frontend logic
│   ├── index.html
│   ├── nos-produits.html
│   ├── produit-detail.html
│   ├── panier.html
│   ├── compte.html
│   ├── paiement.html           # Checkout page
│   ├── confirmation-commande.html # Order confirmation page
│   └── ... (other HTML pages)
├── output_test_labels/         # Example output directory for generate_label.py
├── output_test_passports/      # Example output directory for generate_passport_html.py
├── maison_truvra.db            # SQLite database file (created by backend)
├── generate_label.py           # Script to generate product labels
├── generate_passport_html.py   # Script to generate HTML product passports
├── utils.py                    # Shared utility functions (e.g., for date formatting)
├── requirements.txt            # Python dependencies
└── README.md


## Setup and Installation

**Prerequisites:**
* Python 3.7+
* pip (Python package installer)

**1. Clone the Repository:**
   ```bash
   git clone <repository-url>
   cd maison-truvra-project

