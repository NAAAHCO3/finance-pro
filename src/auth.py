import bcrypt
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError # Importação necessária para tratar o erro
from src.models import User

# --- LÓGICA DE HASHING ---

def get_password_hash(password: str) -> str:
    """Gera o hash da senha usando bcrypt."""
    pwd_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(pwd_bytes, salt)
    return hashed.decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica se a senha bate com o hash salvo."""
    try:
        pwd_bytes = plain_password.encode('utf-8')
        hashed_bytes = hashed_password.encode('utf-8')
        return bcrypt.checkpw(pwd_bytes, hashed_bytes)
    except Exception:
        return False

# --- FUNÇÕES DE BANCO DE DADOS ---

def get_user_by_username(db: Session, username: str):
    # Filtra ignorando maiúsculas/minúsculas para evitar duplicidade visual
    return db.query(User).filter(User.username == username).first()

def create_user(db: Session, username: str, email: str, password: str):
    """
    Tenta criar um usuário. 
    Usa Try/Except para capturar erro de duplicidade (IntegrityError) do banco.
    """
    try:
        # 1. Tenta preparar o usuário
        hashed_password = get_password_hash(password)
        db_user = User(
            username=username, 
            email=email, 
            password_hash=hashed_password
        )
        db.add(db_user)
        
        # 2. Tenta salvar (Aqui que o erro acontecia)
        db.commit()
        db.refresh(db_user)
        return True

    except IntegrityError:
        # SE O BANCO DISSER QUE JÁ EXISTE:
        db.rollback() # Cancela a tentativa travada
        return False  # Retorna "False" para o Home.py mostrar o erro "Usuário já existe"
        
    except Exception as e:
        # Outros erros genéricos
        db.rollback()
        print(f"Erro ao criar usuário: {e}")
        return False