from flask import Blueprint, render_template, request, redirect, url_for
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from .models import db, User

# Inicializa o Blueprint de autenticação
auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        hashed_password = generate_password_hash(password)
        new_user = User(username=username, password_hash=hashed_password)
        
        db.session.add(new_user)
        db.session.commit()
        # Redireciona para o login dentro deste mesmo blueprint (auth)
        return redirect(url_for('auth.login'))
        
    return render_template('register.html')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            # Redireciona para a home que está no blueprint 'tasks'
            return redirect(url_for('tasks.home'))
            
    return render_template('login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))

@auth_bp.route('/toggle-theme')
@login_required
def toggle_theme():
    # Inverte o valor do tema no banco de dados para o usuário atual
    current_user.dark_mode = not current_user.dark_mode
    db.session.commit()
    
    # request.referrer tenta devolver o usuário para a página em que ele clicou no botão
    # Se não conseguir, manda ele de volta pro dashboard (tasks.home)
    return redirect(request.referrer or url_for('tasks.home'))