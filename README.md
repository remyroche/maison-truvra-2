# Maison Trüvra - E-commerce Platform

## Description

Maison Trüvra is a full-stack e-commerce platform designed for selling artisanal products. It features a customer-facing website for browsing and purchasing products, and a comprehensive admin panel for managing inventory, orders, users, and more. A key innovation of this platform is its **serialized inventory management system**, where each individual item receives a unique identifier (UID), a QR code, and a digital "passport" detailing its origin and characteristics. This provides enhanced traceability and authenticity for customers.

The platform supports both B2C (Business-to-Consumer) and B2B (Business-to-Business) functionalities, including professional invoicing for B2B clients.

## Key Features

* **Customer-Facing Website:**
    * Product browsing with categories and search.
    * Detailed product pages.
    * Shopping cart and checkout functionality.
    * User account management (registration, login, order history, password reset).
    * Internationalization (i18n) support (English & French).
    * Newsletter subscription.
    * Responsive design.
* **Admin Panel:**
    * Dashboard with key metrics.
    * Product management (CRUD operations, simple & variable products, image uploads).
    * **Serialized Inventory Management:**
        * Reception of serialized stock.
        * Automatic generation of unique item UIDs.
        * Generation of QR codes for each item.
        * Creation of HTML-based "Digital Passports" for item traceability.
    * Category management.
    * Order management and tracking.
    * User management (B2C and B2B).
    * Review management.
    * Invoice management (including PDF generation for B2B).
* **Backend & API:**
    * Secure RESTful API built with Flask.
    * JWT-based authentication for users and admins.
    * Role-based access control (admin, B2C user, B2B professional).
    * Email verification and password reset.
    * Database management with SQLite.
    * Audit logging for important actions.
* **Digital Passports:**
    * Each serialized item is linked to a unique digital passport accessible via its UID or QR code.
    * Provides detailed information about the item's provenance, materials, and history.

## Technologies Used

* **Backend:**
    * Python
    * Flask (web framework)
    * Flask-SQLAlchemy (ORM)
    * Flask-JWT-Extended (Authentication)
    * Flask-CORS
    * SQLite (Database)
    * ReportLab (for PDF invoice generation)
    * qrcode (for QR code generation)
* **Frontend (Website & Admin Panel):**
    * HTML5
    * CSS3 (Tailwind CSS framework)
    * JavaScript (Vanilla JS)
* **Other Tools:**
    * `requests` (for HTTP requests, potentially for payment gateway integration - not fully implemented)

## Project Structure


maison-truvra-2/
├── admin/                      # Admin panel static HTML/CSS (some JS misplaced here)
│   ├── generate_professional_invoice.py # Script for B2B invoice PDF
│   └── ...
├── backend/
│   ├── admin_api/              # Admin-specific API routes
│   ├── auth/                   # Authentication routes
│   ├── config.py               # Configuration settings
│   ├── database.py             # Database setup and schema
│   ├── db_init_seed.py         # Database initialization and seeding script
│   ├── inventory/              # Serialized inventory management routes
│   ├── newsletter/             # Newsletter subscription routes
│   ├── orders/                 # Order processing routes
│   ├── passport/               # Digital passport viewing routes
│   ├── products/               # Product management routes (public)
│   ├── professional/           # B2B professional user routes
│   ├── run.py                  # Main Flask application runner
│   ├── services/               # Business logic services (AssetService, InvoiceService)
│   ├── static/                 # Static files (e.g., uploaded product images)
│   ├── templates/              # Email templates
│   └── utils.py                # Utility functions
├── website/
│   ├── admin/                  # Admin panel HTML pages and some JS
│   │   ├── js/                 # Admin panel JavaScript files (intended location)
│   │   └── admin_login.html
│   ├── css/                    # (Potentially for compiled Tailwind CSS for website)
│   ├── img/                    # Website images
│   ├── js/                     # Website JavaScript
│   │   ├── locales/            # i18n JSON files (en.json, fr.json)
│   │   └── ...
│   ├── *.html                  # Website HTML pages
│   └── scripts.js              # Main script loader for website
├── audit_log_service.py        # Centralized audit logging
├── generate_label.py           # Script for generating product labels (likely with QR)
├── generate_passport_html.py   # Script for generating HTML for digital passports
└── README.md                   # This file


## Setup and Installation

### Prerequisites

* Python 3.x
* pip (Python package installer)
* Node.js and npm (if you need to rebuild Tailwind CSS, especially for the admin panel)

### Backend Setup

1.  **Clone the repository (if applicable):**
    ```bash
    git clone <repository_url>
    cd maison-truvra-2
    ```
