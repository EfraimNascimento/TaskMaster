from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from .models import db, Task, User, Group, Friendship, user_group

# Inicializa o Blueprint de tarefas
tasks_bp = Blueprint('tasks', __name__)

# 1. Injetor Global: Garante que a Sidebar tenha dados em qualquer tela!
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

# 2. Nova Rota de Configurações do Usuário
@tasks_bp.route('/settings', methods=['GET', 'POST'])
@login_required
def user_settings():
    if request.method == 'POST':
        novo_tema = request.form.get('theme')
        # Você precisará adicionar a coluna 'theme' no models.py -> User!
        current_user.theme = novo_tema 
        db.session.commit()
        flash('Configurações atualizadas com sucesso!', 'success')
        return redirect(url_for('tasks.user_settings'))
    return render_template('settings.html')

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
    
    # tasks = Task.query.filter_by(user_id=current_user.id).all()
    tasks = Task.query.filter_by(
        user_id=current_user.id, 
        group_id=None
    ).all()
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

@tasks_bp.route('/social')
@login_required
def social_dashboard():
    # 1. Busca os amigos (onde o status é 'accepted')
    amizades = Friendship.query.filter(
        ((Friendship.user_id == current_user.id) | (Friendship.friend_id == current_user.id)),
        Friendship.status == 'accepted'
    ).all()
    
    lista_amigos = []
    for a in amizades:
        amigo_id = a.friend_id if a.user_id == current_user.id else a.user_id
        lista_amigos.append(User.query.get(amigo_id))

    convites_pendentes = Friendship.query.filter_by(
        friend_id=current_user.id, 
        status='pending'
    ).all()

    # 2. Busca os grupos do usuário
    meus_grupos = current_user.groups 

    # 3. Envia os dados para a tela HTML usando o Jinja2
    return render_template(
        'social.html', 
        amigos=lista_amigos, 
        grupos=meus_grupos,
        convites=convites_pendentes
    )

@tasks_bp.route('/social/group/create', methods=['POST'])
@login_required
def create_group_html():
    nome_grupo = request.form.get('group_name')
    
    if nome_grupo:
        # Lógica idêntica à da API
        novo_grupo = Group(name=nome_grupo)
        db.session.add(novo_grupo)
        db.session.commit()
        
        stmt = user_group.insert().values(
            user_id=current_user.id, 
            group_id=novo_grupo.id, 
            role='admin'
        )
        db.session.execute(stmt)
        db.session.commit()
        
        # Avisa o usuário que deu certo (o Jinja2 exibe isso depois)
        flash('Grupo criado com sucesso!', 'success')
        
    # Diferente da API (que devolve JSON), o HTML faz um redirecionamento de tela
    return redirect(url_for('tasks.social_dashboard'))

@tasks_bp.route('/social/friend/request', methods=['POST'])
@login_required
def send_friend_request_html():
    friend_username = request.form.get('friend_username')
    
    # 1. Busca o amigo no banco de dados
    friend = User.query.filter_by(username=friend_username).first()
    
    if not friend:
        flash('Usuário não encontrado. Verifique o nome digitado.', 'error')
        return redirect(url_for('tasks.social_dashboard'))
        
    if friend.id == current_user.id:
        flash('Você não pode adicionar a si mesmo.', 'warning')
        return redirect(url_for('tasks.social_dashboard'))
        
    # 2. Verifica se a amizade ou um convite já existe
    amizade_existente = Friendship.query.filter(
        ((Friendship.user_id == current_user.id) & (Friendship.friend_id == friend.id)) |
        ((Friendship.user_id == friend.id) & (Friendship.friend_id == current_user.id))
    ).first()
    
    if amizade_existente:
        flash('Convite já enviado ou vocês já são amigos.', 'warning')
        return redirect(url_for('tasks.social_dashboard'))
        
    # 3. Cria e salva o convite pendente
    novo_convite = Friendship(user_id=current_user.id, friend_id=friend.id, status='pending')
    db.session.add(novo_convite)
    db.session.commit()
    
    flash(f'Convite enviado com sucesso para {friend.username}!', 'success')
    return redirect(url_for('tasks.social_dashboard'))

