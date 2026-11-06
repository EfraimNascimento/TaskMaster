from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from werkzeug.security import check_password_hash
from .models import db, User, Task, Friendship, Group, user_group

api_bp = Blueprint('api', __name__)

# ROTA 1: Login para gerar o Token JWT
@api_bp.route('/login', methods=['POST'])
def login():
    dados = request.get_json()
    if not dados or 'username' not in dados or 'password' not in dados:
        return jsonify({"erro": "Envie username e password"}), 400
        
    user = User.query.filter_by(username=dados['username']).first()
    if user and check_password_hash(user.password_hash, dados['password']):
        # Cria o token usando o ID do usuário como identidade
        token = create_access_token(identity=str(user.id))
        return jsonify({"access_token": token}), 200
        
    return jsonify({"erro": "Credenciais inválidas"}), 401

# ROTA 2: Listar (GET) e Criar (POST) tarefas
@api_bp.route('/tasks', methods=['GET', 'POST'])
@jwt_required()
def handle_tasks():
    current_user_id = get_jwt_identity()
    
    if request.method == 'POST':
        dados = request.get_json()
        if not dados or 'title' not in dados:
            return jsonify({"erro": "O campo title é obrigatório"}), 400
            
        nova_tarefa = Task(
            title=dados['title'],
            description=dados.get('description', ''),
            user_id=current_user_id
        )
        db.session.add(nova_tarefa)
        db.session.commit()
        return jsonify({"mensagem": "Tarefa criada!", "id": nova_tarefa.id}), 201
        
    # Se for GET:
    tasks = Task.query.filter_by(user_id=current_user_id).all()
    lista = [{"id": t.id, "title": t.title, "description": t.description, "status": t.status} for t in tasks]
    return jsonify(lista), 200

# ROTA 3: Editar (PUT) e Excluir (DELETE) tarefa específica
@api_bp.route('/tasks/<int:task_id>', methods=['PUT', 'DELETE'])
@jwt_required()
def handle_task_id(task_id):
    current_user_id = get_jwt_identity()
    task = Task.query.filter_by(id=task_id, user_id=current_user_id).first()
    
    if not task:
        return jsonify({"erro": "Tarefa não encontrada"}), 404
        
    if request.method == 'PUT':
        dados = request.get_json()
        task.title = dados.get('title', task.title)
        task.description = dados.get('description', task.description)
        if 'status' in dados:
            task.status = dados['status']
            
        db.session.commit()
        return jsonify({"mensagem": "Tarefa atualizada!"}), 200
        
    elif request.method == 'DELETE':
        db.session.delete(task)
        db.session.commit()
        return jsonify({"mensagem": "Tarefa excluída!"}), 200

@api_bp.route('/friends/request', methods=['POST'])
@jwt_required()
def send_friend_request():
    current_user_id = int(get_jwt_identity())
    dados = request.get_json()
    
    if not dados or 'friend_username' not in dados:
        return jsonify({"erro": "O campo friend_username é obrigatório"}), 400
        
    friend = User.query.filter_by(username=dados['friend_username']).first()
    
    if not friend:
        return jsonify({"erro": "Usuário não encontrado"}), 404
    if friend.id == current_user_id:
        return jsonify({"erro": "Você não pode adicionar a si mesmo"}), 400
        
    # Verifica se já existe um convite ou amizade entre os dois
    amizade_existente = Friendship.query.filter(
        ((Friendship.user_id == current_user_id) & (Friendship.friend_id == friend.id)) |
        ((Friendship.user_id == friend.id) & (Friendship.friend_id == current_user_id))
    ).first()
    
    if amizade_existente:
        return jsonify({"erro": "Convite já enviado ou vocês já são amigos"}), 400
        
    # Cria o convite pendente
    novo_convite = Friendship(user_id=current_user_id, friend_id=friend.id, status='pending')
    db.session.add(novo_convite)
    db.session.commit()
    
    return jsonify({"mensagem": "Convite enviado com sucesso!"}), 201

