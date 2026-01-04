# src/auth.py
from sqlalchemy.orm import Session
from src.models import User  # Importamos o modelo que você criou
from passlib.context import CryptContext

# Configuração do Passlib
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password):
    return pwd_context.hash(password)

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_user_by_username(db: Session, username: str):
    """
    Busca um usuário pelo username usando o ORM do SQLAlchemy.
    Retorna um objeto User ou None.
    """
    # Em vez de "SELECT * ...", usamos query filter
    return db.query(User).filter(User.username == username).first()

def create_user(db: Session, username: str, email: str, password: str):
    """Cria novo usuário usando o modelo ORM."""
    
    # Verifica se usuário já existe
    if get_user_by_username(db, username):
        return False # Usuário já existe
    
    hashed_password = get_password_hash(password)
    
    # Cria o objeto User (Note que usamos password_hash para bater com o models.py)
    new_user = User(
        username=username,
        email=email,
        password_hash=hashed_password 
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user) # Recarrega o objeto com o ID gerado pelo banco
    return True