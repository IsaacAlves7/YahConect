"""Cria as tabelas no banco configurado em DATABASE_URL (.env)."""
from app.database import init_db

if __name__ == "__main__":
    init_db()
    print("Banco de dados inicializado com sucesso ✅")