@api_bp.route('/friends/accept/<int:friendship_id>', methods=['PUT'])
@jwt_required()
def accept_friend_request(friendship_id):
    current_user_id = int(get_jwt_identity())
    
    # Busca o convite onde o usuário logado é o RECEPTOR (friend_id)
    convite = Friendship.query.filter_by(
        id=friendship_id, 
        friend_id=current_user_id, 
        status='pending'
    ).first()
    
    if not convite:
        return jsonify({"erro": "Convite não encontrado ou já processado"}), 404
        
    convite.status = 'accepted'
    db.session.commit()
    
    return jsonify({"mensagem": "Convite aceito! Vocês agora são amigos."}), 200

@api_bp.route('/friends', methods=['GET'])
@jwt_required()
def list_friends():
    current_user_id = int(get_jwt_identity())
    
    # Busca amizades aceitas onde o usuário é o remetente OU o destinatário
    amizades = Friendship.query.filter(
        ((Friendship.user_id == current_user_id) | (Friendship.friend_id == current_user_id)),
        Friendship.status == 'accepted'
    ).all()
    
    lista_amigos = []
    for amizade in amizades:
        # Se eu sou o user_id, meu amigo é o friend_id (e vice-versa)
        amigo_id = amizade.friend_id if amizade.user_id == current_user_id else amizade.user_id
        amigo = User.query.get(amigo_id)
        
        lista_amigos.append({
            "friendship_id": amizade.id,
            "user_id": amigo.id, 
            "username": amigo.username
        })
        
    return jsonify(lista_amigos), 200

@api_bp.route('/friends/pending', methods=['GET'])
@jwt_required()
def list_pending_requests():
    current_user_id = int(get_jwt_identity())
    
    # Busca convites onde o usuário logado é o DESTINATÁRIO e o status é pendente
    convites = Friendship.query.filter_by(
        friend_id=current_user_id, 
        status='pending'
    ).all()
    
    lista_pendentes = []
    for convite in convites:
        # Precisamos mostrar QUEM enviou o convite (o remetente)
        remetente = User.query.get(convite.user_id)
        
        lista_pendentes.append({
            "friendship_id": convite.id,
            "sender_id": remetente.id,
            "sender_username": remetente.username
        })
        
    return jsonify(lista_pendentes), 200

@api_bp.route('/groups', methods=['POST'])
@jwt_required()
def create_group():
    current_user_id = int(get_jwt_identity())
    dados = request.get_json()
    
    if not dados or 'name' not in dados:
        return jsonify({"erro": "O campo name é obrigatório"}), 400
        
    # 1. Cria o grupo
    novo_grupo = Group(name=dados['name'], description=dados.get('description', ''))
    db.session.add(novo_grupo)
    db.session.commit() # Salva para gerar o ID do grupo
    
    # 2. Adiciona o criador como 'admin' na tabela invisível user_group
    stmt = user_group.insert().values(
        user_id=current_user_id, 
        group_id=novo_grupo.id, 
        role='admin'
    )
    db.session.execute(stmt)
    db.session.commit()
    
    return jsonify({"mensagem": "Grupo criado com sucesso!", "group_id": novo_grupo.id}), 201

@api_bp.route('/groups/<int:group_id>/add_member', methods=['POST'])
@jwt_required()
def add_group_member(group_id):
    current_user_id = int(get_jwt_identity())
    dados = request.get_json()
    
    if not dados or 'friend_id' not in dados:
        return jsonify({"erro": "O campo friend_id é obrigatório"}), 400
        
    friend_id = dados['friend_id']
    
    # 1. Verifica se o usuário atual é admin do grupo (segurança máxima)
    admin_check = db.session.query(user_group).filter(
        user_group.c.user_id == current_user_id, 
        user_group.c.group_id == group_id, 
        user_group.c.role == 'admin'
    ).first()
    
    if not admin_check:
        return jsonify({"erro": "Apenas administradores podem adicionar membros"}), 403
        
    # 2. Verifica se o friend_id realmente é amigo
    amizade = Friendship.query.filter(
        ((Friendship.user_id == current_user_id) & (Friendship.friend_id == friend_id)) |
        ((Friendship.user_id == friend_id) & (Friendship.friend_id == current_user_id)),
        Friendship.status == 'accepted'
    ).first()
    
    if not amizade:
        return jsonify({"erro": "Você só pode adicionar amigos aprovados aos seus grupos"}), 403
        
    # 3. Verifica se o amigo já está no grupo
    membro_existente = db.session.query(user_group).filter(
        user_group.c.user_id == friend_id, 
        user_group.c.group_id == group_id
    ).first()
    
    if membro_existente:
        return jsonify({"erro": "O usuário já é membro deste grupo"}), 400
        
    # 4. Adiciona o amigo como membro comum
    stmt = user_group.insert().values(user_id=friend_id, group_id=group_id, role='member')
    db.session.execute(stmt)
    db.session.commit()
    
    return jsonify({"mensagem": "Amigo adicionado ao grupo com sucesso!"}), 200

