from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app.models import db, Task, User, Group, Friendship, user_group

tasks_bp = Blueprint('tasks', __name__)

@tasks_bp.context_processor
def inject_social_data():
    if current_user.is_authenticated:
        amizades = Friendship.query.filter(
            ((Friendship.user_id == current_user.id) | (Friendship.friend_id == current_user.id)),
            Friendship.status == 'accepted'
        ).all()
        amigos = [User.query.get(a.friend_id if a.user_id == current_user.id else a.user_id) for a in amizades]
        convites = Friendship.query.filter_by(friend_id=current_user.id, status='pending').all()
        return dict(sidebar_amigos=amigos, sidebar_grupos=current_user.groups, sidebar_convites=convites)
    return dict()

@tasks_bp.route('/')
@login_required
def home():
    tasks = Task.query.filter_by(user_id=current_user.id, group_id=None).all()
    return render_template('index.html', tasks=tasks)

@tasks_bp.route('/add', methods=['POST'])
@login_required
def add_task():
    titulo = request.form.get('title')
    if titulo:
        nova_tarefa = Task(title=titulo, user_id=current_user.id, group_id=None)
        db.session.add(nova_tarefa)
        db.session.commit()
        flash('Tarefa adicionada!', 'success')
    return redirect(url_for('tasks.home'))

@tasks_bp.route('/toggle/<int:task_id>', methods=['POST'])
@login_required
def toggle_task(task_id):
    tarefa = Task.query.get(task_id)
    if not tarefa: return redirect(request.referrer)
    
    if tarefa.group_id:
        membro = db.session.query(user_group).filter_by(user_id=current_user.id, group_id=tarefa.group_id).first()
        if not membro: return redirect(request.referrer)
    else:
        if tarefa.user_id != current_user.id: return redirect(request.referrer)

    tarefa.status = not tarefa.status
    db.session.commit()
    return redirect(request.referrer or url_for('tasks.home'))

@tasks_bp.route('/delete/<int:task_id>', methods=['POST'])
@login_required
def delete_task(task_id):
    tarefa = Task.query.get(task_id)
    if not tarefa: return redirect(request.referrer)

    if tarefa.group_id:
        membro = db.session.query(user_group).filter_by(user_id=current_user.id, group_id=tarefa.group_id).first()
        if not membro or (membro.role != 'admin' and tarefa.user_id != current_user.id):
            flash('Acesso negado para excluir.', 'error')
            return redirect(request.referrer)
    else:
        if tarefa.user_id != current_user.id: return redirect(request.referrer)

    db.session.delete(tarefa)
    db.session.commit()
    flash('Tarefa excluída!', 'success')
    return redirect(request.referrer or url_for('tasks.home'))

@tasks_bp.route('/description/<int:task_id>', methods=['POST'])
@login_required
def update_description(task_id):
    tarefa = Task.query.get(task_id)
    if not tarefa: return redirect(request.referrer)
    
    # Verifica permissão
    if tarefa.group_id:
        membro = db.session.query(user_group).filter_by(user_id=current_user.id, group_id=tarefa.group_id).first()
        if not membro: return redirect(request.referrer)
    else:
        if tarefa.user_id != current_user.id: return redirect(request.referrer)
        
    # Salva a nova descrição
    tarefa.description = request.form.get('description')
    db.session.commit()
    return redirect(request.referrer or url_for('tasks.home'))

@tasks_bp.route('/social')
@login_required
def social_dashboard():
    amizades = Friendship.query.filter(
        ((Friendship.user_id == current_user.id) | (Friendship.friend_id == current_user.id)),
        Friendship.status == 'accepted'
    ).all()
    amigos = [User.query.get(a.friend_id if a.user_id == current_user.id else a.user_id) for a in amizades]
    convites = Friendship.query.filter_by(friend_id=current_user.id, status='pending').all()
    return render_template('social.html', amigos=amigos, convites=convites, grupos=current_user.groups)

@tasks_bp.route('/social/friend/request', methods=['POST'])
@login_required
def send_friend_request():
    friend = User.query.filter_by(username=request.form.get('friend_username')).first()
    if not friend or friend.id == current_user.id:
        flash('Usuário inválido.', 'error')
        return redirect(url_for('tasks.social_dashboard'))
        
    existente = Friendship.query.filter(
        ((Friendship.user_id == current_user.id) & (Friendship.friend_id == friend.id)) |
        ((Friendship.user_id == friend.id) & (Friendship.friend_id == current_user.id))
    ).first()
    
    if existente:
        flash('Convite já enviado ou vocês já são amigos.', 'error')
    else:
        db.session.add(Friendship(user_id=current_user.id, friend_id=friend.id))
        db.session.commit()
        flash('Convite enviado!', 'success')
    return redirect(url_for('tasks.social_dashboard'))

