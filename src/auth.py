import bcrypt
from sqlalchemy.orm import Session
from src.models import User

# --- LÓGICA DE HASHING (ATUALIZADA PARA PYTHON 3.13) ---

def get_password_hash(password: str) -> str:
    """
    Gera o hash da senha usando bcrypt.
    Converte a string para bytes antes de hashear.
    """
    # Converte string para bytes (utf-8)
    pwd_bytes = password.encode('utf-8')
    # Gera o salt e o hash
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(pwd_bytes, salt)
    # Retorna como string para salvar no banco
    return hashed.decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifica se a senha bate com o hash salvo.
    """
    try:
        # Converte ambos para bytes
        pwd_bytes = plain_password.encode('utf-8')
        hashed_bytes = hashed_password.encode('utf-8')
        
        return bcrypt.checkpw(pwd_bytes, hashed_bytes)
    except Exception:
        # Se houver erro de formato (ex: banco antigo ou corrompido), nega o acesso
        return False

# --- FUNÇÕES DE BANCO DE DADOS ---

def get_user_by_username(db: Session, username: str):
    return db.query(User).filter(User.username == username).first()

def create_user(db: Session, username: str, email: str, password: str):
    # Verifica se já existe
    if get_user_by_username(db, username):
        return False
    
    # Cria novo
    hashed_password = get_password_hash(password)
    db_user = User(
        username=username, 
        email=email, 
        password_hash=hashed_password
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return True