@api_bp.route('/groups', methods=['GET'])
@jwt_required()
def list_groups():
    current_user_id = int(get_jwt_identity())
    user = User.query.get(current_user_id)
    
    lista_grupos = []
    for grupo in user.groups:
        # Puxamos a role ('admin' ou 'member') diretamente da tabela intermediária
        papel = db.session.query(user_group.c.role).filter(
            user_group.c.user_id == current_user_id, 
            user_group.c.group_id == grupo.id
        ).first()
        
        lista_grupos.append({
            "id": grupo.id,
            "name": grupo.name,
            "description": grupo.description,
            "my_role": papel[0] if papel else 'member'
        })
        
    return jsonify(lista_grupos), 200

@api_bp.route('/groups/<int:group_id>/tasks', methods=['POST'])
@jwt_required()
def create_group_task(group_id):
    current_user_id = int(get_jwt_identity())
    
    # 1. Verifica se o usuário pertence a este grupo
    membro = db.session.query(user_group).filter(
        user_group.c.user_id == current_user_id, 
        user_group.c.group_id == group_id
    ).first()
    
    if not membro:
        return jsonify({"erro": "Acesso negado. Você não é membro deste grupo."}), 403
        
    dados = request.get_json()
    if not dados or 'title' not in dados:
        return jsonify({"erro": "O campo title é obrigatório"}), 400
        
    # 2. Cria a tarefa marcando o group_id (Tarefa Compartilhada)
    nova_tarefa = Task(
        title=dados['title'],
        description=dados.get('description', ''),
        user_id=current_user_id, # Registra quem criou a tarefa
        group_id=group_id        # Registra a qual grupo ela pertence
    )
    
    db.session.add(nova_tarefa)
    db.session.commit()
    
    return jsonify({"mensagem": "Tarefa de grupo criada!", "id": nova_tarefa.id}), 201

@api_bp.route('/groups/<int:group_id>/tasks', methods=['GET'])
@jwt_required()
def list_group_tasks(group_id):
    current_user_id = int(get_jwt_identity())
    
    # 1. Verifica segurança (apenas membros podem ver o quadro)
    membro = db.session.query(user_group).filter(
        user_group.c.user_id == current_user_id, 
        user_group.c.group_id == group_id
    ).first()
    
    if not membro:
        return jsonify({"erro": "Acesso negado. Você não pertence a este grupo."}), 403
        
    # 2. Busca todas as tarefas daquele grupo
    tarefas = Task.query.filter_by(group_id=group_id).all()
    
    lista_tarefas = []
    for t in tarefas:
        # Pega o nome de quem criou a tarefa para exibir no card
        criador = User.query.get(t.user_id) if t.user_id else None
        
        lista_tarefas.append({
            "id": t.id,
            "title": t.title,
            "description": t.description,
            "status": t.status,
            "created_by": criador.username if criador else "Sistema"
        })
        
    return jsonify(lista_tarefas), 200

