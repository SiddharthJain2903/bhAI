import os
from flask import Flask, jsonify
from markupsafe import Markup
from flask_login import LoginManager
from flask_bcrypt import Bcrypt
from sqlalchemy import text, inspect

from config import Config
from models import db, User
from render import render_markdown

bcrypt = Bcrypt()
login_manager = LoginManager()


def _ensure_attachment_columns(app):
    """
    db.create_all() only creates missing TABLES, not missing COLUMNS on a
    table that already exists. Since existing users already have a message
    table from before file uploads were added, this adds the new attachment
    columns to their existing database in place, so nobody has to delete
    their chat history to get the new feature.
    """
    with app.app_context():
        inspector = inspect(db.engine)
        if "message" not in inspector.get_table_names():
            return  # fresh install — db.create_all() already built the full table

        existing_columns = {col["name"] for col in inspector.get_columns("message")}
        new_columns = {
            "attachment_name": "VARCHAR(255)",
            "attachment_path": "VARCHAR(500)",
            "attachment_kind": "VARCHAR(20)",
        }
        with db.engine.connect() as conn:
            for name, col_type in new_columns.items():
                if name not in existing_columns:
                    conn.execute(text(f"ALTER TABLE message ADD COLUMN {name} {col_type}"))
            conn.commit()


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Please log in to access bhAI."
    login_manager.login_message_category = "error"

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    from auth import auth_bp
    from chat import chat_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(chat_bp)

    with app.app_context():
        db.create_all()

    _ensure_attachment_columns(app)

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    # Lets templates show saved replies as clean formatted text: {{ m.content|markdown }}
    app.jinja_env.filters["markdown"] = lambda text: Markup(render_markdown(text))

    @app.errorhandler(413)
    def file_too_large(_e):
        return jsonify({"error": f"That file is too large (max {app.config['MAX_UPLOAD_MB']} MB)."}), 413

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True, port=5000)
