from app.models import Task, User, db

def test_criar_tarefa(client, app):
    """Testa o fluxo de usuário logado criando uma tarefa"""

    # Registrando e logando o uuário
    client.post('/register', data={'username': 'Mario', 'password': '123'})
    client.post('/login', data={'username': 'Mario', 'password': '123'})

    # Enviando formulário de nova tarefa
    resposta = client.post('/', data={
        'title': 'Derrotar o Bowser',
        'description': 'Resgatar a princesa Peach'
    }, follow_redirects=True)

    assert resposta.status_code == 200
    # O titulo da tarefa deve aparecer no HTML recarregado
    assert b'Derrotar o Bowser' in resposta.data

    # Checar o Banco de Dados
    with app.app_context():
        tarefa = Task.query.filter_by(title='Derrotar o Bowser').first()
        assert tarefa is not None
        assert tarefa.description == 'Resgatar a princesa Peach'

        # Garantir que pertence ao usuário 
        dono = db.session.get(User, tarefa.user_id)
        assert dono.username == 'Mario'
        assert tarefa.status == False

def text_excluir_tarefa(client, app):
    """"Testa o fluxo de criação e exclusão de uma tarefa"""
    client.post('/register', data={'username': 'link', 'password': '123'})
    client.post('/register', data={'username': 'link', 'password': '123'})

    # Cria a tarefa
    client.post('/', data={'title': 'Quebrar vasos', 'description': ''})

    # Descobre o ID que a tarefa ganhou no banco de dados
    with app.app_context():
        tarefa_criada = Task.query.filter_by(title='Quebrar vasos').first()
        task_id = tarefa_criada.id

    # Simula o clique no botão Excluir do HTML
    resposta = client.get(f'/delete/{task_id}', follow_redirects=True)
    assert resposta.status_code == 200

    # Verificar se a tarefa sumiu
    with app.app_context():
        tarefa_deletada = Task.query.get(task_id)
        assert tarefa_deletada is None # Deve ser None (vazio)

def test_toggle_e_erros_tarefas(client, app):
    """Testa o botão concluir e os tratamentos de erro do app/tasks.py"""
    # Preparação
    client.post('/register', data={'username': 'zelda', 'password': '123'})
    client.post('/login', data={'username': 'zelda', 'password': '123'})
    
    # 1. Tenta criar tarefa com título vazio (cobre a falha do 'if task_title:')
    resposta_vazia = client.post('/', data={'title': '', 'description': ''}, follow_redirects=True)
    assert resposta_vazia.status_code == 200
    
    # 2. Cria a tarefa real
    client.post('/', data={'title': 'Salvar Hyrule', 'description': ''})
    
    # Descobre o ID
    with app.app_context():
        from app.models import Task, db
        tarefa = Task.query.filter_by(title='Salvar Hyrule').first()
        task_id = tarefa.id
        
    # 3. Ação: Clica no botão de concluir (Toggle)
    client.get(f'/toggle/{task_id}', follow_redirects=True)
    
    # Verifica se o status mudou para True
    with app.app_context():
        tarefa_atualizada = db.session.get(Task, task_id)
        assert tarefa_atualizada.status == True
        
    # 4. Força o erro: Tenta concluir e excluir uma tarefa que NÃO EXISTE (ID 999)
    # (Isso cobre os 'if task:' para quando a busca no banco não acha nada)
    client.get('/toggle/999')
    client.get('/delete/999')

def test_excluir_tarefa_sucesso(client, app):
    """Testa o caminho feliz de excluir uma tarefa real"""
    # 1. Cria um usuário e faz login
    client.post('/register', data={'username': 'exterminador', 'password': '123'})
    client.post('/login', data={'username': 'exterminador', 'password': '123'})
    
    # 2. Cria uma tarefa
    client.post('/', data={'title': 'Alvo a ser eliminado', 'description': ''})
    
    # 3. Descobre o ID dessa tarefa no banco
    with app.app_context():
        from app.models import Task, db
        tarefa = Task.query.filter_by(title='Alvo a ser eliminado').first()
        task_id = tarefa.id
        
    # 4. Executa a linha vermelha: deleta de verdade!
    client.get(f'/delete/{task_id}')
    
    # 5. Garante que ela sumiu do banco
    with app.app_context():
        tarefa_apagada = db.session.get(Task, task_id)
        assert tarefa_apagada is None