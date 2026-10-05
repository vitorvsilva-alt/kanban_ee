"""
Sistema de Gestão Kanban & Planejamento Estratégico Cross-Áreas
Desenvolvido em Streamlit com Banco de Dados DuckDB Local.
"""

import io
from datetime import date, datetime
import altair as alt
import pandas as pd
import streamlit as st

import database
from business_logic import (
    AREAS_LIST,
    FAROL_COLORS,
    INTERFERENCIA_LIST,
    PRIORIDADE_COLORS,
    PRIORIDADE_LIST,
    STATUS_COLORS,
    STATUS_LIST,
    calculate_farol,
    calculate_prioridade,
    calculate_score
)

# Configuração da página Streamlit
st.set_page_config(
    page_title="Kanban Estratégico Cross-Áreas",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Inicializa o banco de dados DuckDB e importa planilha se necessário
database.init_db()

STATUS_FLOW_NEXT = {
    "Não iniciado": "Em análise",
    "Em análise": "Planejado",
    "Planejado": "Em andamento",
    "Em andamento": "Concluído",
    "Bloqueado": "Em andamento",
    "Concluído": None
}

STATUS_FLOW_PREV = {
    "Não iniciado": None,
    "Em análise": "Não iniciado",
    "Planejado": "Em análise",
    "Em andamento": "Planejado",
    "Bloqueado": "Em andamento",
    "Concluído": "Em andamento"
}

st.markdown("""
<style>
    .main .block-container {
        padding-top: 1.2rem;
        padding-bottom: 2rem;
    }
    .kanban-column-header {
        font-weight: 700;
        font-size: 0.92rem;
        padding: 8px 12px;
        border-radius: 8px;
        margin-bottom: 12px;
        color: white;
        display: flex;
        justify-content: space-between;
        align-items: center;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
    .kanban-card {
        background-color: #FFFFFF;
        border-radius: 8px;
        padding: 12px 14px;
        margin-bottom: 10px;
        border: 1px solid #E2E8F0;
        border-left-width: 6px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.04);
        transition: transform 0.15s ease, box-shadow 0.15s ease;
    }
    .kanban-card:hover {
        box-shadow: 0 4px 14px rgba(0,0,0,0.1);
        transform: translateY(-2px);
    }
    .badge {
        display: inline-block;
        padding: 2px 7px;
        border-radius: 10px;
        font-size: 0.72rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.4px;
    }
    .badge-score {
        background-color: #1E293B;
        color: #FFFFFF;
    }
    .badge-area {
        background-color: #F1F5F9;
        color: #334155;
        font-weight: 600;
        border: 1px solid #CBD5E1;
    }
    .badge-interferencia {
        background-color: #ECFDF5;
        color: #065F46;
        font-weight: 600;
        border: 1px solid #A7F3D0;
    }
    .farol-indicator {
        display: inline-flex;
        align-items: center;
        gap: 4px;
        font-size: 0.75rem;
        font-weight: 600;
        padding: 2px 7px;
        border-radius: 10px;
    }
    .narrative-box {
        background: #F8FAFC;
        border-left: 5px solid #2563EB;
        padding: 12px 16px;
        border-radius: 6px;
        margin-bottom: 16px;
        font-size: 0.92rem;
        color: #1E293B;
        line-height: 1.5;
        box-shadow: 0 1px 2px rgba(0,0,0,0.03);
    }
</style>
""", unsafe_allow_html=True)


@st.dialog("📝 Detalhes e Edição da Iniciativa", width="large")
def task_detail_modal(task_id: str):
    """Modal completo para visualização e edição de uma tarefa."""
    task = database.get_task_by_id(task_id)
    if not task:
        st.error(f"Iniciativa {task_id} não encontrada.")
        return

    st.subheader(f"{task['id']} — {task['area_lider']}")
    
    tab_view, tab_edit = st.tabs(["👁️ Visualizar Detalhes", "✏️ Editar Iniciativa"])
    
    with tab_view:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Score", task["score"])
        c2.metric("Prioridade", task["prioridade"])
        c3.metric("Status", task["status"])
        farol_info = FAROL_COLORS.get(task["farol"], FAROL_COLORS["Cinza"])
        c4.metric("Farol de Prazo", f"{farol_info['icon']} {task['farol']}")
        
        st.divider()
        
        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown(f"**🏢 Área Líder:** {task['area_lider'] or 'Não informada'}")
            st.markdown(f"**🎯 Área Impactada:** {task['area_impactada'] or 'Não informada'}")
            st.markdown(f"**⚡ Tipo de Interferência:** {task['tipo_interferencia'] or 'Não informado'}")
            st.markdown(f"**👤 Responsável:** {task['responsavel'] or 'Não atribuído'}")
        with col_b:
            st.markdown(f"**📅 Data de Início:** {task['data_inicio'] or 'Não definida'}")
            st.markdown(f"**⏰ Prazo:** {task['prazo'] or 'Sem prazo'}")
            st.markdown(f"**🎯 Meta:** {task['meta'] or 'Não definida'}")
            st.markdown(f"**🕒 Última Atualização:** {task['ultima_atualizacao'] or '—'}")
            
        st.markdown("#### 🔍 Descrição do Problema")
        st.info(task["descricao_problema"] or "Nenhuma descrição detalhada.")
        
        st.markdown("#### 💡 Prévia da Solução")
        st.success(task["previa_solucao"] or "Nenhuma prévia da solução informada.")
        
        if task.get("proxima_acao"):
            st.markdown("#### 🚀 Próxima Ação")
            st.warning(task["proxima_acao"])

        st.divider()
        col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 1])
        if task["status"] != "Concluído":
            if col_btn1.button("✅ Marcar como Concluída", key=f"dlg_concluir_{task_id}", use_container_width=True, type="primary"):
                database.mark_as_completed(task_id)
                st.success("Iniciativa marcada como Concluída!")
                st.rerun()
        else:
            if col_btn1.button("↩️ Reabrir Iniciativa", key=f"dlg_reabrir_{task_id}", use_container_width=True):
                database.update_task_status(task_id, "Em andamento")
                st.info("Iniciativa reaberta para 'Em andamento'!")
                st.rerun()

        if col_btn3.button("🗑️ Excluir Tarefa", key=f"dlg_del_{task_id}", use_container_width=True):
            database.delete_task(task_id)
            st.warning("Iniciativa excluída.")
            st.rerun()

    with tab_edit:
        with st.form(key=f"edit_form_{task_id}"):
            f_col1, f_col2 = st.columns(2)
            with f_col1:
                current_areas = database.get_all_areas()
                curr_lead = task["area_lider"] or ""
                lead_opts = current_areas if curr_lead in current_areas or not curr_lead else [curr_lead] + current_areas
                e_area_lider = st.selectbox(
                    "Área Líder *",
                    options=lead_opts,
                    index=lead_opts.index(curr_lead) if curr_lead in lead_opts else 0
                )
                
                curr_impactadas_text = str(task["area_impactada"] or "")
                preselected_impactadas = [a for a in current_areas if a.lower() in curr_impactadas_text.lower()]
                e_areas_impactadas = st.multiselect(
                    "Área(s) Impactada(s)",
                    options=current_areas,
                    default=preselected_impactadas,
                    help="Selecione as áreas que serão impactadas por esta iniciativa."
                )
                e_area_impactada_custom = st.text_input(
                    "Complemento / Outras áreas impactadas",
                    value="" if preselected_impactadas and curr_impactadas_text == ", ".join(preselected_impactadas) else curr_impactadas_text,
                    help="Especifique manualmente caso haja terceiros ou áreas não cadastradas."
                )
                e_tipo_interf = st.selectbox(
                    "Tipo de Interferência",
                    options=INTERFERENCIA_LIST,
                    index=INTERFERENCIA_LIST.index(task["tipo_interferencia"]) if task["tipo_interferencia"] in INTERFERENCIA_LIST else 0
                )
                e_status = st.selectbox(
                    "Status",
                    options=STATUS_LIST,
                    index=STATUS_LIST.index(task["status"]) if task["status"] in STATUS_LIST else 0
                )
                e_responsavel = st.text_input("Responsável", value=task["responsavel"] or "")
            
            with f_col2:
                default_inicio = None
                val_ini = task.get("data_inicio")
                if val_ini is not None and not pd.isna(val_ini):
                    try:
                        dt = pd.to_datetime(val_ini)
                        if not pd.isna(dt):
                            d = dt.date()
                            if not pd.isna(d):
                                default_inicio = d
                    except Exception:
                        default_inicio = None
                        
                default_prazo = None
                val_prz = task.get("prazo")
                if val_prz is not None and not pd.isna(val_prz):
                    try:
                        dt = pd.to_datetime(val_prz)
                        if not pd.isna(dt):
                            d = dt.date()
                            if not pd.isna(d):
                                default_prazo = d
                    except Exception:
                        default_prazo = None
                
                e_data_inicio = st.date_input("Data de Início", value=default_inicio)
                e_prazo = st.date_input("Prazo Final", value=default_prazo)
                e_meta = st.text_input("Meta", value=task["meta"] or "")
                e_proxima_acao = st.text_input("Próxima Ação", value=task["proxima_acao"] or "")

            e_problema = st.text_area("Descrição do Problema", value=task["descricao_problema"] or "", height=90)
            e_solucao = st.text_area("Prévia da Solução", value=task["previa_solucao"] or "", height=80)
            
            st.markdown("##### ⚖️ Avaliação de Priorização (Fórmula do Score)")
            p_col1, p_col2, p_col3 = st.columns(3)
            with p_col1:
                e_impacto = st.slider("Impacto (1 = baixo, 5 = alto)", 1, 5, int(task.get("impacto") or 3))
            with p_col2:
                e_urgencia = st.slider("Urgência (1 = baixa, 5 = alta)", 1, 5, int(task.get("urgencia") or 3))
            with p_col3:
                e_esforco = st.slider("Esforço (1 = baixo, 5 = alto)", 1, 5, int(task.get("esforco") or 3))
            
            calc_sc = calculate_score(e_impacto, e_urgencia, e_esforco)
            calc_pri = calculate_prioridade(calc_sc)
            st.caption(f"💡 Score resultante: **{calc_sc}** | Prioridade calculada: **{calc_pri}** [Fórmula: {e_impacto} × {e_urgencia} × (6 - {e_esforco})]")

            submitted = st.form_submit_button("💾 Salvar Alterações", use_container_width=True, type="primary")
            if submitted:
                updated_data = {
                    "area_lider": e_area_lider,
                                        "area_impactada": ", ".join(list(e_areas_impactadas) + ([e_area_impactada_custom.strip()] if e_area_impactada_custom.strip() and e_area_impactada_custom.strip() not in e_areas_impactadas else [])) if (e_areas_impactadas or e_area_impactada_custom.strip()) else "", 
                    "tipo_interferencia": e_tipo_interf,
                    "status": e_status,
                    "responsavel": e_responsavel,
                    "data_inicio": e_data_inicio.strftime("%Y-%m-%d") if e_data_inicio else None,
                    "prazo": e_prazo.strftime("%Y-%m-%d") if e_prazo else None,
                    "meta": e_meta,
                    "proxima_acao": e_proxima_acao,
                    "descricao_problema": e_problema,
                    "previa_solucao": e_solucao,
                    "impacto": e_impacto,
                    "urgencia": e_urgencia,
                    "esforco": e_esforco
                }
                database.update_task(task_id, updated_data)
                st.success("Iniciativa atualizada com sucesso!")
                st.rerun()


