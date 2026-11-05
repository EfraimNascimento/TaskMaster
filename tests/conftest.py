import pytest
from app import create_app
from app.models import db, User

@pytest.fixture
def app():
    # Cria o app apontando para um banco de dados tamporário na memória
    app = create_app()
    app.config.update({
        "TESTING": True,
        "SQULALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "WTF_CSRF_ENABLED": False # Desativa o CSRF nos testes
    })

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    # Navegador, para simular cliques e acessos
    return app.test_client()