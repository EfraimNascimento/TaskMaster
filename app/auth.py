from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required
from app.models import db, User

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form['username']).first()
        if user and user.check_password(request.form['password']):
            login_user(user)
            return redirect(url_for('tasks.home'))
        flash('Usuário ou senha incorretos.', 'error')
    return render_template('login.html')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        if User.query.filter_by(username=request.form['username']).first():
            flash('Este usuário já existe.', 'error')
        else:
            novo_usuario = User(username=request.form['username'])
            novo_usuario.set_password(request.form['password'])
            db.session.add(novo_usuario)
            db.session.commit()
            flash('Conta criada! Faça login.', 'success')
            return redirect(url_for('auth.login'))
    return render_template('register.html')

# @tasks_bp.route('/description/<int:task_id>', methods=['POST'])
# @login_required
# def update_description(task_id):
#     tarefa = Task.query.get(task_id)
#     if not tarefa: return redirect(request.referrer)
    
#     # Verifica permissão
#     if tarefa.group_id:
#         membro = db.session.query(user_group).filter_by(user_id=current_user.id, group_id=tarefa.group_id).first()
#         if not membro: return redirect(request.referrer)
#     else:
#         if tarefa.user_id != current_user.id: return redirect(request.referrer)
        
#     # Salva a nova descrição
#     tarefa.description = request.form.get('description')
#     db.session.commit()
#     return redirect(request.referrer or url_for('tasks.home'))

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))