@tasks_bp.route('/social/friend/accept/<int:friendship_id>', methods=['POST'])
@login_required
def accept_friend_request(friendship_id):
    convite = Friendship.query.get(friendship_id)
    if convite and convite.friend_id == current_user.id:
        convite.status = 'accepted'
        db.session.commit()
    return redirect(url_for('tasks.social_dashboard'))

@tasks_bp.route('/social/friend/reject/<int:friendship_id>', methods=['POST'])
@login_required
def reject_friend_request(friendship_id):
    convite = Friendship.query.get(friendship_id)
    if convite and convite.friend_id == current_user.id:
        db.session.delete(convite)
        db.session.commit()
    return redirect(url_for('tasks.social_dashboard'))

@tasks_bp.route('/social/friend/remove/<int:amigo_id>', methods=['POST'])
@login_required
def remove_friend(amigo_id):
    amizade = Friendship.query.filter(
        ((Friendship.user_id == current_user.id) & (Friendship.friend_id == amigo_id)) |
        ((Friendship.user_id == amigo_id) & (Friendship.friend_id == current_user.id))
    ).first()
    if amizade:
        db.session.delete(amizade)
        db.session.commit()
    return redirect(url_for('tasks.social_dashboard'))

@tasks_bp.route('/social/group/create', methods=['POST'])
@login_required
def create_group():
    nome = request.form.get('group_name')
    if nome:
        novo_grupo = Group(name=nome, creator_id=current_user.id)
        db.session.add(novo_grupo)
        db.session.flush()
        db.session.execute(user_group.insert().values(user_id=current_user.id, group_id=novo_grupo.id, role='admin'))
        db.session.commit()
        flash('Grupo criado!', 'success')
    return redirect(url_for('tasks.social_dashboard'))

@tasks_bp.route('/social/group/<int:group_id>')
@login_required
def group_board(group_id):
    membro = db.session.query(user_group).filter_by(user_id=current_user.id, group_id=group_id).first()
    if not membro: return redirect(url_for('tasks.social_dashboard'))
        
    grupo = Group.query.get(group_id)
    tarefas = Task.query.filter_by(group_id=group_id).all()
    membros_ids = [u.id for u in grupo.members]
    
    amizades = Friendship.query.filter(
        ((Friendship.user_id == current_user.id) | (Friendship.friend_id == current_user.id)),
        Friendship.status == 'accepted'
    ).all()
    amigos = [User.query.get(a.friend_id if a.user_id == current_user.id else a.user_id) for a in amizades]
    amigos_elegiveis = [a for a in amigos if a.id not in membros_ids]
            
    return render_template('group_board.html', grupo=grupo, tarefas=tarefas, meu_papel=membro.role, membros_grupo=grupo.members, amigos_elegiveis=amigos_elegiveis)

@tasks_bp.route('/social/group/<int:group_id>/add_member', methods=['POST'])
@login_required
def add_group_member(group_id):
    friend_id = request.form.get('friend_id')
    admin = db.session.query(user_group).filter_by(user_id=current_user.id, group_id=group_id, role='admin').first()
    if admin and friend_id:
        db.session.execute(user_group.insert().values(user_id=friend_id, group_id=group_id, role='member'))
        db.session.commit()
    return redirect(url_for('tasks.group_board', group_id=group_id))

@tasks_bp.route('/social/group/<int:group_id>/task', methods=['POST'])
@login_required
def create_group_task(group_id):
    if request.form.get('title'):
        db.session.add(Task(title=request.form.get('title'), user_id=current_user.id, group_id=group_id))
        db.session.commit()
    return redirect(url_for('tasks.group_board', group_id=group_id))

@tasks_bp.route('/social/group/<int:group_id>/leave', methods=['POST'])
@login_required
def leave_group(group_id):
    db.session.execute(user_group.delete().where(user_group.c.user_id == current_user.id).where(user_group.c.group_id == group_id))
    db.session.commit()
    if db.session.query(user_group).filter_by(group_id=group_id).count() == 0:
        db.session.delete(Group.query.get(group_id))
        db.session.commit()
    return redirect(url_for('tasks.social_dashboard'))

@tasks_bp.route('/social/group/<int:group_id>/delete', methods=['POST'])
@login_required
def delete_group(group_id):
    admin = db.session.query(user_group).filter_by(user_id=current_user.id, group_id=group_id, role='admin').first()
    if admin:
        db.session.delete(Group.query.get(group_id))
        db.session.commit()
        flash('Grupo deletado.', 'success')
    return redirect(url_for('tasks.social_dashboard'))

@tasks_bp.route('/settings', methods=['GET', 'POST'])
@login_required
def user_settings():
    if request.method == 'POST':
        current_user.theme = request.form.get('theme')
        db.session.commit()
        flash('Configurações salvas!', 'success')
        return redirect(url_for('tasks.user_settings'))
    return render_template('settings.html')