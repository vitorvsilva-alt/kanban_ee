"""
Database layer using local DuckDB for the Kanban system.
Handles schema initialization, data migration from Excel, and CRUD operations.
"""

import os
import re
from datetime import date, datetime
from typing import Any, Dict, List, Optional
import duckdb
import openpyxl
import pandas as pd

from business_logic import (
    calculate_farol,
    calculate_prioridade,
    calculate_score
)

DB_PATH = "kanban.duckdb"
EXCEL_PATH = "Planilha de controle - Planejamento.xlsx"


def get_connection(read_only: bool = False) -> duckdb.DuckDBPyConnection:
    """Retorna uma conexão DuckDB local."""
    return duckdb.connect(database=DB_PATH, read_only=read_only)


def init_db(force_reseed: bool = False):
    """
    Inicializa as tabelas no DuckDB.
    Se a tabela estiver vazia, importa automaticamente os dados da planilha Excel existente.
    """
    with get_connection() as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS tarefas (
                id VARCHAR PRIMARY KEY,
                area_lider VARCHAR,
                area_impactada VARCHAR,
                descricao_problema VARCHAR,
                previa_solucao VARCHAR,
                tipo_interferencia VARCHAR,
                impacto INTEGER,
                urgencia INTEGER,
                esforco INTEGER,
                score INTEGER,
                prioridade VARCHAR,
                status VARCHAR,
                responsavel VARCHAR,
                data_inicio DATE,
                prazo DATE,
                meta VARCHAR,
                proxima_acao VARCHAR,
                ultima_atualizacao VARCHAR,
                farol VARCHAR
            );
        """)
        count = con.execute("SELECT COUNT(*) FROM tarefas").fetchone()[0]

        con.execute("""
            CREATE TABLE IF NOT EXISTS categorias_areas (
                nome VARCHAR PRIMARY KEY,
                criado_em TIMESTAMP
            );
        """)
        area_count = con.execute("SELECT COUNT(*) FROM categorias_areas").fetchone()[0]
        if area_count == 0:
            defaults = ["Faturamento", "CX", "Operações", "Setor de cadastro", "Tecnologia", "Financeiro"]
            for d in defaults:
                con.execute("INSERT OR IGNORE INTO categorias_areas VALUES (?, current_timestamp)", [d])
        
    if count == 0 or force_reseed:
        if os.path.exists(EXCEL_PATH):
            import_from_excel(EXCEL_PATH, overwrite=force_reseed)


def import_from_excel(file_path: str, overwrite: bool = False) -> int:
    """
    Importa dados da aba 'Plano Estratégico' da planilha Excel para o DuckDB.
    """
    wb = openpyxl.load_workbook(file_path, data_only=True)
    if "Plano Estratégico" not in wb.sheetnames:
        return 0

    ws = wb["Plano Estratégico"]
    
    header_row = [ws.cell(1, c).value for c in range(1, ws.max_column + 1)]
    col_map = {}
    for idx, h in enumerate(header_row, 1):
        if h:
            norm = str(h).strip().lower()
            col_map[norm] = idx
            
    def get_val(row_idx, col_name_patterns):
        for pattern in col_name_patterns:
            for h_norm, c_idx in col_map.items():
                if pattern in h_norm:
                    val = ws.cell(row_idx, c_idx).value
                    return val
        return None

    imported_rows = []
    
    for r in range(2, ws.max_row + 1):
        id_val = get_val(r, ["id"])
        area_lider = get_val(r, ["área líder", "area lider", "líder", "lider"])
        desc = get_val(r, ["descrição do problema", "descricao do problema", "problema", "descrição"])
        
        if not id_val and not area_lider and not desc:
            continue
            
        area_impactada = get_val(r, ["área impactada", "area impactada", "impactada"])
        previa_solucao = get_val(r, ["prévia da solução", "previa da solucao", "solução", "solucao"])
        tipo_interferencia = get_val(r, ["tipo de interferência", "tipo de interferencia", "interferência", "interferencia"])
        
        try:
            impacto = int(get_val(r, ["impacto"]) or 3)
        except (ValueError, TypeError):
            impacto = 3
            
        try:
            urgencia = int(get_val(r, ["urgência", "urgencia"]) or 3)
        except (ValueError, TypeError):
            urgencia = 3
            
        try:
            esforco = int(get_val(r, ["esforço", "esforco"]) or 3)
        except (ValueError, TypeError):
            esforco = 3
            
        status = get_val(r, ["status"]) or "Não iniciado"
        responsavel = get_val(r, ["responsável", "responsavel"]) or ""
        
        data_inicio = get_val(r, ["início", "inicio", "data início"])
        if isinstance(data_inicio, (datetime, date)):
            data_inicio_str = data_inicio.strftime("%Y-%m-%d")
        else:
            data_inicio_str = None
            
        prazo = get_val(r, ["prazo", "data limite", "limite"])
        if isinstance(prazo, (datetime, date)):
            prazo_str = prazo.strftime("%Y-%m-%d")
        else:
            prazo_str = None

        meta = get_val(r, ["meta"]) or ""
        proxima_acao = get_val(r, ["próxima ação", "proxima acao", "próxima", "proxima"]) or ""
        
        ultima_att = get_val(r, ["última atualização", "ultima atualizacao", "atualização"])
        if isinstance(ultima_att, (datetime, date)):
            ultima_att_str = ultima_att.strftime("%Y-%m-%d %H:%M:%S")
        else:
            ultima_att_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        score = calculate_score(impacto, urgencia, esforco)
        prioridade = calculate_prioridade(score)
        farol = calculate_farol(status, prazo_str)
        
        if not id_val:
            id_val = f"P.E-{r-1:03d}"
            
        imported_rows.append({
            "id": str(id_val).strip(),
            "area_lider": str(area_lider or "").strip(),
            "area_impactada": str(area_impactada or "").strip(),
            "descricao_problema": str(desc or "").strip(),
            "previa_solucao": str(previa_solucao or "").strip(),
            "tipo_interferencia": str(tipo_interferencia or "Processo").strip(),
            "impacto": impacto,
            "urgencia": urgencia,
            "esforco": esforco,
            "score": score,
            "prioridade": prioridade,
            "status": str(status).strip(),
            "responsavel": str(responsavel or "").strip(),
            "data_inicio": data_inicio_str,
            "prazo": prazo_str,
            "meta": str(meta or "").strip(),
            "proxima_acao": str(proxima_acao or "").strip(),
            "ultima_atualizacao": ultima_att_str,
            "farol": farol
        })

    with get_connection() as con:
        if overwrite:
            con.execute("DELETE FROM tarefas")
            
        for row in imported_rows:
            con.execute("""
                INSERT OR REPLACE INTO tarefas (
                    id, area_lider, area_impactada, descricao_problema, previa_solucao,
                    tipo_interferencia, impacto, urgencia, esforco, score, prioridade,
                    status, responsavel, data_inicio, prazo, meta, proxima_acao,
                    ultima_atualizacao, farol
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, [
                row["id"], row["area_lider"], row["area_impactada"], row["descricao_problema"],
                row["previa_solucao"], row["tipo_interferencia"], row["impacto"], row["urgencia"],
                row["esforco"], row["score"], row["prioridade"], row["status"], row["responsavel"],
                row["data_inicio"], row["prazo"], row["meta"], row["proxima_acao"],
                row["ultima_atualizacao"], row["farol"]
            ])

    return len(imported_rows)