@tasks_bp.route('/social/friend/accept/<int:friendship_id>', methods=['POST'])
@login_required
def accept_friend_request_html(friendship_id):
    # Busca o convite garantindo que o usuário logado é realmente o destinatário
    convite = Friendship.query.filter_by(
        id=friendship_id, 
        friend_id=current_user.id, 
        status='pending'
    ).first()
    
    if not convite:
        flash('Convite não encontrado ou já processado.', 'error')
    else:
        # A mágica acontece aqui:
        convite.status = 'accepted'
        db.session.commit()
        flash(f'Você agora é amigo de {convite.sender.username}!', 'success')
        
    return redirect(url_for('tasks.social_dashboard'))

@tasks_bp.route('/social/friend/reject/<int:friendship_id>', methods=['POST'])
@login_required
def reject_friend_request_html(friendship_id):
    # Validação de segurança: garante que o convite é para o usuário logado e está pendente
    convite = Friendship.query.filter_by(
        id=friendship_id, 
        friend_id=current_user.id, 
        status='pending'
    ).first()
    
    if not convite:
        flash('Convite não encontrado ou já processado.', 'error')
    else:
        # Em vez de mudar o status, nós deletamos para manter o banco limpo
        db.session.delete(convite)
        db.session.commit()
        flash('Convite recusado e removido.', 'info')
        
    return redirect(url_for('tasks.social_dashboard'))

@tasks_bp.route('/social/friend/remove/<int:amigo_id>', methods=['POST'])
@login_required
def remove_friend_html(amigo_id):
    # Busca a amizade aceita, independente de quem foi o remetente original
    amizade = Friendship.query.filter(
        ((Friendship.user_id == current_user.id) & (Friendship.friend_id == amigo_id)) |
        ((Friendship.user_id == amigo_id) & (Friendship.friend_id == current_user.id)),
        Friendship.status == 'accepted'
    ).first()
    
    if not amizade:
        flash('Amizade não encontrada.', 'error')
    else:
        db.session.delete(amizade)
        db.session.commit()
        flash('Amizade desfeita com sucesso.', 'info')
        
    return redirect(url_for('tasks.social_dashboard'))

@tasks_bp.route('/social/group/<int:group_id>')
@login_required
def group_board(group_id):
    # 1. Verifica segurança: o usuário é membro?
    membro = db.session.query(user_group).filter(
        user_group.c.user_id == current_user.id,
        user_group.c.group_id == group_id
    ).first()
    
    if not membro:
        flash('Acesso negado. Você não é membro deste grupo.', 'error')
        return redirect(url_for('tasks.social_dashboard'))
        
    grupo = Group.query.get(group_id)
    tarefas = Task.query.filter_by(group_id=group_id).all()
    
    # 2. Separa os IDs de quem JÁ ESTÁ no grupo
    membros_atuais_ids = [u.id for u in grupo.members]
    
    # 3. Busca todos os amigos aprovados do usuário
    amizades = Friendship.query.filter(
        ((Friendship.user_id == current_user.id) | (Friendship.friend_id == current_user.id)),
        Friendship.status == 'accepted'
    ).all()
    
    amigos_elegiveis = []
    for a in amizades:
        amigo_id = a.friend_id if a.user_id == current_user.id else a.user_id
        # Só adiciona na lista de "convidáveis" se o amigo não estiver no grupo
        if amigo_id not in membros_atuais_ids:
            amigos_elegiveis.append(User.query.get(amigo_id))
            
    return render_template(
        'group_board.html', 
        grupo=grupo, 
        tarefas=tarefas, 
        meu_papel=membro.role,
        membros_grupo=grupo.members,
        amigos_elegiveis=amigos_elegiveis
    )

@tasks_bp.route('/social/group/<int:group_id>/add_member', methods=['POST'])
@login_required
def add_group_member_html(group_id):
    friend_id = request.form.get('friend_id')
    
    if not friend_id:
        flash('Nenhum amigo foi selecionado.', 'warning')
        return redirect(url_for('tasks.group_board', group_id=group_id))
        
    # 1. Regra de Negócio: Apenas o Administrador pode adicionar membros
    admin = db.session.query(user_group).filter(
        user_group.c.user_id == current_user.id,
        user_group.c.group_id == group_id,
        user_group.c.role == 'admin'
    ).first()
    
    if not admin:
        flash('Apenas administradores podem adicionar membros ao grupo.', 'error')
        return redirect(url_for('tasks.group_board', group_id=group_id))
        
    # 2. Insere o amigo na tabela invisível do grupo
    stmt = user_group.insert().values(user_id=friend_id, group_id=group_id, role='member')
    db.session.execute(stmt)
    db.session.commit()
    
    flash('Amigo adicionado à equipe com sucesso!', 'success')
    return redirect(url_for('tasks.group_board', group_id=group_id))

