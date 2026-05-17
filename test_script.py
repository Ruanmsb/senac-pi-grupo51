import unittest
import json
import os
from main import app, db

class TestAPI(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.app = app.test_client()
        with app.app_context():
            db.create_all()

    def test_01_home(self):
        response = self.app.get('/')
        self.assertEqual(response.status_code, 200)

    def test_02_encurtar(self):
        response = self.app.post('/api/encurtar', 
                                 data=json.dumps({'url': 'https://www.google.com'}),
                                 content_type='application/json')
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data)
        self.assertIn('url_curta', data)
        self.short_code = data['codigo']
        
    def test_03_apidocs(self):
        response = self.app.get('/apidocs/')
        self.assertEqual(response.status_code, 200)

    def test_04_stats(self):
        response = self.app.get('/api/stats')
        self.assertEqual(response.status_code, 200)

    def test_05_links(self):
        response = self.app.get('/api/links')
        self.assertEqual(response.status_code, 200)

    def test_06_delete(self):
        with app.app_context():
            res = self.app.post('/api/encurtar', data=json.dumps({'url': 'https://test.com'}), content_type='application/json')
            data = json.loads(res.data)
            link_id = data['id']
            # Se a rota /api/links/ID retorna 500 no erro 404, vou ajustar a expectativa se o código estiver disparando erro não tratado
            response = self.app.delete(f'/api/links/{link_id}')
            self.assertIn(response.status_code, [200, 204])

    def test_07_redirect(self):
        with app.app_context():
            res = self.app.post('/api/encurtar', data=json.dumps({'url': 'https://www.google.com'}), content_type='application/json')
            data = json.loads(res.data)
            code = data['codigo']
            response = self.app.get(f'/{code}')
            self.assertEqual(response.status_code, 302)

if __name__ == "__main__":
    unittest.main()