def get_next_task_id() -> str:
    """Calcula o próximo ID sequencial no padrão P.E-001."""
    with get_connection(read_only=True) as con:
        ids = con.execute("SELECT id FROM tarefas").fetchall()
        
    max_num = 0
    pattern = re.compile(r"P\.E-(\d+)", re.IGNORECASE)
    for (tid,) in ids:
        match = pattern.match(str(tid).strip())
        if match:
            num = int(match.group(1))
            if num > max_num:
                max_num = num
                
    return f"P.E-{max_num + 1:03d}"


def get_all_tasks(order_by: str = "score DESC") -> pd.DataFrame:
    """Busca todas as tarefas cadastradas com os faróis atualizados."""
    with get_connection() as con:
        df = con.execute(f"SELECT * FROM tarefas ORDER BY {order_by}").fetchdf()

    if not df.empty:
        updated_farois = []
        for _, row in df.iterrows():
            calc_f = calculate_farol(row["status"], row["prazo"])
            updated_farois.append(calc_f)
        df["farol"] = updated_farois
        
    return df


def get_task_by_id(task_id: str) -> Optional[Dict[str, Any]]:
    """Retorna os dados de uma tarefa específica por ID."""
    with get_connection(read_only=True) as con:
        result = con.execute("SELECT * FROM tarefas WHERE id = ?", [task_id]).fetchdf()
    
    if result.empty:
        return None
    
    task_dict = result.iloc[0].to_dict()
    for k, v in list(task_dict.items()):
        if pd.isna(v):
            task_dict[k] = None
    task_dict["farol"] = calculate_farol(task_dict["status"], task_dict["prazo"])
    return task_dict


