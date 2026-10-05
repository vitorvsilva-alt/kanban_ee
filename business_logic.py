"""
Business logic and score calculation rules based on 'Planilha de controle - Planejamento.xlsx'.

Formula:
  Score = Impacto * Urgência * (6 - Esforço)
  
Escalas:
  - Impacto (1 a 5): Quanto a iniciativa ajuda o negócio
  - Urgência (1 a 5): Quão rápido precisa ser resolvida
  - Esforço (1 a 5): Quanto recurso/tempo ela consome (1 = menor esforço, 5 = maior esforço)
  
Prioridades:
  - Score >= 80: Crítico ("Alta combinação de impacto e urgência com menor esforço")
  - Score >= 45: Alto ("Deve entrar no ciclo prioritário de execução")
  - Score >= 20: Médio ("Planejar após os itens críticos e altos")
  - Score < 20: Baixo ("Manter no backlog e revisar periodicamente")

Farol (SLA de Prazo):
  - Concluído: Verde
  - Sem prazo: Cinza
  - Prazo < Hoje: Vermelho (Vencido)
  - Prazo <= Hoje + 7 dias: Amarelo (Atenção / Próximo do vencimento)
  - Prazo > Hoje + 7 dias: Verde (No prazo)
"""

from datetime import date, datetime
from typing import Any, Optional, Tuple
import pandas as pd

STATUS_LIST = [
    "Não iniciado",
    "Em análise",
    "Planejado",
    "Em andamento",
    "Bloqueado",
    "Concluído"
]

AREAS_LIST = [
    "Faturamento",
    "CX",
    "Operações",
    "Setor de cadastro",
    "Tecnologia",
    "Financeiro"
]

INTERFERENCIA_LIST = [
    "Processo",
    "Sistema / Dados",
    "Pessoas",
    "Governança",
    "Fornecedor / Terceiro"
]

PRIORIDADE_LIST = [
    "Crítico",
    "Alto",
    "Médio",
    "Baixo"
]

PRIORIDADE_COLORS = {
    "Crítico": {"bg": "#FDEDEC", "border": "#E74C3C", "text": "#900C3F", "badge": "#C0392B"},
    "Alto": {"bg": "#FEF5E7", "border": "#F39C12", "text": "#B9770E", "badge": "#E67E22"},
    "Médio": {"bg": "#FEFDE8", "border": "#F1C40F", "text": "#7D6608", "badge": "#D4AC0D"},
    "Baixo": {"bg": "#EBF5FB", "border": "#5DADE2", "text": "#1B4F72", "badge": "#2980B9"}
}

FAROL_COLORS = {
    "Verde": {"hex": "#27AE60", "label": "No Prazo / Concluído", "icon": "🟢"},
    "Amarelo": {"hex": "#F39C12", "label": "Atenção (<= 7 dias)", "icon": "🟡"},
    "Vermelho": {"hex": "#E74C3C", "label": "Vencido", "icon": "🔴"},
    "Cinza": {"hex": "#95A5A6", "label": "Sem Prazo", "icon": "⚪"}
}

STATUS_COLORS = {
    "Não iniciado": "#7F8C8D",
    "Em análise": "#3498DB",
    "Planejado": "#9B59B6",
    "Em andamento": "#E67E22",
    "Bloqueado": "#E74C3C",
    "Concluído": "#27AE60"
}


def calculate_score(impacto: int, urgencia: int, esforco: int) -> int:
    """Calcula o score de priorização pela fórmula da planilha."""
    try:
        imp = int(impacto)
        urg = int(urgencia)
        esf = int(esforco)
        imp = max(1, min(5, imp))
        urg = max(1, min(5, urg))
        esf = max(1, min(5, esf))
        return imp * urg * (6 - esf)
    except (ValueError, TypeError):
        return 0


def calculate_prioridade(score: int) -> str:
    """Determina a prioridade com base nos limites definidos na planilha."""
    if score is None or score == "":
        return "Baixo"
    try:
        sc = int(score)
        if sc >= 80:
            return "Crítico"
        elif sc >= 45:
            return "Alto"
        elif sc >= 20:
            return "Médio"
        else:
            return "Baixo"
    except (ValueError, TypeError):
        return "Baixo"


def calculate_farol(status: str, prazo: Optional[Any] = None) -> str:
    """
    Calcula o indicador do Farol:
    - Status 'Concluído' -> Verde
    - Sem prazo -> Cinza
    - Prazo < Hoje -> Vermelho
    - Prazo <= Hoje + 7 dias -> Amarelo
    - Caso contrário -> Verde
    """
    if status == "Concluído":
        return "Verde"
    
    if prazo is None or pd.isna(prazo):
        return "Cinza"
    
    target_date = None
    if isinstance(prazo, datetime):
        target_date = prazo.date()
    elif isinstance(prazo, date):
        target_date = prazo
    elif hasattr(prazo, "date"):
        try:
            target_date = prazo.date()
        except Exception:
            target_date = None
    elif isinstance(prazo, str):
        prazo_clean = prazo.strip()
        if not prazo_clean or prazo_clean.lower() in ("none", "nat", "nan"):
            return "Cinza"
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y-%m-%d %H:%M:%S", "%d-%m-%Y"):
            try:
                target_date = datetime.strptime(prazo_clean, fmt).date()
                break
            except ValueError:
                continue
    
    if target_date is None or pd.isna(target_date):
        return "Cinza"
    
    today = date.today()
    try:
        diff_days = (target_date - today).days
    except Exception:
        return "Cinza"
    
    if diff_days < 0:
        return "Vermelho"
    elif diff_days <= 7:
        return "Amarelo"
    else:
        return "Verde"
