from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from werkzeug.security import check_password_hash
from .models import db, User, Task

api_bp = Blueprint('api', __name__)

# EndPoint de login para API (Gera o Token)
@api_bp.route('/login', methods=['POST'])
def api_login():
    # APIs recebem dados em JSN, não em formulários
    data = request.get_json()

    if not data or not data.get('username') or not data.get('password'):
        return jsonify({'message': 'Dados de login ausentes'}), 400

    user = User.query.filter_by(username=data.get('username')).first()

    if user and check_password_hash(user.password_hash, data.get('password')):
        # Se a senha estiver correta, criamos o token
        # Usamos o ID do usuário como "Identidade" do token
        access_token = create_access_token(identity=str(user.id))
        return jsonify(access_token=access_token), 200

    return jsonify({'message': 'Credenciais inválidas'}), 401

# EndPoint para listar as tarefas do usuário logado (Requer Token)
@api_bp.route('/tasks', methods=['GET'])
@jwt_required()
def get_tasks():
    # get_jwt_identity() retorna a 'identity' (o ID do usuário) que guardamos no token
    current_user_id = get_jwt_identity()
    tasks = Task.query.filter_by(user_id=current_user_id).all()

    # Convertemos os objetos Task em uma lista de dicionários (serialização)
    task_list = []
    for task in task:
        task_list.append({
            'id': task.id,
            'title': task.title,
            'description': task.description,
            'status': task.status
        })
    return jsonify({'tasks': task_list}), 200

# Método POST
@api_bp.route('/tasks', methods=['POST'])
@jwt_required()
def create_task():
    current_user_id = get_jwt_identity()
    data = request.get_json()

    if not data or not data.get('title'):
        return jsonify({'message': 'O título da tarefa é obrigatório'}), 400

    new_task = Task(
        title=data.get('title'),
        description=data.get('description'),
        user_id=current_user_id
    )

    db.session.add(new_task)
    db.session.commit()

    return jsonify({'message': 'Tarefa criada com sucesso', 'task_id': new_task.id}), 201


# Método GET
@api_bp.route('/tasks/<int:task_id>', methods=['GET'])
@jwt_required()
def get_task(task_id):
    current_user_id = get_jwt_identity()
    task = Task.query.filter_by(id=task_id, user_id=current_user_id).first()

    if not task:
        return jsonify({'message': 'Tarefa não encontrada'}), 404

    return jsonify({
        'id': task_id,
        'title': task.title,
        'description': task.description,
        'status': task.status
    }), 200


#Método PUT
@api_bp.route('/tasks/<int:task_id>', methods=['PUT'])
@jwt_required()
def update_task(task_id):
    current_user_id = get_jwt_identity()
    task = Task.query.filter_by(id=task_id, user_id=current_user_id).first()

    if not task:
        return jsonify({'message': 'Tarefa não encontrada'}), 404

    data = request.get_json()
    if not task:
        return jsonify({'message': 'Nenhum dado fornecido'}), 400

    if 'title' in data:
        task.title = data['title']
    if 'description' in data:
        task.description = data['description']
    if 'status' in data:
        task.status = data['status']

    db.session.commit()
    return jsonify({'message': 'Tarefa atualizada com sucesso'}), 200

#Método DELETE
@api_bp.route('/tasks/<int:task_id>', methods=['DELETE'])
@jwt_required()
def delete_task(task_id):
    current_user_id = get_jwt_identity()
    task = Task.query.filter_by(id=task_id, user_id=current_user_id).first()

    if not task:
        return jsonify({'message': 'Tarefa não encontrada'}), 404

    db.session.delete(task)
    db.session.commit()
    return jsonify({'message': 'Tarefa deletada com sucesso'}), 200