def add_task(data: Dict[str, Any]) -> str:
    """Insere uma nova tarefa no DuckDB."""
    task_id = data.get("id") or get_next_task_id()
    impacto = int(data.get("impacto", 3))
    urgencia = int(data.get("urgencia", 3))
    esforco = int(data.get("esforco", 3))
    
    score = calculate_score(impacto, urgencia, esforco)
    prioridade = calculate_prioridade(score)
    status = data.get("status", "Não iniciado")
    prazo = data.get("prazo")
    farol = calculate_farol(status, prazo)
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with get_connection() as con:
        con.execute("""
            INSERT INTO tarefas (
                id, area_lider, area_impactada, descricao_problema, previa_solucao,
                tipo_interferencia, impacto, urgencia, esforco, score, prioridade,
                status, responsavel, data_inicio, prazo, meta, proxima_acao,
                ultima_atualizacao, farol
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            task_id,
            data.get("area_lider", ""),
            data.get("area_impactada", ""),
            data.get("descricao_problema", ""),
            data.get("previa_solucao", ""),
            data.get("tipo_interferencia", "Processo"),
            impacto,
            urgencia,
            esforco,
            score,
            prioridade,
            status,
            data.get("responsavel", ""),
            data.get("data_inicio"),
            prazo,
            data.get("meta", ""),
            data.get("proxima_acao", ""),
            now_str,
            farol
        ])
    return task_id


def update_task(task_id: str, data: Dict[str, Any]) -> bool:
    """Atualiza todos os dados de uma tarefa existente."""
    impacto = int(data.get("impacto", 3))
    urgencia = int(data.get("urgencia", 3))
    esforco = int(data.get("esforco", 3))
    
    score = calculate_score(impacto, urgencia, esforco)
    prioridade = calculate_prioridade(score)
    status = data.get("status", "Não iniciado")
    prazo = data.get("prazo")
    farol = calculate_farol(status, prazo)
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with get_connection() as con:
        con.execute("""
            UPDATE tarefas SET
                area_lider = ?,
                area_impactada = ?,
                descricao_problema = ?,
                previa_solucao = ?,
                tipo_interferencia = ?,
                impacto = ?,
                urgencia = ?,
                esforco = ?,
                score = ?,
                prioridade = ?,
                status = ?,
                responsavel = ?,
                data_inicio = ?,
                prazo = ?,
                meta = ?,
                proxima_acao = ?,
                ultima_atualizacao = ?,
                farol = ?
            WHERE id = ?
        """, [
            data.get("area_lider", ""),
            data.get("area_impactada", ""),
            data.get("descricao_problema", ""),
            data.get("previa_solucao", ""),
            data.get("tipo_interferencia", "Processo"),
            impacto,
            urgencia,
            esforco,
            score,
            prioridade,
            status,
            data.get("responsavel", ""),
            data.get("data_inicio"),
            prazo,
            data.get("meta", ""),
            data.get("proxima_acao", ""),
            now_str,
            farol,
            task_id
        ])
    return True


def update_task_status(task_id: str, new_status: str) -> bool:
    """Atualiza apenas o status de uma tarefa e recalcula seu farol."""
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with get_connection() as con:
        task = con.execute("SELECT prazo FROM tarefas WHERE id = ?", [task_id]).fetchone()
        if not task:
            return False
        prazo = task[0]
        farol = calculate_farol(new_status, prazo)
        
        con.execute("""
            UPDATE tarefas SET
                status = ?,
                farol = ?,
                ultima_atualizacao = ?
            WHERE id = ?
        """, [new_status, farol, now_str, task_id])
    return True


def mark_as_completed(task_id: str) -> bool:
    """Marca a tarefa como Concluído e Farol Verde com 1 clique."""
    return update_task_status(task_id, "Concluído")


def delete_task(task_id: str) -> bool:
    """Remove uma tarefa do banco de dados."""
    with get_connection() as con:
        con.execute("DELETE FROM tarefas WHERE id = ?", [task_id])
    return True


def get_kpis() -> Dict[str, Any]:
    """
    Calcula os KPIs executivos espelhando a aba 'Painel Executivo' da planilha.
    """
    df = get_all_tasks()
    if df.empty:
        return {
            "total": 0,
            "em_aberto": 0,
            "critico": 0,
            "prazos_em_risco": 0,
            "resumo_texto": "Nenhuma iniciativa cadastrada no momento."
        }
        
    total = len(df)
    em_aberto = len(df[df["status"] != "Concluído"])
    critico = len(df[df["prioridade"] == "Crítico"])
    prazos_em_risco = len(df[df["farol"] == "Vermelho"])
    
    resumo_texto = (
        f"O planejamento possui {total} iniciativas, das quais {em_aberto} estão em aberto. "
        f"Há {critico} item(ns) de prioridade crítica e {prazos_em_risco} prazo(s) vencido(s). "
        f"Use o score para ordenar a execução e Dependências para coordenar os handoffs entre áreas."
    )
    
    return {
        "total": total,
        "em_aberto": em_aberto,
        "critico": critico,
        "prazos_em_risco": prazos_em_risco,
        "resumo_texto": resumo_texto
    }


def export_to_excel(output_path: str = "kanban_export.xlsx") -> str:
    """Exporta todas as tarefas atuais de volta para uma planilha Excel formatada."""
    df = get_all_tasks(order_by="score DESC")
    
    rename_cols = {
        "id": "ID",
        "area_lider": "Área líder",
        "area_impactada": "Área impactada",
        "descricao_problema": "Descrição do problema",
        "previa_solucao": "Prévia da solução",
        "tipo_interferencia": "Tipo de interferência",
        "impacto": "Impacto",
        "urgencia": "Urgência",
        "esforco": "Esforço",
        "score": "Score",
        "prioridade": "Prioridade",
        "status": "Status",
        "responsavel": "Responsável",
        "data_inicio": "Início",
        "prazo": "Prazo",
        "meta": "Meta",
        "proxima_acao": "Próxima ação",
        "ultima_atualizacao": "Última atualização",
        "farol": "Farol"
    }
    
    export_df = df.rename(columns=rename_cols)
    export_df.to_excel(output_path, index=False, sheet_name="Plano Estratégico")
    return output_path

# ==============================================================================
# GESTÃO DE CATEGORIAS DE ÁREAS (LÍDER E IMPACTADAS)
# ==============================================================================

def get_all_areas() -> List[str]:
    """Retorna a lista de todas as áreas cadastradas ordenadas alfabeticamente."""
    with get_connection(read_only=True) as con:
        rows = con.execute("SELECT nome FROM categorias_areas ORDER BY nome ASC").fetchall()
    return [r[0] for r in rows] if rows else ["Faturamento", "CX", "Operações", "Setor de cadastro", "Tecnologia", "Financeiro"]


def add_area(nome: str) -> bool:
    """Adiciona uma nova área à lista de categorias."""
    clean_nome = nome.strip()
    if not clean_nome:
        return False
    with get_connection() as con:
        con.execute("INSERT OR REPLACE INTO categorias_areas (nome, criado_em) VALUES (?, current_timestamp)", [clean_nome])
    return True


def remove_area(nome: str) -> bool:
    """Remove uma área da lista de categorias."""
    clean_nome = nome.strip()
    if not clean_nome:
        return False
    with get_connection() as con:
        con.execute("DELETE FROM categorias_areas WHERE nome = ?", [clean_nome])
    return True


def update_area(old_name: str, new_name: str, update_tasks: bool = True) -> bool:
    """Renomeia uma área existente e opcionalmente atualiza as tarefas associadas."""
    old_name = old_name.strip()
    new_name = new_name.strip()
    if not new_name or old_name == new_name:
        return False
    with get_connection() as con:
        con.execute("INSERT OR REPLACE INTO categorias_areas (nome, criado_em) VALUES (?, current_timestamp)", [new_name])
        con.execute("DELETE FROM categorias_areas WHERE nome = ?", [old_name])
        if update_tasks:
            con.execute("UPDATE tarefas SET area_lider = ? WHERE area_lider = ?", [new_name, old_name])
            # Atualiza também nas áreas impactadas se for o nome exato
            con.execute("""
                UPDATE tarefas 
                SET area_impactada = REPLACE(area_impactada, ?, ?)
                WHERE area_impactada LIKE '%' || ? || '%'
            """, [old_name, new_name, old_name])
    return True


def get_area_stats() -> List[Dict[str, Any]]:
    """Retorna cada área cadastrada com o número de iniciativas em que atua como Líder e Impactada."""
    areas = get_all_areas()
    stats = []
    with get_connection(read_only=True) as con:
        for a in areas:
            count_lider = con.execute("SELECT COUNT(*) FROM tarefas WHERE area_lider = ?", [a]).fetchone()[0]
            count_impactada = con.execute("SELECT COUNT(*) FROM tarefas WHERE area_impactada LIKE '%' || ? || '%'", [a]).fetchone()[0]
            stats.append({
                "nome": a,
                "qtd_lider": count_lider,
                "qtd_impactada": count_impactada,
                "total_vinculos": count_lider + count_impactada
            })
    return stats
