import logging
from typing import List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
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
    # MÉTODOS DE LISTAGEM
    # ======================================================
    def listar_todos(self, user_id: int) -> List[Category]:
        """
        Lista TODAS as categorias do usuário (sem filtro de tipo).
        """
        try:
            return self.db.query(Category).filter(Category.user_id == user_id).all()
        except Exception:
            logger.exception("Erro ao listar todas as categorias | user_id=%s", user_id)
            return []

    def listar_padrao(self) -> List[str]:
        """
        Retorna sugestões padrão.
        """
        return [
            "Moradia", "Alimentação", "Transporte", "Lazer", 
            "Saúde", "Educação", "Salário", "Investimentos"
        ]

    def listar_por_tipo(self, user_id: int, tipo: str) -> List[Category]:
        """
        Lista categorias filtrando por tipo (renda ou gasto).
        """
        tipo = str(tipo).lower().strip()

        if tipo not in self.TIPOS_VALIDOS:
            logger.warning("Tipo de categoria inválido: %s", tipo)
            return []

        try:
            return (
                self.db.query(Category)
                .filter(Category.user_id == user_id, Category.type == tipo)
                .order_by(Category.name.asc())
                .all()
            )
        except Exception:
            logger.exception("Erro ao listar categorias | user_id=%s tipo=%s", user_id, tipo)
            return []

    # ======================================================
    # MÉTODOS DE CRIAÇÃO E EDIÇÃO
    # ======================================================
    def adicionar(self, user_id: int, categoria: str, tipo: str = "gasto") -> bool:
        """
        Adiciona uma nova categoria.
        """
        tipo = str(tipo).lower().strip()
        categoria_nome = str(categoria).strip()

        if tipo not in self.TIPOS_VALIDOS:
            return False

        if not categoria_nome:
            return False

        try:
            # Evita duplicatas
            existente = (
                self.db.query(Category)
                .filter(
                    Category.user_id == user_id,
                    Category.name == categoria_nome,
                    Category.type == tipo
                )
                .first()
            )

            if existente:
                return False

            nova_categoria = Category(
                user_id=user_id,
                name=categoria_nome,
                type=tipo
            )

            self.db.add(nova_categoria)
            self.db.commit()
            return True

        except Exception:
            self.db.rollback()
            logger.exception("Erro ao adicionar categoria")
            return False

    def atualizar(self, user_id: int, category_id: int, novo_nome: str) -> bool:
        """
        Renomeia uma categoria existente.
        """
        nome_limpo = str(novo_nome).strip()
        if not nome_limpo:
            return False

        try:
            cat = self.db.query(Category).filter(
                Category.id == category_id,
                Category.user_id == user_id
            ).first()

            if cat:
                cat.name = nome_limpo
                self.db.commit()
                return True
            return False
        except Exception:
            self.db.rollback()
            return False

    # ======================================================
    # EXCLUSÃO (COM PROTEÇÃO)
    # ======================================================
    def deletar(self, user_id: int, category_id: int) -> Tuple[bool, str]:
        """
        Remove uma categoria pelo ID.
        Retorna (Sucesso, Mensagem).
        """
        try:
            cat = self.db.query(Category).filter(
                Category.id == category_id, 
                Category.user_id == user_id
            ).first()
            
            if not cat:
                return False, "Categoria não encontrada."

            self.db.delete(cat)
            self.db.commit()
            logger.info("Categoria ID %s removida", category_id)
            return True, "Categoria removida com sucesso."

        except IntegrityError:
            self.db.rollback()
            # Esta mensagem protege contra a exclusão de dados importantes
            return False, "Não é possível excluir: existem lançamentos usando esta categoria."
        
        except Exception as e:
            self.db.rollback()
            logger.exception("Erro ao deletar categoria")
            return False, f"Erro interno: {str(e)}"