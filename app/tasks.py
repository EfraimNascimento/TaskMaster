from flask import Blueprint, render_template, request, redirect, url_for
from flask_login import login_required, current_user
from .models import db, Task

# Inicializa o Blueprint de tarefas
tasks_bp = Blueprint('tasks', __name__)

@tasks_bp.route('/', methods=['GET', 'POST'])
@login_required
def home():
    if request.method == 'POST':
        task_title = request.form.get('title')
        task_desc = request.form.get('description')
        
        if task_title:
            new_task = Task(title=task_title, description=task_desc, user_id=current_user.id)
            db.session.add(new_task)
            db.session.commit()
        return redirect(url_for('tasks.home'))
    
    tasks = Task.query.filter_by(user_id=current_user.id).all()
    return render_template('index.html', framework_name="Flask", tasks=tasks)

@tasks_bp.route('/toggle/<int:task_id>')
@login_required
def toggle_task(task_id):
    # Busca a tarefa garantindo que ela pertence ao usuário logado
    task = Task.query.filter_by(id=task_id, user_id=current_user.id).first()

    if task:
        # Inverte o status booleano
        task.status = not task.status
        db.session.commit()

    # Redireciona de volta para o dashboard
    return redirect(url_for('tasks.home'))

@tasks_bp.route('/delete/<int:task_id>')
@login_required
def delete_task(task_id):
    # Busca a tarefe garantindo que ela pertence ao usuário atual
    task = Task.query.filter_by(id=task_id, user_id=current_user.id).first()

    if task:
        db.session.delete(task)
        db.session.commit()

    return redirect(url_for('tasks.home'))