with st.sidebar:
    st.title("🎛️ Painel de Controle")
    st.caption("Organizador Kanban & Planejamento Cross-Áreas")
    st.divider()

    st.subheader("🔍 Filtros")
    search_query = st.text_input("Buscar por texto ou ID:", placeholder="Ex: CRM, faturas, P.E-001...")
    
    current_areas_list = database.get_all_areas()
    filtro_area = st.multiselect(
        "Área Líder:",
        options=current_areas_list,
        default=[]
    )
    
    filtro_prioridade = st.multiselect(
        "Prioridade:",
        options=PRIORIDADE_LIST,
        default=[]
    )
    
    filtro_interferencia = st.multiselect(
        "Tipo de Interferência:",
        options=INTERFERENCIA_LIST,
        default=[]
    )
    
    filtro_farol = st.multiselect(
        "Farol de Prazo:",
        options=["Verde", "Amarelo", "Vermelho", "Cinza"],
        default=[]
    )

    st.divider()
    st.markdown("### ℹ️ Regra do Score")
    st.latex(r"\text{Score} = \text{Imp.} \times \text{Urg.} \times (6 - \text{Esf.})")
    st.caption("""
    • **Crítico**: Score ≥ 80
    • **Alto**: Score ≥ 45
    • **Médio**: Score ≥ 20
    • **Baixo**: Score < 20
    """)
    
    st.divider()
    df_raw = database.get_all_tasks()
    if not df_raw.empty:
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df_raw.to_excel(writer, index=False, sheet_name="Plano Estratégico")
        st.download_button(
            label="📥 Exportar Excel Atualizado",
            data=buffer.getvalue(),
            file_name=f"planejamento_kanban_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )


df_tasks = database.get_all_tasks(order_by="score DESC")

if search_query:
    q = search_query.lower()
    df_tasks = df_tasks[
        df_tasks["id"].str.lower().str.contains(q, na=False) |
        df_tasks["descricao_problema"].str.lower().str.contains(q, na=False) |
        df_tasks["previa_solucao"].str.lower().str.contains(q, na=False) |
        df_tasks["area_lider"].str.lower().str.contains(q, na=False) |
        df_tasks["responsavel"].str.lower().str.contains(q, na=False)
    ]

if filtro_area:
    df_tasks = df_tasks[df_tasks["area_lider"].isin(filtro_area)]

if filtro_prioridade:
    df_tasks = df_tasks[df_tasks["prioridade"].isin(filtro_prioridade)]

if filtro_interferencia:
    df_tasks = df_tasks[df_tasks["tipo_interferencia"].isin(filtro_interferencia)]

if filtro_farol:
    df_tasks = df_tasks[df_tasks["farol"].isin(filtro_farol)]


st.title("📋 Planejamento Estratégico & Gestão Kanban")

kpis = database.get_kpis()
kpi1, kpi2, kpi3, kpi4 = st.columns(4)

kpi1.metric(
    "Total de Iniciativas",
    kpis["total"],
    help="Número total de iniciativas cadastradas"
)
kpi2.metric(
    "Iniciativas em Aberto",
    kpis["em_aberto"],
    delta=f"{(kpis['em_aberto']/kpis['total']*100):.0f}% do total" if kpis["total"] > 0 else "0%",
    delta_color="inverse",
    help="Iniciativas com status diferente de 'Concluído'"
)
kpi3.metric(
    "Prioridade Crítica",
    kpis["critico"],
    delta=f"{kpis['critico']} crítica(s)" if kpis["critico"] > 0 else "Nenhum crítico",
    delta_color="off",
    help="Iniciativas com Score ≥ 80"
)
kpi4.metric(
    "Prazos em Risco (Vencidos)",
    kpis["prazos_em_risco"],
    delta=f"{kpis['prazos_em_risco']} vencido(s)" if kpis["prazos_em_risco"] > 0 else "Em dia",
    delta_color="inverse",
    help="Iniciativas não concluídas com prazo anterior a hoje"
)

st.markdown(f'<div class="narrative-box">📢 <b>Resumo Executivo:</b> {kpis["resumo_texto"]}</div>', unsafe_allow_html=True)


tab_kanban, tab_nova, tab_dashboard, tab_tabela, tab_areas, tab_metodologia = st.tabs([
    "📌 Quadro Kanban",
    "➕ Nova Iniciativa",
    "📊 Painel Executivo / Gráficos",
    "📑 Tabela Completa",
    "🏢 Gestão de Áreas",
    "📖 Metodologia & Regras"
])


with tab_kanban:
    st.markdown("### 🗂️ Quadro Ágil de Iniciativas")
    st.caption("Cartões ordenados automaticamente por **Score de Prioridade (maior score no topo)**.")
    
    kanban_cols = st.columns(len(STATUS_LIST))
    
    for idx, status_name in enumerate(STATUS_LIST):
        col_color = STATUS_COLORS.get(status_name, "#34495E")
        tasks_in_col = df_tasks[df_tasks["status"] == status_name]
        
        with kanban_cols[idx]:
            st.markdown(f"""
            <div class="kanban-column-header" style="background-color: {col_color};">
                <span>{status_name}</span>
                <span style="background: rgba(255,255,255,0.25); padding: 2px 8px; border-radius: 10px; font-size: 0.8rem;">
                    {len(tasks_in_col)}
                </span>
            </div>
            """, unsafe_allow_html=True)
            
            if tasks_in_col.empty:
                st.markdown("<p style='text-align: center; color: #94A3B8; font-size: 0.82rem; padding: 15px 0;'>Nenhuma tarefa</p>", unsafe_allow_html=True)
            else:
                for _, task in tasks_in_col.iterrows():
                    tid = task["id"]
                    pri = task["prioridade"]
                    pri_style = PRIORIDADE_COLORS.get(pri, PRIORIDADE_COLORS["Baixo"])
                    farol_style = FAROL_COLORS.get(task["farol"], FAROL_COLORS["Cinza"])
                    
                    desc = task["descricao_problema"] or "Sem descrição"
                    if len(desc) > 95:
                        desc = desc[:92] + "..."
                    
                    prazo_display = task["prazo"] if pd.notna(task["prazo"]) and str(task["prazo"]).strip() != "" else "Sem prazo"
                    resp_display = task["responsavel"] if pd.notna(task["responsavel"]) and str(task["responsavel"]).strip() != "" else "Não atribuído"

                    card_html = f"""
                    <div class="kanban-card" style="border-left-color: {pri_style['border']};">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                            <span style="font-weight: 700; font-size: 0.85rem; color: #1E293B;">{tid}</span>
                            <div>
                                <span class="badge" style="background-color: {pri_style['bg']}; color: {pri_style['text']}; border: 1px solid {pri_style['border']};">
                                    {pri}
                                </span>
                                <span class="badge badge-score">
                                    ★ {task['score']}
                                </span>
                            </div>
                        </div>
                        <div style="margin-bottom: 6px;">
                            <span class="badge badge-area">{task['area_lider']}</span>
                            <span class="badge badge-interferencia">{task['tipo_interferencia']}</span>
                        </div>
                        <div style="font-size: 0.82rem; color: #334155; margin: 8px 0; line-height: 1.35; font-weight: 500;">
                            {desc}
                        </div>
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 8px; font-size: 0.75rem; color: #64748B; border-top: 1px dashed #E2E8F0; padding-top: 6px;">
                            <span>👤 {resp_display}</span>
                            <span class="farol-indicator" style="background-color: {farol_style['hex']}22; color: {farol_style['hex']};">
                                {farol_style['icon']} {prazo_display}
                            </span>
                        </div>
                    </div>
                    """
                    st.markdown(card_html, unsafe_allow_html=True)
                    
                    if st.button("🔍 Ver / Editar", key=f"btn_edit_{tid}", use_container_width=True):
                        task_detail_modal(tid)

                    next_status = STATUS_FLOW_NEXT.get(status_name)
                    prev_status = STATUS_FLOW_PREV.get(status_name)
                    
                    b_col1, b_col2 = st.columns(2)
                    
                    if status_name != "Concluído":
                        with b_col1:
                            if st.button("✅ Concluir", key=f"btn_done_{tid}", use_container_width=True, help="Marcar como Concluído"):
                                database.mark_as_completed(tid)
                                st.toast(f"Iniciativa {tid} concluída!", icon="🎉")
                                st.rerun()
                        with b_col2:
                            if next_status and next_status != "Concluído":
                                if st.button(f"➡️ Avançar", key=f"btn_next_{tid}", use_container_width=True, help=f"Mover para {next_status}"):
                                    database.update_task_status(tid, next_status)
                                    st.toast(f"{tid} movido para {next_status}", icon="🚀")
                                    st.rerun()
                            elif prev_status:
                                if st.button(f"⬅️ Voltar", key=f"btn_prev_{tid}", use_container_width=True, help=f"Voltar para {prev_status}"):
                                    database.update_task_status(tid, prev_status)
                                    st.toast(f"{tid} retornado para {prev_status}", icon="↩️")
                                    st.rerun()
                    else:
                        with b_col1:
                            if st.button("↩️ Reabrir", key=f"btn_reopen_{tid}", use_container_width=True, help="Reabrir iniciativa"):
                                database.update_task_status(tid, "Em andamento")
                                st.toast(f"{tid} reaberto para Em andamento", icon="🔄")
                                st.rerun()
                        with b_col2:
                            if st.button("🗑️ Excluir", key=f"btn_del_card_{tid}", use_container_width=True):
                                database.delete_task(tid)
                                st.toast(f"{tid} excluído.", icon="🗑️")
                                st.rerun()

                    other_statuses = ["Mover..."] + [s for s in STATUS_LIST if s != status_name]
                    sel_box = st.selectbox(
                        "Mover coluna:",
                        options=other_statuses,
                        key=f"sel_move_{tid}",
                        label_visibility="collapsed"
                    )
                    if sel_box != "Mover...":
                        database.update_task_status(tid, sel_box)
                        st.session_state[f"sel_move_{tid}"] = "Mover..."
                        st.toast(f"{tid} movido para {sel_box}", icon="🚀")
                        st.rerun()


with tab_nova:
    st.markdown("### ➕ Cadastrar Nova Iniciativa")
    st.caption("Preencha as informações abaixo. O **Score** e a **Prioridade** serão calculados automaticamente.")
    
    next_suggested_id = database.get_next_task_id()
    
    col_form, col_sim = st.columns([1.6, 1.4])
    
    with col_sim:
        st.markdown("#### ⚡ Simulador de Score em Tempo Real")
        st.info("Ajuste os controles deslizantes abaixo para simular o score e a prioridade.")
        
        sim_impacto = st.slider("1. Impacto no Negócio", 1, 5, 3, help="Quanto a iniciativa ajuda o negócio")
        sim_urgencia = st.slider("2. Urgência", 1, 5, 3, help="Quão rápido precisa ser resolvida")
        sim_esforco = st.slider("3. Esforço Necessário", 1, 5, 2, help="Quanto recurso/tempo ela consome (1 = menor esforço, 5 = esforço máximo)")
        
        sim_score = calculate_score(sim_impacto, sim_urgencia, sim_esforco)
        sim_prioridade = calculate_prioridade(sim_score)
        sim_p_style = PRIORIDADE_COLORS.get(sim_prioridade, PRIORIDADE_COLORS["Baixo"])
        
        st.markdown(f"""
        <div style="background-color: {sim_p_style['bg']}; border: 2px solid {sim_p_style['border']}; border-radius: 10px; padding: 20px; text-align: center; margin-top: 15px;">
            <div style="font-size: 0.85rem; font-weight: 700; color: #475569; text-transform: uppercase;">Score Resultante</div>
            <div style="font-size: 2.8rem; font-weight: 800; color: {sim_p_style['badge']}; margin: 4px 0;">{sim_score}</div>
            <div style="display: inline-block; padding: 4px 14px; border-radius: 12px; background-color: {sim_p_style['badge']}; color: white; font-weight: 700; font-size: 0.95rem;">
                Prioridade: {sim_prioridade}
            </div>
            <div style="margin-top: 14px; font-size: 0.85rem; color: #475569;">
                Fórmula: <b>{sim_impacto}</b> (Imp.) × <b>{sim_urgencia}</b> (Urg.) × (6 - <b>{sim_esforco}</b> Esf.) = <b>{sim_score}</b>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("""
        <div style="margin-top: 15px; font-size: 0.82rem; color: #64748B; background: #F8FAFC; padding: 12px; border-radius: 8px; border: 1px solid #E2E8F0;">
            💡 <b>Racional da Fórmula:</b><br>
            A multiplicação por <code>(6 - Esforço)</code> privilegia iniciativas de <b>baixo esforço (1)</b> com multiplicador <b>5</b>, garantindo que ganhos rápidos e eficientes fiquem no topo da lista.
        </div>
        """, unsafe_allow_html=True)

    with col_form:
        st.markdown("#### 📝 Dados da Iniciativa")
        with st.form("form_nova_tarefa"):
            current_areas_form = database.get_all_areas()
            f_col_id, f_col_lead = st.columns([1, 2])
            with f_col_id:
                new_id = st.text_input("ID da Tarefa", value=next_suggested_id)
            with f_col_lead:
                new_area_lider = st.selectbox("Área Líder *", options=current_areas_form)
                
            f_col_imp, f_col_interf = st.columns(2)
            with f_col_imp:
                new_areas_impactadas = st.multiselect(
                    "Área(s) Impactada(s) *",
                    options=current_areas_form,
                    placeholder="Selecione as áreas impactadas..."
                )
                new_impactada_custom = st.text_input("Outra área impactada (opcional)", placeholder="Ex: Fornecedores, Parceiros...")
            with f_col_interf:
                new_tipo_interf = st.selectbox("Tipo de Interferência", options=INTERFERENCIA_LIST)

            new_problema = st.text_area("Descrição do Problema *", placeholder="Explique a dor, impacto atual ou gargalo operacional...", height=90)
            new_solucao = st.text_area("Prévia da Solução *", placeholder="Qual a solução recomendada ou plano de ação?", height=80)
            
            f_col_stat, f_col_resp = st.columns(2)
            with f_col_stat:
                new_status = st.selectbox("Status Inicial", options=STATUS_LIST, index=0)
            with f_col_resp:
                new_responsavel = st.text_input("Responsável", placeholder="Nome da pessoa responsável")

            f_col_ini, f_col_prz = st.columns(2)
            with f_col_ini:
                new_inicio = st.date_input("Data de Início", value=None)
            with f_col_prz:
                new_prazo = st.date_input("Prazo Final", value=None)

            new_meta = st.text_input("Meta / KPI Esperado", placeholder="Ex: Reduzir tempo de faturamento em 50%")
            new_proxima_acao = st.text_input("Próxima Ação Imediata", placeholder="Ex: Realizar alinhamento com setor de tecnologia")

            btn_criar = st.form_submit_button("🚀 Criar Iniciativa no Kanban", use_container_width=True, type="primary")

            if btn_criar:
                if not new_problema.strip():
                    st.error("Por favor, preencha a descrição do problema.")
                else:
                    new_task_payload = {
                        "id": new_id.strip(),
                        "area_lider": new_area_lider,
                                                "area_impactada": ", ".join(list(new_areas_impactadas) + ([new_impactada_custom.strip()] if new_impactada_custom.strip() and new_impactada_custom.strip() not in new_areas_impactadas else [])), 
                        "descricao_problema": new_problema.strip(),
                        "previa_solucao": new_solucao.strip(),
                        "tipo_interferencia": new_tipo_interf,
                        "impacto": sim_impacto,
                        "urgencia": sim_urgencia,
                        "esforco": sim_esforco,
                        "status": new_status,
                        "responsavel": new_responsavel.strip(),
                        "data_inicio": new_inicio.strftime("%Y-%m-%d") if new_inicio else None,
                        "prazo": new_prazo.strftime("%Y-%m-%d") if new_prazo else None,
                        "meta": new_meta.strip(),
                        "proxima_acao": new_proxima_acao.strip()
                    }
                    created_id = database.add_task(new_task_payload)
                    st.success(f"Iniciativa **{created_id}** cadastrada com sucesso!")
                    st.rerun()


with tab_dashboard:
    st.markdown("### 📊 Painel Executivo & Métricas Estratégicas")
    st.caption("Visão analítica espelhando a aba 'Painel Executivo' da planilha com gráficos interativos.")
    
    if df_tasks.empty:
        st.info("Nenhuma tarefa cadastrada para exibir nos gráficos.")
    else:
        d_col1, d_col2 = st.columns(2)
        
        with d_col1:
            st.markdown("##### 📌 Distribuição por Status")
            status_counts = df_tasks["status"].value_counts().reset_index()
            status_counts.columns = ["Status", "Quantidade"]
            
            chart_status = alt.Chart(status_counts).mark_bar(cornerRadius=6).encode(
                x=alt.X("Quantidade:Q", title="Qtd. Iniciativas"),
                y=alt.Y("Status:N", sort=STATUS_LIST, title=""),
                color=alt.Color("Status:N", scale=alt.Scale(
                    domain=list(STATUS_COLORS.keys()),
                    range=list(STATUS_COLORS.values())
                ), legend=None),
                tooltip=["Status", "Quantidade"]
            ).properties(height=260)
            st.altair_chart(chart_status, use_container_width=True)

        with d_col2:
            st.markdown("##### 🎯 Distribuição por Nível de Prioridade")
            pri_counts = df_tasks["prioridade"].value_counts().reset_index()
            pri_counts.columns = ["Prioridade", "Quantidade"]
            
            pri_color_map = {
                "Crítico": "#E74C3C",
                "Alto": "#E67E22",
                "Médio": "#F1C40F",
                "Baixo": "#3498DB"
            }
            
            chart_pri = alt.Chart(pri_counts).mark_bar(cornerRadius=6).encode(
                x=alt.X("Quantidade:Q", title="Qtd. Iniciativas"),
                y=alt.Y("Prioridade:N", sort=PRIORIDADE_LIST, title=""),
                color=alt.Color("Prioridade:N", scale=alt.Scale(
                    domain=list(pri_color_map.keys()),
                    range=list(pri_color_map.values())
                ), legend=None),
                tooltip=["Prioridade", "Quantidade"]
            ).properties(height=260)
            st.altair_chart(chart_pri, use_container_width=True)

        d_col3, d_col4 = st.columns(2)
        
        with d_col3:
            st.markdown("##### 🏢 Iniciativas por Área Líder")
            area_counts = df_tasks["area_lider"].value_counts().reset_index()
            area_counts.columns = ["Área", "Quantidade"]
            
            chart_area = alt.Chart(area_counts).mark_bar(cornerRadius=6, color="#0D9488").encode(
                x=alt.X("Quantidade:Q", title="Qtd. Iniciativas"),
                y=alt.Y("Área:N", sort="-x", title=""),
                tooltip=["Área", "Quantidade"]
            ).properties(height=260)
            st.altair_chart(chart_area, use_container_width=True)

        with d_col4:
            st.markdown("##### 🚦 Farol de Prazos (SLA)")
            farol_counts = df_tasks["farol"].value_counts().reset_index()
            farol_counts.columns = ["Farol", "Quantidade"]
            
            farol_map = {
                "Verde": "#27AE60",
                "Amarelo": "#F39C12",
                "Vermelho": "#E74C3C",
                "Cinza": "#95A5A6"
            }
            
            chart_farol = alt.Chart(farol_counts).mark_bar(cornerRadius=6).encode(
                x=alt.X("Quantidade:Q", title="Qtd. Iniciativas"),
                y=alt.Y("Farol:N", sort=["Vermelho", "Amarelo", "Cinza", "Verde"], title=""),
                color=alt.Color("Farol:N", scale=alt.Scale(
                    domain=list(farol_map.keys()),
                    range=list(farol_map.values())
                ), legend=None),
                tooltip=["Farol", "Quantidade"]
            ).properties(height=260)
            st.altair_chart(chart_farol, use_container_width=True)

        st.markdown("##### ⚖️ Matriz de Priorização: Impacto vs Esforço (Tamanho da Bolha = Score)")
        chart_scatter = alt.Chart(df_tasks).mark_circle().encode(
            x=alt.X("esforco:Q", title="Esforço (1 = Menor, 5 = Maior)", scale=alt.Scale(domain=[0.5, 5.5])),
            y=alt.Y("impacto:Q", title="Impacto (1 = Menor, 5 = Maior)", scale=alt.Scale(domain=[0.5, 5.5])),
            size=alt.Size("score:Q", title="Score", scale=alt.Scale(range=[150, 900])),
            color=alt.Color("prioridade:N", scale=alt.Scale(
                domain=list(pri_color_map.keys()),
                range=list(pri_color_map.values())
            ), title="Prioridade"),
            tooltip=["id", "area_lider", "descricao_problema", "score", "prioridade", "status"]
        ).properties(height=350)
        st.altair_chart(chart_scatter, use_container_width=True)


with tab_tabela:
    st.markdown("### 📑 Visão Detalhada em Tabela")
    st.caption("Consulte todas as iniciativas cadastradas, ordene colunas e faça download dos dados.")
    
    if df_tasks.empty:
        st.info("Nenhuma iniciativa encontrada com os filtros selecionados.")
    else:
        display_df = df_tasks[[
            "id", "score", "prioridade", "status", "farol", "area_lider",
            "tipo_interferencia", "impacto", "urgencia", "esforco",
            "responsavel", "prazo", "descricao_problema", "previa_solucao"
        ]].copy()
        
        display_df.columns = [
            "ID", "Score", "Prioridade", "Status", "Farol", "Área Líder",
            "Interferência", "Imp.", "Urg.", "Esf.",
            "Responsável", "Prazo", "Problema", "Solução"
        ]
        
        st.dataframe(
            display_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Score": st.column_config.ProgressColumn(
                    "Score",
                    help="Fórmula: Impacto * Urgência * (6 - Esforço)",
                    format="%d",
                    min_value=0,
                    max_value=125,
                ),
                "Farol": st.column_config.TextColumn(
                    "Farol",
                    help="Verde = No Prazo / Amarelo = Próximo / Vermelho = Vencido / Cinza = Sem prazo"
                )
            }
        )
        
        st.divider()
        col_exp1, col_exp2, _ = st.columns([1, 1, 2])
        
        csv_data = df_tasks.to_csv(index=False).encode('utf-8')
        col_exp1.download_button(
            label="📥 Baixar Dados (CSV)",
            data=csv_data,
            file_name=f"iniciativas_kanban_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
            use_container_width=True
        )
        
        excel_buffer = io.BytesIO()
        with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
            df_tasks.to_excel(writer, index=False, sheet_name="Plano Estratégico")
        col_exp2.download_button(
            label="📊 Baixar Excel (.xlsx)",
            data=excel_buffer.getvalue(),
            file_name=f"iniciativas_kanban_{datetime.now().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )


with tab_areas:
    st.markdown("### 🏢 Gestão de Categorias de Áreas")
    st.caption("Cadastre novas áreas, edite ou remova categorias existentes. As alterações são refletidas nos campos de **Área Líder** e **Áreas Impactadas**.")
    
    cat_areas = database.get_all_areas()
    cat_stats = database.get_area_stats()
    
    col_kpi1, col_kpi2 = st.columns([1, 3])
    with col_kpi1:
        st.metric("Total de Áreas Cadastradas", len(cat_areas))
    with col_kpi2:
        st.info("💡 As áreas cadastradas aqui alimentam automaticamente as listas de seleção para novos cadastros e filtros do sistema.")

    col_add_area, col_edit_area = st.columns(2)
    
    with col_add_area:
        st.markdown("#### ➕ Adicionar Nova Área")
        with st.form("form_add_nova_area"):
            nome_nova = st.text_input("Nome da Nova Área *", placeholder="Ex: Recursos Humanos, Jurídico, Comercial...")
            btn_add = st.form_submit_button("Salvar Nova Área", type="primary", use_container_width=True)
            if btn_add:
                clean_n = nome_nova.strip()
                if not clean_n:
                    st.error("Por favor, digite o nome da área.")
                elif clean_n.lower() in [a.lower() for a in cat_areas]:
                    st.warning(f"A área '{clean_n}' já está cadastrada.")
                else:
                    database.add_area(clean_n)
                    st.success(f"Área '{clean_n}' adicionada com sucesso!")
                    st.rerun()

    with col_edit_area:
        st.markdown("#### ✏️ Renomear Área Existente")
        with st.form("form_rename_area"):
            area_selecionada = st.selectbox("Selecione a Área", options=cat_areas)
            novo_nome_area = st.text_input("Novo Nome da Área *", value=area_selecionada if area_selecionada else "")
            atualizar_tarefas = st.checkbox("Atualizar iniciativas existentes vinculadas a esta área", value=True)
            btn_rename = st.form_submit_button("Renomear Área", use_container_width=True)
            if btn_rename:
                clean_new = novo_nome_area.strip()
                if not clean_new:
                    st.error("Por favor, digite o novo nome.")
                elif clean_new == area_selecionada:
                    st.info("O novo nome é idêntico ao atual.")
                else:
                    database.update_area(area_selecionada, clean_new, update_tasks=atualizar_tarefas)
                    st.success(f"Área '{area_selecionada}' atualizada para '{clean_new}'!")
                    st.rerun()

    st.divider()
    st.markdown("#### 📋 Áreas Cadastradas e Vínculos")
    
    # Cabeçalho da lista
    h_col1, h_col2, h_col3, h_col4 = st.columns([3, 2, 2, 2])
    h_col1.markdown("**Nome da Área**")
    h_col2.markdown("**Como Área Líder**")
    h_col3.markdown("**Como Área Impactada**")
    h_col4.markdown("**Ação**")
    st.markdown("<hr style='margin: 4px 0 12px 0;'>", unsafe_allow_html=True)

    for stat in cat_stats:
        a_nome = stat["nome"]
        q_lider = stat["qtd_lider"]
        q_impactada = stat["qtd_impactada"]
        
        c1, c2, c3, c4 = st.columns([3, 2, 2, 2])
        c1.markdown(f"🏷️ **{a_nome}**")
        c2.markdown(f"{q_lider} iniciativa(s)")
        c3.markdown(f"{q_impactada} iniciativa(s)")
        
        if c4.button("🗑️ Remover", key=f"btn_del_cat_{a_nome}", use_container_width=True):
            database.remove_area(a_nome)
            st.toast(f"Área '{a_nome}' removida das categorias.", icon="🗑️")
            st.rerun()
            
        st.markdown("<hr style='margin: 4px 0 8px 0; border: none; border-top: 1px dashed #E2E8F0;'>", unsafe_allow_html=True)


with tab_metodologia:
    st.markdown("### 📖 Metodologia & Regras Extraídas da Planilha")
    
    st.markdown("""
    #### 1. Fórmula de Priorização
    O sistema adota estritamente a fórmula configurada na planilha original:
    """)
    st.latex(r"\text{Score} = \text{Impacto} \times \text{Urgência} \times (6 - \text{Esforço})")
    
    m_col1, m_col2 = st.columns(2)
    
    with m_col1:
        st.markdown("""
        ##### 📏 Escalas (1 a 5):
        * **Impacto (1 a 5):** Quanto a iniciativa ajuda o negócio e gera retorno.
        * **Urgência (1 a 5):** Quão rápido precisa ser resolvida para mitigar riscos ou perdas.
        * **Esforço (1 a 5):** Quanto recurso, equipe e tempo ela consome.
        
        > **Racional do Inversor (6 - Esforço):**  
        > * Esforço baixo (1): Multiplicador máximo (5), aumentando expressivamente o score.  
        > * Esforço alto (5): Multiplicador mínimo (1), reduzindo o score.  
        > Isso evita que iniciativas extremamente trabalhosas travem a fila de prioridades na frente de itens mais rápidos e eficientes.
        """)

    with m_col2:
        st.markdown("""
        ##### 🎯 Limites de Prioridade:
        | Prioridade | Limite Mínimo de Score | Descrição Operacional |
        | :--- | :---: | :--- |
        | 🔴 **Crítico** | **≥ 80** | Alta combinação de impacto e urgência com menor esforço |
        | 🟠 **Alto** | **≥ 45** | Deve entrar no ciclo prioritário de execução |
        | 🟡 **Médio** | **≥ 20** | Planejar após os itens críticos e altos |
        | 🔵 **Baixo** | **< 20** | Manter no backlog e revisar periodicamente |
        """)

    st.divider()
    
    st.markdown("""
    #### 2. Regra do Farol de Prazos (SLA)
    * 🟢 **Verde:** Tarefa com status **Concluído** OU Prazo com mais de 7 dias de antecedência.
    * 🟡 **Amarelo:** Prazo vence nos próximos 7 dias (atenção requerida).
    * 🔴 **Vermelho:** Prazo vencido (`Prazo < Hoje`) e status não concluído.
    * ⚪ **Cinza:** Iniciativa sem prazo definido.
    """)

    st.divider()
    st.markdown("#### 🔄 Sincronização & Banco DuckDB")
    st.caption("O banco local `kanban.duckdb` persiste todas as alterações de forma segura e autônoma.")
    
    if st.button("⚠️ Restaurar Dados Originais da Planilha Excel", help="Substitui os dados do DuckDB pelos dados contidos em 'Planilha de controle - Planejamento.xlsx'"):
        reseeded = database.import_from_excel("Planilha de controle - Planejamento.xlsx", overwrite=True)
        st.success(f"{reseeded} iniciativa(s) recarregadas da planilha original!")
        st.rerun()
