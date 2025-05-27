import sqlite3
from flask import request, g, current_app
from datetime import datetime
import json

class AuditLogService:
    def __init__(self, app):
        self.app = app
        # No direct db connection here, use Flask's g or app context for requests

    def _get_db(self):
        # Helper to get DB connection, assuming flask g is used
        # This relies on the database connection being managed by Flask's app context
        # as set up in database.py and __init__.py
        if 'db_conn' not in g:
            # This case should ideally not happen if db is managed per request
            # For robustness, try to get it from current_app if possible,
            # but this service should be called within a request context.
            db_path = current_app.config['DATABASE_PATH']
            g.db_conn = sqlite3.connect(db_path)
            g.db_conn.row_factory = sqlite3.Row
        return g.db_conn


    def log_action(self, action: str, user_id: int = None, username: str = None, 
                   target_type: str = None, target_id: int = None, 
                   details: dict = None, success: bool = None):
        """
        Logs an action to the audit_log table.

        :param action: Description of the action (e.g., 'user_login', 'product_created').
        :param user_id: ID of the user performing the action.
        :param username: Username or email of the user (denormalized).
        :param target_type: Type of the entity being affected (e.g., 'product', 'order').
        :param target_id: ID of the affected entity.
        :param details: A dictionary with additional information about the event.
        :param success: Optional boolean to indicate if the action was successful.
        """
        if not self.app:
            print("AuditLogService: Flask app not initialized. Skipping log.")
            return

        try:
            # Use current_app.app_context() if called outside a request,
            # but typically this will be within a request.
            # with self.app.app_context(): # Not always needed if already in context
            db = self._get_db() # Uses g.db_conn
            cursor = db.cursor()

            ip_address = request.remote_addr if request else None
            
            current_timestamp = datetime.utcnow()

            # Prepare details for storage
            log_details = {}
            if details:
                log_details.update(details)
            if success is not None:
                log_details['success'] = success
            
            details_json = json.dumps(log_details) if log_details else None

            # Attempt to get username if user_id is provided and username is not
            if user_id and not username:
                try:
                    user_cursor = db.cursor()
                    user_cursor.execute("SELECT email FROM users WHERE id = ?", (user_id,))
                    user_row = user_cursor.fetchone()
                    if user_row:
                        username = user_row['email']
                except Exception as e_user:
                    self.app.logger.error(f"AuditLog: Could not fetch username for user_id {user_id}: {e_user}")


            sql = """
                INSERT INTO audit_log (timestamp, user_id, username, action, target_type, target_id, details, ip_address)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """
            cursor.execute(sql, (current_timestamp, user_id, username, action, target_type, target_id, details_json, ip_address))
            db.commit()
            self.app.logger.info(f"Audit Log: {action} by user {username or user_id or 'System'} - Details: {details_json}")

        except sqlite3.Error as e_sql:
            self.app.logger.error(f"AuditLogService: Database error logging action '{action}': {e_sql}")
        except Exception as e:
            # Catch any other exceptions to prevent logging failure from crashing the app
            self.app.logger.error(f"AuditLogService: Error logging action '{action}': {e}")

# Example usage (would be in your routes):
# from flask import current_app
# current_app.audit_log_service.log_action(
#     action='user_login_attempt', 
#     username=form.email.data, 
#     details={'reason': 'invalid_credentials'},
#     success=False
# )
# current_app.audit_log_service.log_action(
#     action='product_created', 
#     user_id=current_user.id, # Assuming current_user
#     username=current_user.email,
#     target_type='product',
#     target_id=new_product_id,
#     details={'name': product_name, 'sku': product_sku}
#     success=True
# )
