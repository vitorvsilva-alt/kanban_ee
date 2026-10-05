# 📋 Sistema Kanban de Planejamento Estratégico Cross-Áreas

Sistema interativo de gestão ágil (Kanban) construído com **Streamlit** e banco de dados relacional local de alta performance **DuckDB**, desenvolvido a partir da análise da planilha `Planilha de controle - Planejamento.xlsx`.

---

## 🎯 Principais Funcionalidades

1. **Quadro Kanban Interativo (6 Raias / Status):**
   - **Não iniciado** | **Em análise** | **Planejado** | **Em andamento** | **Bloqueado** | **Concluído**
   - **Ordenação Automática por Score:** As iniciativas com maior pontuação aparecem no topo de cada coluna.
   - **Cartões Inteligentes:** Exibem ID (`P.E-001`), Score, badge de Prioridade com código de cores, Área Líder, Tipo de Interferência, Responsável, Prazo e Farol de SLA.
   - **Ações Rápidas em 1 Clique:**
     - `✅ Concluir`: Finaliza a tarefa instantaneamente e marca o Farol como Verde.
     - `➡️ Avançar` / `⬅️ Voltar`: Transiciona o status no fluxo de trabalho.
     - `🔍 Ver / Editar`: Abre modal com visão completa e formulário de edição.
     - Mover direto para qualquer raia via menu rápido.

2. **Cálculo de Score e Priorização em Tempo Real:**
   - Adota a fórmula exata configurada na planilha original:
     Score = Impacto * Urgência * (6 - Esforço)
   - **Classificação Automática de Prioridade:**
     - 🔴 **Crítico:** Score >= 80 (Alta combinação de impacto e urgência com menor esforço)
     - 🟠 **Alto:** Score >= 45 (Ciclo prioritário de execução)
     - 🟡 **Médio:** Score >= 20 (Planejar após os itens críticos e altos)
     - 🔵 **Baixo:** Score < 20 (Backlog e revisão periódica)
   - **Simulador Interativo:** Na tela de cadastro, sliders ajustam o Score e a Prioridade dinamicamente antes de salvar.

3. **Farol de Prazos (SLA Dinâmico):**
   - 🟢 **Verde:** Tarefa com status *Concluído* ou com prazo com mais de 7 dias de antecedência.
   - 🟡 **Amarelo:** Prazo nos próximos 7 dias (atenção requerida).
   - 🔴 **Vermelho:** Prazo vencido (Prazo < Hoje) e status não concluído.
   - ⚪ **Cinza:** Iniciativa sem prazo definido.

4. **Banco de Dados Local DuckDB:**
   - Persistência no arquivo `kanban.duckdb`.
   - **Carga Automática:** Na primeira execução, o sistema lê automaticamente os dados existentes na aba *Plano Estratégico* do arquivo Excel e popula o DuckDB.
   - Operações completas de CRUD (Criar, Consultar, Modificar, Excluir).

5. **Painel Executivo & Métricas Estratégicas:**
   - KPIs: Total de Iniciativas, Em Aberto (% do total), Prioridade Crítica e Prazos em Risco.
   - Resumo Executivo em texto narrativo sincronizado com os dados.
   - Gráficos Interativos (Altair):
     - Distribuição por Status
     - Distribuição por Prioridade
     - Distribuição por Área Líder
     - Distribuição do Farol de Prazos
     - Matriz de Priorização (Impacto vs. Esforço com tamanho da bolha proporcional ao Score)

6. **Tabela Geral e Exportação:**
   - Visualização tabular completa com pesquisa e filtros.
   - Download dos dados atualizados em formato **Excel (.xlsx)** ou **CSV** a qualquer momento.

---

## 🚀 Como Executar o Sistema

### 1. Iniciar o Servidor Streamlit
Na pasta do projeto, execute:
```powershell
python -m streamlit run app.py
```

O sistema abrirá automaticamente no seu navegador padrão no endereço:
👉 **`http://localhost:8501`**