@api_bp.route('/tasks', methods=['GET'])
@jwt_required()
def get_tasks():
    current_user_id = int(get_jwt_identity())
    
    # A MÁGICA ACONTECE AQUI: Adicionamos o group_id=None
    # Isso garante que ele só pegue tarefas que NÃO estão em nenhum grupo
    tarefas = Task.query.filter_by(
        user_id=current_user_id, 
        group_id=None
    ).all()
    
    lista_tarefas = []
    for t in tarefas:
        lista_tarefas.append({
            "id": t.id,
            "title": t.title,
            "description": t.description,
            "status": t.status
        })
        
    return jsonify(lista_tarefas), 200

@api_bp.route('/groups/<int:group_id>/leave', methods=['DELETE'])
@jwt_required()
def leave_group(group_id):
    current_user_id = int(get_jwt_identity())
    
    # 1. Verifica se o usuário realmente está no grupo
    membro = db.session.query(user_group).filter(
        user_group.c.user_id == current_user_id, 
        user_group.c.group_id == group_id
    ).first()
    
    if not membro:
        return jsonify({"erro": "Você não faz parte deste grupo"}), 400
        
    # 2. Remove a conexão entre o usuário e o grupo
    stmt = user_group.delete().where(
        user_group.c.user_id == current_user_id,
        user_group.c.group_id == group_id
    )
    db.session.execute(stmt)
    db.session.commit()
    
    # 3. Limpeza automática: Se o grupo ficou vazio, apaga ele do banco
    membros_restantes = db.session.query(user_group).filter_by(group_id=group_id).count()
    if membros_restantes == 0:
        grupo_vazio = Group.query.get(group_id)
        if grupo_vazio:
            db.session.delete(grupo_vazio)
            db.session.commit()
            
    return jsonify({"mensagem": "Você saiu do grupo com sucesso!"}), 200

@api_bp.route('/groups/<int:group_id>', methods=['DELETE'])
@jwt_required()
def delete_group(group_id):
    current_user_id = int(get_jwt_identity())
    
    # 1. Validação estrita: O usuário logado é admin deste grupo?
    admin = db.session.query(user_group).filter(
        user_group.c.user_id == current_user_id, 
        user_group.c.group_id == group_id, 
        user_group.c.role == 'admin'
    ).first()
    
    if not admin:
        return jsonify({"erro": "Acesso negado. Apenas o administrador pode deletar o grupo."}), 403
        
    grupo = Group.query.get(group_id)
    if not grupo:
        return jsonify({"erro": "Grupo não encontrado"}), 404
        
    # 2. Apaga o grupo (as tarefas vinculadas a ele somem junto por efeito cascata)
    db.session.delete(grupo)
    db.session.commit()
    
    return jsonify({"mensagem": "Grupo e todas as suas tarefas foram deletados."}), 200

@api_bp.route('/tasks/<int:task_id>/status', methods=['PUT'])
@jwt_required()
def toggle_task_status(task_id):
    current_user_id = int(get_jwt_identity())
    
    # 1. Busca a tarefa no banco
    tarefa = Task.query.get(task_id)
    if not tarefa:
        return jsonify({"erro": "Tarefa não encontrada"}), 404
        
    # 2. Roteamento de Segurança (Privada vs Compartilhada)
    if tarefa.group_id:
        # É uma tarefa de grupo: o usuário precisa estar na tabela user_group
        membro = db.session.query(user_group).filter(
            user_group.c.user_id == current_user_id,
            user_group.c.group_id == tarefa.group_id
        ).first()
        
        if not membro:
            return jsonify({"erro": "Acesso negado. Você não é membro deste grupo."}), 403
    else:
        # É uma tarefa privada: o usuário logado precisa ser o dono exato
        if tarefa.user_id != current_user_id:
            return jsonify({"erro": "Acesso negado. Esta tarefa pertence a outra pessoa."}), 403

    # 3. O Efeito Interruptor (Toggle)
    # Se era False (pendente), vira True (concluída) e vice-versa.
    tarefa.status = not tarefa.status
    db.session.commit()
    
    estado = "concluída" if tarefa.status else "pendente"
    return jsonify({"mensagem": f"Tarefa marcada como {estado}!", "novo_status": tarefa.status}), 200

