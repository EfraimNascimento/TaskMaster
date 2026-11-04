from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from werkzeug.security import check_password_hash
from .models import db, User, Task

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