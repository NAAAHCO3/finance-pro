import logging
from typing import List
from sqlalchemy.orm import Session
from src.models.category import Category

logger = logging.getLogger(__name__)

class CategoryService:
    """
    Serviço responsável por gerenciar categorias de renda e gasto.
    """

    TIPOS_VALIDOS = {"renda", "gasto"}

    def __init__(self, db: Session):
        self.db = db

    # ======================================================
    # MÉTODOS NOVOS (NECESSÁRIOS PARA O EDITOR)
    # ======================================================
    def listar_todos(self, user_id: int) -> List[Category]:
        """
        Lista TODAS as categorias do usuário (sem filtro de tipo).
        Usado para o editor de categorias listar tudo o que existe.
        """
        try:
            return self.db.query(Category).filter(Category.user_id == user_id).all()
        except Exception:
            logger.exception("Erro ao listar todas as categorias | user_id=%s", user_id)
            return []

    def listar_padrao(self) -> List[str]:
        """
        Retorna uma lista de strings com categorias padrão.
        Útil para autocompletar dropdowns quando o usuário é novo.
        """
        return [
            "Moradia", "Alimentação", "Transporte", "Lazer", 
            "Saúde", "Educação", "Salário", "Investimentos"
        ]

    def deletar(self, user_id: int, nome: str) -> bool:
        """
        Remove uma categoria pelo nome.
        """
        try:
            cat = self.db.query(Category).filter(
                Category.user_id == user_id, 
                Category.name == nome
            ).first()
            
            if cat:
                self.db.delete(cat)
                self.db.commit()
                logger.info("Categoria removida: %s", nome)
                return True
            return False
        except Exception:
            self.db.rollback()
            logger.exception("Erro ao deletar categoria: %s", nome)
            return False

    # ======================================================
    # MÉTODOS EXISTENTES (MANTIDOS E MELHORADOS)
    # ======================================================
    def listar_por_tipo(self, user_id: int, tipo: str) -> List[Category]:
        """
        Lista categorias do usuário filtrando por tipo (renda ou gasto).
        Retorna OBJETOS Category completos.
        """
        tipo = str(tipo).lower().strip()

        if tipo not in self.TIPOS_VALIDOS:
            logger.warning("Tipo de categoria inválido: %s", tipo)
            return []

        try:
            categorias = (
                self.db.query(Category)
                .filter(
                    Category.user_id == user_id,
                    Category.type == tipo,
                )
                .order_by(Category.name.asc())
                .all()
            )
            return categorias
        except Exception:
            logger.exception("Erro ao listar categorias | user_id=%s tipo=%s", user_id, tipo)
            return []

    def adicionar(self, user_id: int, categoria: str, tipo: str = "gasto") -> bool:
        """
        Adiciona uma nova categoria.
        Retorna: True (Sucesso) ou False (Erro/Duplicada)
        """
        tipo = str(tipo).lower().strip()
        categoria_nome = str(categoria).strip()

        if tipo not in self.TIPOS_VALIDOS:
            logger.warning("Tentativa de criar tipo inválido: %s", tipo)
            return False

        if not categoria_nome:
            return False

        try:
            # Verifica se já existe
            existente = (
                self.db.query(Category)
                .filter(
                    Category.user_id == user_id,
                    Category.name == categoria_nome
                )
                .first()
            )

            if existente:
                logger.info("Categoria '%s' já existe. Ignorando.", categoria_nome)
                return False # Retorna False para o front avisar o usuário, sem crashar

            nova_categoria = Category(
                user_id=user_id,
                name=categoria_nome,
                type=tipo
            )

            self.db.add(nova_categoria)
            self.db.commit()
            self.db.refresh(nova_categoria)

            logger.info("Categoria adicionada: %s", categoria_nome)
            return True

        except Exception:
            self.db.rollback()
            logger.exception("Erro ao adicionar categoria no banco")
            return False