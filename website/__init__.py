import os

from flask import Flask, redirect, url_for, request, flash
from flask_sqlalchemy import SQLAlchemy
from os import path
from flask_login import LoginManager, current_user

db = SQLAlchemy()
DB_NAME = "database.db"

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'd5f8@!2XkN9vQzL1j7z#Tp8mH3bR5Yw6'
    DATABASE_URL = os.getenv('DATABASE_URL', f"sqlite:///{DB_NAME}")
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)

    from .views import views
    from .auth import auth

    app.register_blueprint(views, url_prefix='/')
    app.register_blueprint(auth, url_prefix='/')

    from .models import User, Note, Info
    
    with app.app_context():
        db.create_all()

    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.init_app(app)

    @app.context_processor
    def inject_user():
        from flask_login import current_user
        return {'user': current_user}

    @login_manager.user_loader
    def load_user(id):
        return User.query.get(int(id))

    @app.before_request
    def require_info_submission():
        from flask import current_app, redirect, url_for
        from flask_login import current_user
        from website.models import Info

        # Only apply this restriction if the user is logged in
        if current_user.is_authenticated:
            # Check if the current user has submitted the required information
            with current_app.app_context():
                user_info = Info.query.filter_by(user_id=current_user.id).first()

            # If no information is submitted and the user is not already on the /info or static assets
            if not user_info and request.endpoint != 'views.info' and not request.endpoint.startswith('static'):
                flash('You must input your information first', category='error')
                # Redirect user to the /info page
                return redirect(url_for('views.info'))

    @app.context_processor
    def inject_info():
        if current_user.is_authenticated:
            user_info = Info.query.filter_by(user_id=current_user.id).first()
            return {'info': user_info}
        return {'info': None}

    return app


def create_database(app):
    if not path.exists('website/' + DB_NAME):
        db.create_all(app=app)
        print('Created Database!')
