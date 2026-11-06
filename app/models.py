from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

db = SQLAlchemy()

# 1. Tabela Intermediária: Relação Muitos-para-Muitos entre Usuários e Grupos
user_group = db.Table('user_group',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('group_id', db.Integer, db.ForeignKey('group.id'), primary_key=True),
    # A coluna 'role' define se o usuário é 'admin' (criador) ou 'member' (convidado)
    db.Column('role', db.String(20), default='member')
)

# 2. Modelo de Amizade (Self-Referential)
class Friendship(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    # Quem enviou o convite
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    # Quem recebeu o convite
    friend_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    # Status pode ser: 'pending', 'accepted', 'blocked'
    status = db.Column(db.String(20), default='pending')

# 3. Modelo de Grupo
class Group(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(255), nullable=True)
    
    # Relacionamento para acessar os membros do grupo facilmente (e vice-versa)
    members = db.relationship('User', secondary=user_group, backref=db.backref('groups', lazy='dynamic'))
    
    # Relacionamento com as tarefas que pertencem a este grupo
    tasks = db.relationship('Task', backref='group', lazy=True, cascade="all, delete-orphan")

# 4. Modelo de Usuário Expandido
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    dark_mode = db.Column(db.Boolean, default=False)
    
    # Tarefas individuais do usuário
    tasks = db.relationship('Task', backref='owner', lazy=True, foreign_keys='Task.user_id')

    # Relacionamentos para rastrear amizades enviadas e recebidas
    sent_requests = db.relationship('Friendship', foreign_keys=[Friendship.user_id], backref='sender', lazy=True)
    received_requests = db.relationship('Friendship', foreign_keys=[Friendship.friend_id], backref='receiver', lazy=True)

# 5. Modelo de Tarefa Adaptado
class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=True)
    status = db.Column(db.Boolean, default=False)
    
    # Chaves Estrangeiras: Uma tarefa agora pode pertencer a uma pessoa OU a um grupo
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    group_id = db.Column(db.Integer, db.ForeignKey('group.id'), nullable=True)