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
    # LISTAGEM
    # ======================================================
    def listar_por_tipo(
        self,
        user_id: int,
        tipo: str
    ) -> List[Category]:
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

            # CORREÇÃO: Retorna a lista de objetos, não apenas os nomes.
            return categorias

        except Exception:
            logger.exception(
                "Erro ao listar categorias | user_id=%s tipo=%s",
                user_id, tipo
            )
            return []

    # ======================================================
    # CRIAÇÃO
    # ======================================================
    def adicionar(
        self,
        user_id: int,
        categoria: str,
        tipo: str = "gasto"
    ) -> bool:
        """
        Adiciona uma nova categoria.

        Retorna:
            True em caso de sucesso
        """
        tipo = str(tipo).lower().strip()
        categoria_nome = str(categoria).strip()

        if tipo not in self.TIPOS_VALIDOS:
            raise ValueError("Tipo de categoria inválido (use renda ou gasto)")

        if not categoria_nome:
            raise ValueError("Nome da categoria inválido")

        try:
            # Evita duplicatas
            # Nota: Removi a verificação de .active.is_(True) para simplificar,
            # pois seu model básico pode não ter essa coluna ainda.
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
                raise ValueError("Categoria já existe")

            nova_categoria = Category(
                user_id=user_id,
                name=categoria_nome,
                type=tipo
            )

            self.db.add(nova_categoria)
            self.db.commit()

            logger.info(
                "Categoria adicionada | user_id=%s categoria=%s tipo=%s",
                user_id, categoria_nome, tipo
            )

            return True

        except Exception:
            self.db.rollback()
            logger.exception(
                "Erro ao adicionar categoria | user_id=%s categoria=%s tipo=%s",
                user_id, categoria_nome, tipo
            )
            raise