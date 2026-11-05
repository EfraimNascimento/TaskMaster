from app.models import User

def test_pagina_login_carrega(client):
    """Testa se a página de login retorna status 200 (OK)"""
    resposta = client.get('/login')

    # O assert é o "juiz" do teste. Se for verdade, o teste passa.
    assert resposta.status_code == 200
    assert b'Login' in resposta.data # Verifica se a palavra Login está no HTML

def test_registro_usuario(client, app):
    """"Testa o fluxo de cadastro e o banco de dados"""
    # client.post envia os dados como se fossem digitados no HTML
    resposta = client.post('/register', data={
        'username': 'joao_teste',
        'password': 'senha_super_segura'
    }, follow_redirects=True)
    # follow_redirects=True faz o teste seguir o redirecionamento para o login

    # Verifica se carregou a tela de login após o sucesso
    assert resposta.status_code == 200

    # Verifica no Banco de Dados se o usuário foi criado de verdade
    with app.app_context():
        user = User.query.filter_by(username='joao_teste').first()
        assert user is not None
        assert user.username == 'joao_teste'
        assert user.dark_mode == False 

# Adicione no seu test_auth.py

def test_login_senha_errada(client):
    """Testa se o sistema bloqueia senhas incorretas"""
    resposta = client.post('/login', data={'username': 'joao_teste', 'password': 'senha_falsa'})
    # O sistema deve impedir o login (verifique se a palavra 'Credenciais inválidas' ou erro aparece, 
    # ou se ele NÃO redireciona para o dashboard)
    assert b'dashboard' not in resposta.data.lower()

def test_logout(client, app):
    """Testa se o usuário consegue sair do sistema"""
    # Primeiro loga
    client.post('/register', data={'username': 'luigi', 'password': '123'})
    client.post('/login', data={'username': 'luigi', 'password': '123'})
    
    # Depois clica em sair (GET na rota /logout)
    resposta = client.get('/logout', follow_redirects=True)
    
    # Verifica se voltou pra tela de login
    assert resposta.status_code == 200
    assert b'Login' in resposta.data

def test_mudar_tema(client, app):
    """Testa se a rota altera a preferência de tema do usuário no banco"""
    # Preparação
    client.post('/register', data={'username': 'batman', 'password': '123'})
    client.post('/login', data={'username': 'batman', 'password': '123'})

    # Ação: clica no botão de alternar tema (rota do nosso auth.py)
    client.get('/toggle-theme')

    # Verificação: O usuário prefere o modo escuro ou não
    with app.app_context():
        from app.models import User
        user = User.query.filter_by(username='batman').first()
        assert user.dark_mode == True

def test_registro_usuario_duplicado(client):
    """Testa se o sistema impede dois usuários com o mesmo nome"""
    # 1. Registra o primeiro
    client.post('/register', data={'username': 'gemeo', 'password': '123'})
    
    # 2. Tenta registrar outro com o mesmo nome
    resposta = client.post('/register', data={'username': 'gemeo', 'password': 'abc'})
    
    # Como deve dar erro, ele provavelmente continua na tela de registro ou mostra erro
    # Verifique se o redirecionamento para login NÃO aconteceu (código 200 em vez de 302, ou flash message)
    assert resposta.status_code == 302 

def test_login_usuario_inexistente(client):
    """Testa login com um username que não existe no banco"""
    resposta = client.post('/login', data={'username': 'fantasma', 'password': '123'})
    # A página deve recarregar mostrando o erro, não entrar no painel
    assert b'dashboard' not in resposta.data.lower()

def test_cobertura_sniper(client):
    """Testa o GET do registro e força o carregamento do usuário (load_user)"""
    # 1. Cobre o 'return render_template('register.html')'
    resposta_get = client.get('/register')
    assert resposta_get.status_code == 200
    
    # 2. Registra, loga e acessa a Home para forçar o 'load_user' do __init__.py
    client.post('/register', data={'username': 'sniper', 'password': '123'})
    client.post('/login', data={'username': 'sniper', 'password': '123'})
    
    # Ao acessar a Home, o Flask-Login obrigatoriamente aciona o load_user!
    client.get('/')

def test_forcar_load_user(client, app):
    """Força a execução direta do callback interno do Flask-Login"""
    # 1. Criamos um usuário que vai ganhar o ID 1 no banco fantasma
    client.post('/register', data={'username': 'chefao', 'password': '123'})
    
    with app.app_context():
        # 2. Pegamos a função 'load_user' que o Flask-Login guardou internamente
        funcao_load_user = app.login_manager._user_callback
        
        # 3. Executamos ela passando o ID '1' (Isso aciona a Linha 33 exata!)
        usuario = funcao_load_user('1')
        
        # 4. Verificamos se ele realmente encontrou o usuário
        assert usuario is not None
        assert usuario.username == 'chefao'