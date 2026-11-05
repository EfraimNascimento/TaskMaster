def test_api_login(client):
    """Testa o login pela API e a geração do Token JWT"""
    # Criamos o usuário usando a rota HTML normal
    client.post('/register', data={'username': 'hacker', 'password': '123'})
    
    # 1. Falha: Faltam dados (400)
    resp_erro1 = client.post('/api/v1/login', json={})
    assert resp_erro1.status_code == 400
    
    # 2. Falha: Senha incorreta (401)
    resp_erro2 = client.post('/api/v1/login', json={'username': 'hacker', 'password': 'err'})
    assert resp_erro2.status_code == 401
    
    # 3. Sucesso: Retorna o token (200)
    resp_sucesso = client.post('/api/v1/login', json={'username': 'hacker', 'password': '123'})
    assert resp_sucesso.status_code == 200
    assert 'access_token' in resp_sucesso.get_json()

def test_api_crud_tarefas(client):
    """Testa criar, listar, atualizar e excluir via API"""
    client.post('/register', data={'username': 'ninja', 'password': '123'})
    resp_login = client.post('/api/v1/login', json={'username': 'ninja', 'password': '123'})
    
    # Extraímos o token e montamos o cabeçalho
    token = resp_login.get_json()['access_token']
    headers = {'Authorization': f'Bearer {token}'}
    
    # 1. POST Erro (Sem título)
    resp_post_err = client.post('/api/v1/tasks', json={}, headers=headers)
    assert resp_post_err.status_code == 400
    
    # 2. POST Sucesso (Criar Tarefa)
    resp_post = client.post('/api/v1/tasks', json={'title': 'Tarefa API'}, headers=headers)
    assert resp_post.status_code == 201
    task_id = resp_post.get_json()['id']
    
    # 3. GET (Listar)
    resp_get = client.get('/api/v1/tasks', headers=headers)
    assert resp_get.status_code == 200
    assert len(resp_get.get_json()) == 1
    
    # 4. PUT (Atualizar)
    resp_put = client.put(f'/api/v1/tasks/{task_id}', json={'status': True}, headers=headers)
    assert resp_put.status_code == 200
    
    # 5. PUT Erro (Tarefa não encontrada 404)
    resp_404 = client.put('/api/v1/tasks/999', json={}, headers=headers)
    assert resp_404.status_code == 404
    
    # 6. DELETE (Excluir)
    resp_delete = client.delete(f'/api/v1/tasks/{task_id}', headers=headers)
    assert resp_delete.status_code == 200