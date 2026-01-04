import io
import logging
from typing import Optional
import pandas as pd

logger = logging.getLogger(__name__)

class ExportService:
    """
    Serviço responsável por exportar dados para download (Em memória).
    """

    def export_csv_buffer(self, df: pd.DataFrame) -> io.BytesIO:
        """
        Converte DataFrame para buffer CSV em memória (UTF-8).
        Ideal para botão de download do Streamlit.
        """
        if df is None or df.empty:
            return None

        try:
            df_export = self._preparar_df(df)
            
            # Buffer em memória (não salva no disco)
            buffer = io.BytesIO()
            df_export.to_csv(buffer, index=False, encoding="utf-8-sig")
            buffer.seek(0)
            
            return buffer

        except Exception:
            logger.exception("Erro ao gerar buffer CSV")
            return None

    @staticmethod
    def _preparar_df(df: pd.DataFrame) -> pd.DataFrame:
        df_out = df.copy()
        
        # Remove colunas técnicas desnecessárias para o usuário final
        colunas_remover = ["id", "user_id", "category_id", "account_id"]
        cols_existentes = [c for c in colunas_remover if c in df_out.columns]
        
        if cols_existentes:
            df_out.drop(columns=cols_existentes, inplace=True)

        if "date" in df_out.columns:
            df_out["date"] = pd.to_datetime(df_out["date"]).dt.strftime("%d/%m/%Y")
            df_out = df_out.sort_values("date", ascending=False)

        return df_out