2.  **Create and activate a virtual environment (recommended):**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```
3.  **Install Python dependencies:**
    ```bash
    pip install Flask Flask-SQLAlchemy Flask-JWT-Extended Flask-CORS Pillow qrcode reportlab requests python-dotenv
    ```
    *(Note: `python-dotenv` might be useful if you plan to use `.env` files for configuration, though not explicitly used in `config.py` yet).*
4.  **Initialize the Database:**
    * Navigate to the `backend` directory: `cd backend`
    * Run the database initialization script. This will create `maison_truvra.db` and seed it with initial data.
        ```bash
        python db_init_seed.py
        ```
        *Ensure this script correctly creates all tables as defined in `database.py` and `schema.sql` (embedded).*

### Frontend Setup

1.  **Website:**
    * The website frontend (`website/` directory) consists of static HTML, CSS, and JavaScript files. It should work by opening `website/index.html` in a browser, provided the backend is running and accessible.
    * Ensure the `API_BASE_URL` in `website/js/config.js` points to your running backend (e.g., `http://127.0.0.1:5000`).
2.  **Admin Panel:**
    * The admin panel also uses static files.
    * **Tailwind CSS Build (Important):** The `admin/admin_styles.css` file uses Tailwind CSS's `@apply` directives. This file needs to be processed by Tailwind CSS to generate a usable CSS file.
        * If not already set up, you'll need to install Tailwind CSS:
            ```bash
            npm install -D tailwindcss postcss autoprefixer
            npx tailwindcss init
            ```
        * Configure `tailwind.config.js` to include paths to your admin HTML files:
            ```js
            // tailwind.config.js
            module.exports = {
              content: [
                "./admin/**/*.html",
                "./website/admin/**/*.html", // If JS for admin is also in HTML
                "./website/admin/js/**/*.js",
              ],
              theme: {
                extend: {},
              },
              plugins: [],
            }
            ```
        * Create a source CSS file (e.g., `admin/src/input.css`) that imports Tailwind and your custom styles:
            ```css
            /* admin/src/input.css */
            @tailwind base;
            @tailwind components;
            @tailwind utilities;

            /* Import your custom admin styles */
            @import "../admin_styles.css"; /* Or move content of admin_styles.css here */
            ```
        * Run the Tailwind CLI to build your CSS:
            ```bash
            npx tailwindcss -i ./admin/src/input.css -o ./admin/dist/output.css --watch
            ```
        * Update your admin HTML files to link to the generated `output.css` (e.g., `<link rel="stylesheet" href="dist/output.css">`).
    * Ensure the `API_BASE_URL` in `website/admin/js/admin_api.js` (or equivalent config for admin) points to your backend.

## Running the Application

1.  **Start the Backend Server:**
    * Navigate to the `backend` directory: `cd backend`
    * Run the Flask application:
        ```bash
        python run.py
        ```
    * The backend server will typically start on `http://127.0.0.1:5000`.

2.  **Access the Website:**
    * Open `website/index.html` in your web browser.

3.  **Access the Admin Panel:**
    * Open `website/admin/admin_login.html` (or the main admin dashboard page if login is bypassed for development) in your web browser.
    * Default admin credentials (if seeded by `db_init_seed.py`): Check the seeding script. Often `admin@example.com` / `adminpassword`.

## API Endpoints

The backend provides a comprehensive set of RESTful API endpoints. Key blueprints include:

* `/auth/...` - Authentication and user management.
* `/products/...` - Public product listings.
* `/orders/...` - Order creation and management.
* `/professional/...` - B2B specific functionalities.
* `/newsletter/...` - Newsletter subscriptions.
* `/passport/...` - Accessing digital passports.
* `/api/admin/...` - Admin-specific operations for managing products, inventory, users, orders, etc.

Refer to the route definitions in the `backend` subdirectories (e.g., `backend/admin_api/routes.py`, `backend/products/routes.py`) for detailed endpoint specifications.

## Current Status & Known Issues

* **Backend:** Largely functional and feature-rich.
    * The `InvoiceService` (`backend/services/invoice_service.py`) currently has a placeholder for PDF generation. The logic from `admin/generate_professional_invoice.py` needs to be fully integrated here.
* **Website Frontend (B2C):** Appears to be mostly complete and functional.
* **Admin Panel Frontend:**
    * **Critical:** JavaScript files are disorganized. Several HTML files in `admin/` and `website/admin/` contain JavaScript logic that should be in dedicated `.js` files within `website/admin/js/`. This needs significant refactoring for the admin panel to be functional.
    * Some JavaScript files for admin functionality (e.g., `admin_auth.js`, `admin_inventory.js`, `admin_orders.js`) appear to be missing or incomplete.
    * Requires a Tailwind CSS build step for `admin/admin_styles.css` to be correctly applied.

## Future Enhancements (Suggestions)

* Integrate a real payment gateway (e.g., Stripe, PayPal).
* Improve error handling and user feedback on the frontend.
* Add more comprehensive unit and integration tests for backend and frontend.
* Implement advanced analytics for the admin dashboard.
* Refine the UI/UX for both the website and admin panel.
* Containerize the application using Docker for easier deployment.
* Implement WebSocket for real-time admin updates.
