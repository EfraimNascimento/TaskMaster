import os
from flask import Flask 
from flask_migrate import Migrate 
from flask_login import LoginManager 
from flask_jwt_extended import JWTManager 
from .models import db, User 
 
migrate = Migrate() 
login_manager = LoginManager() 
jwt = JWTManager()
 
# Esta é a Application Factory 
def create_app(): 
    app = Flask(__name__) 
    
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db' 
    
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'chave-local-de-desenvolvimento') 
    app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY', 'chave-jwt-local')
 
    # Conectamos as extensões ao app criado 
    db.init_app(app) 
    migrate.init_app(app, db, render_as_batch=True) 
    login_manager.init_app(app) 
    jwt.init_app(app) 
 
    # Note que agora o login_view aponta para o blueprint 'auth' 
    login_manager.login_view = 'auth.login' 
 
    @login_manager.user_loader 
    def load_user(user_id): 
        # AQUI ESTÁ A CORREÇÃO: Sintaxe moderna do SQLAlchemy 2.0!
        return db.session.get(User, int(user_id)) 
 
    # Importamos e registramos os Blueprints 
    from .auth import auth_bp 
    from .tasks import tasks_bp 
    from .api import api_bp 
 
    app.register_blueprint(auth_bp) 
    app.register_blueprint(tasks_bp) 
    app.register_blueprint(api_bp, url_prefix='/api/v1') 
 
    return app