@tasks_bp.route('/social/group/<int:group_id>/task', methods=['POST'])
@login_required
def create_group_task_html(group_id):
    # Proteção: Apenas membros podem criar tarefas aqui
    membro = db.session.query(user_group).filter(
        user_group.c.user_id == current_user.id,
        user_group.c.group_id == group_id
    ).first()
    
    if not membro:
        flash('Acesso negado.', 'error')
        return redirect(url_for('tasks.social_dashboard'))
        
    titulo = request.form.get('title')
    if titulo:
        nova_tarefa = Task(
            title=titulo,
            user_id=current_user.id, # Quem criou
            group_id=group_id        # Onde foi criada
        )
        db.session.add(nova_tarefa)
        db.session.commit()
        flash('Tarefa adicionada ao quadro do grupo!', 'success')
        
    # Redireciona de volta para o quadro do grupo
    return redirect(url_for('tasks.group_board', group_id=group_id))

@tasks_bp.route('/social/task/<int:task_id>/toggle', methods=['POST'])
@login_required
def toggle_task_status_html(task_id):
    tarefa = Task.query.get(task_id)
    
    if not tarefa:
        flash('Tarefa não encontrada.', 'error')
        return redirect(request.referrer or url_for('tasks.social_dashboard'))
        
    # 1. Roteamento de Segurança (O mesmo da API)
    if tarefa.group_id:
        membro = db.session.query(user_group).filter(
            user_group.c.user_id == current_user.id,
            user_group.c.group_id == tarefa.group_id
        ).first()
        if not membro:
            flash('Acesso negado. Você não é membro deste grupo.', 'error')
            return redirect(url_for('tasks.social_dashboard'))
    else:
        if tarefa.user_id != current_user.id:
            flash('Acesso negado. Esta tarefa é privada e pertence a outra pessoa.', 'error')
            return redirect(url_for('tasks.social_dashboard'))
            
    # 2. O Efeito Interruptor (Inverte o booleano)
    tarefa.status = not tarefa.status
    db.session.commit()
    
    # 3. Volta exatamente para a página de onde o usuário veio
    return redirect(request.referrer or url_for('tasks.social_dashboard'))

@tasks_bp.route('/social/group/<int:group_id>/leave', methods=['POST'])
@login_required
def leave_group_html(group_id):
    membro = db.session.query(user_group).filter(
        user_group.c.user_id == current_user.id,
        user_group.c.group_id == group_id
    ).first()
    
    if not membro:
        flash('Você não faz parte deste grupo.', 'error')
        return redirect(url_for('tasks.social_dashboard'))
        
    # Desvincula o usuário do grupo
    stmt = user_group.delete().where(
        user_group.c.user_id == current_user.id,
        user_group.c.group_id == group_id
    )
    db.session.execute(stmt)
    db.session.commit()
    
    # Limpeza: Se o grupo ficou vazio, apaga ele
    membros_restantes = db.session.query(user_group).filter_by(group_id=group_id).count()
    if membros_restantes == 0:
        grupo_vazio = Group.query.get(group_id)
        if grupo_vazio:
            db.session.delete(grupo_vazio)
            db.session.commit()
            
    flash('Você saiu do grupo com sucesso.', 'info')
    return redirect(url_for('tasks.social_dashboard'))

@tasks_bp.route('/social/group/<int:group_id>/delete', methods=['POST'])
@login_required
def delete_group_html(group_id):
    admin = db.session.query(user_group).filter(
        user_group.c.user_id == current_user.id,
        user_group.c.group_id == group_id,
        user_group.c.role == 'admin'
    ).first()
    
    if not admin:
        flash('Acesso negado. Apenas administradores podem deletar o grupo.', 'error')
        return redirect(url_for('tasks.group_board', group_id=group_id))
        
    grupo = Group.query.get(group_id)
    if grupo:
        db.session.delete(grupo)
        db.session.commit()
        flash(f'O grupo "{grupo.name}" e suas tarefas foram deletados.', 'success')
        
    return redirect(url_for('tasks.social_dashboard'))

