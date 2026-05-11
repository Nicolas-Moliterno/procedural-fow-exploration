# Procedural FOW Exploration

> **Análise Comparativa de Agentes em um Ambiente de Jogo com Exploração Procedural e Fog of War**

Um projeto de pesquisa em IA para Jogos que implementa e analisa três estratégias de inteligência artificial em um ambiente de jogo gerado proceduralmente, com sistema avançado de "Fog of War" (campo de visão limitado).

## 📋 Visão Geral

Este projeto explora como diferentes estratégias de IA se comportam em um ambiente de exploração dinâmico. O cenário envolve um jogador que precisa encontrar itens (uma espada e um cálice) em um mundo gerado proceduralmente, enfrentando inimigos e obstáculos, com visão limitada apenas às áreas próximas.

### Objetivo Principal
Comparar o desempenho de três agentes com estratégias distintas:
- **Random**: estratégia aleatória pura
- **BFS (Breadth-First Search)**: busca gulosa direta ao objetivo
- **Item Hunter**: busca sequencial (primeiro item → objetivo final)

## 🎮 Características do Ambiente

### Mundo Procedural
- **Tamanho**: 800×600 pixels em grid de células 12×12 (67×50 células)
- **Geração**: Perlin noise multi-octava para biomas realistas
- **Elementos**:
  - **Biomas**: Terreno com altura variável (água, terra, montanha)
  - **Cavernas**: Geradas via cellular automata
  - **Vegetação**: Árvores distribuídas proceduralmente
  - **Obstáculos**: Água, paredes de caverna, árvores

### Fog of War (FOW)
- **Raio de Visão**: 10 células do jogador
- **Dinâmico**: Áreas exploradas são lembradas, novas áreas são descobertas conforme o jogador se move
- **Desafiador**: O agente não tem mapa completo, deve explorar e planejar

### Mecânicas de Jogo
- **Objetivos**: Coletar Espada → Coletar Cálice (vitória)
- **Combate**: 5 inimigos ativos no mapa
- **Recurso**: HP (começa em 100)
- **Transporte**: Barcos para cruzar água
- **Limite de Passos**: 2000 por partida

## 🤖 Estratégias dos Agentes

### 1. **Random**
```python
# Escolhe uma ação aleatória a cada passo
ação ∈ {UP, DOWN, LEFT, RIGHT, INTERACT, SKIP}
```
- **Baseline**: Sem inteligência
- **Esperado**: Baixa taxa de vitória
- **Uso**: Comparativo

### 2. **BFS (Breadth-First Search)**
```python
# Pathfinding guloso direto ao Cálice
while not tem_calice:
    proximo_passo = BFS(posição_atual → posição_cálice)
    mover_para(proximo_passo)
```
- **Inteligência**: Conhecimento de objetivo
- **Limitação**: Não otimizado para recolher espada primeiro
- **Esperado**: Taxa média de vitória

### 3. **Item Hunter**
```python
# Busca sequencial inteligente
if não_tem_espada:
    proximo_passo = BFS(posição_atual → posição_espada)
else:
    proximo_passo = BFS(posição_atual → posição_cálice)
```
- **Inteligência**: Entende dependência de itens
- **Estratégia**: Resolve pré-requisitos (espada → cálice)
- **Esperado**: Maior taxa de vitória

## 📁 Estrutura do Projeto

```
procedural-fow-exploration/
├── gameAutomatic.py          # Simulador do jogo (3 agentes)
├── GameAnalytics.py          # Coleta de dados de partidas
├── analytics.py              # Pipeline de análise e visualização
├── data/                      # Dados brutos do agente random
├── dataBFS/                  # Dados brutos do agente BFS
├── dataHunter/               # Dados brutos do agente item_hunter
├── analysis_output/          # Gráficos e relatórios gerados
├── IA_para_Jogos.pdf         # Documentação da disciplina
└── README.md                 # Este arquivo
```

## 🚀 Como Usar

### Requisitos
```bash
python >= 3.8
pip install pandas numpy matplotlib seaborn scikit-learn perlin-noise
```

### 1. Gerar Dados de Partidas

Simule cada agente independentemente:

```bash
# Agente Random (200 partidas)
python gameAutomatic.py --runs 200 --outdir data --agent random

# Agente BFS (200 partidas)
python gameAutomatic.py --runs 200 --outdir dataBFS --agent bfs

# Agente Item Hunter (200 partidas)
python gameAutomatic.py --runs 200 --outdir dataHunter --agent item_hunter
```

**Opções**:
- `--runs N`: Número de partidas a simular
- `--outdir PATH`: Diretório de saída para dados
- `--agent {random, bfs, item_hunter}`: Qual agente executar
- `--max_steps N`: Limite de passos por partida (padrão: 2000)

### 2. Analisar e Gerar Relatórios

```bash
python analytics.py --data_dir . --outdir analysis_output
```

Isso gera:
- **Resumos estatísticos** (CSV)
- **Gráficos comparativos** (PNG)
- **Análise de clusters** (estilos de jogo)
- **Feature importance** (quais features preveem vitória)
- **Heatmaps** de posições

**Opções**:
- `--data_dir PATH`: Diretório com subpastas (data/, dataBFS/, dataHunter/)
- `--outdir PATH`: Diretório de saída dos gráficos

## 📊 Resultados e Métricas

### Métricas por Agente
| Métrica | Random | BFS | Item Hunter |
|---------|--------|-----|-------------|
| **Win Rate** | 17% | 46% | 33% |
| **Avg Score** | ~300 | ~550 | ~400 |
| **Avg Steps** | ~1200 | ~150 | ~1100 |
| **Avg Kills** | 8.6 | 7.7 | 11.3 |

### Saídas Analíticas

#### 1. **Estatísticas por Agente** (`summary_by_agent.csv`)
```
agent,total_matches,win_rate,avg_steps,avg_score,avg_hp_final,avg_kills
random,200,0.17,1200,300,45,8.6
bfs,200,0.46,150,550,98,7.7
item_hunter,200,0.33,1100,400,65,11.3
```

#### 2. **Distribuição de Ações** (`action_distribution_*.csv`)
- Frequência de cada ação (UP, DOWN, LEFT, RIGHT, INTERACT, SKIP)
- Revela padrões comportamentais

#### 3. **Clustering de Estilo de Jogo** (PCA + K-Means)
- Agrupa partidas em clusters similares
- Revela padrões emergentes além da estratégia base

#### 4. **Feature Importance** (`feature_importances.csv`)
- Quais features do estado (itens, posição, inimigos) mais afetam vitória
- Modelo: RandomForestClassifier

#### 5. **Heatmaps de Posições**
- `Heatmap de Posições — player (global)`: Onde o jogador visitou
- `Heatmap de Posições — inimigos (global)`: Onde os inimigos aparecem
- Revela estratégias de exploração

### Gráficos Gerados

1. **win_rate_by_agent.png** - Taxa de vitória de cada agente
2. **score_distribution.png** - Distribuição de scores (boxplot)
3. **steps_distribution.png** - Número de passos por partida
4. **kills_by_agent.png** - Inimigos eliminados por agente
5. **hp_final_by_agent.png** - HP final (violino)
6. **action_distribution_*.png** - Frequência de ações por agente
7. **clusters_by_agent.png** - Estilos de jogo (PCA)
8. **feature_importances_*.png** - Importância de features para vitória
9. **heatmap_positions_*.png** - Mapa de calor de posições visitadas

## 📖 Arquivos Principais

### `gameAutomatic.py`
Simulador do jogo com 3 agentes integrados.

**Fluxo**:
1. Gera mundo procedural (biomas, cavernas, itens, inimigos)
2. Posiciona jogador aleatoriamente
3. Executa loop de jogo por até 2000 passos
4. Coleta dados via `GameAnalytics`
5. Salva em CSV

**Funções-chave**:
- `generate_world()` - Cria mapa procedural
- `update_fog()` - Atualiza visibilidade
- `get_next_step(start, target)` - BFS pathfinding
- `step_agent()` - Lógica de decisão do agente
- `run_match()` - Loop principal

### `GameAnalytics.py`
Classe para coleta estruturada de dados.

**O que coleta**:
- **Matches**: Resumo de vitória, score, passos, HP, kills
- **Events**: Eventos importantes (item coletado, inimigo matado, etc)
- **Positions**: Localização de entidades a cada passo
- **Actions**: Ação tomada a cada passo

**Saída**: 4 CSVs por partida/agente

### `analytics.py`
Pipeline completo de análise e visualização.

**Etapas**:
1. Carrega dados de todas as partidas (3 agentes)
2. Calcula estatísticas agregadas
3. Gera gráficos comparativos
4. Executa clustering (PCA + K-Means)
5. Treina RandomForest para feature importance
6. Gera heatmaps de posições
7. Salva tudo em `analysis_output/`

## 🔍 Exemplos de Análise

### Comparar Win Rate
```python
import pandas as pd

matches = pd.read_csv("analysis_output/summary_by_agent.csv")
print(matches[["agent", "win_rate"]])

# Output:
#       agent  win_rate
# 0    random     0.17
# 1       bfs     0.46
# 2 item_hunter     0.33
```

### Analisar Feature Importance
```python
import pandas as pd

features = pd.read_csv("analysis_output/feature_importances.csv")
print(features.nlargest(3, "importance"))
```

### Visualizar Padrões de Movimento
```bash
# Abrir heatmaps para cada agente
# Compara estratégia de exploração
open analysis_output/heatmap_positions_*.png
```

## 🧪 Experimentos Futuros

Possíveis extensões:
1. **Agentes com Aprendizado**: Q-Learning, Policy Gradient
2. **Visibilidade Dinâmica**: FOW mais realista (line-of-sight)
3. **Cooperação**: Múltiplos agentes colaborando
4. **Inimigos Inteligentes**: Pathfinding para NPCs
5. **Equilíbrio**: Ajustar dificuldade dinamicamente
6. **Gráficos**: Renderização visual do jogo

## 📚 Referências e Contexto

- **Disciplina**: IA para Jogos (UNICAMP)
- **Tópicos**: Pathfinding, Procedural Generation, Fog of War, Agent Design
- **Algoritmos**: BFS, Perlin Noise, Cellular Automata, Random Forest, K-Means

## 📝 Notas Implementação

### Validações do FOW
- Visibilidade é circular com raio 10
- Áreas exploradas são persistentes
- O agente não vê além de seu raio mesmo se já explorou

### Restrições de Movimento
- Água é intransitável (a menos que em barco)
- Árvores bloqueiam movimento
- Paredes de caverna bloqueiam
- Barcos permitem cruzar água

### Scoring
- Base: Score do jogo
- HP restante: +HP_final ao score
- Kills: +pontos por inimigo
- Vitória: Bônus se derrotar o boss final

## 🤝 Contribuições

Este é um projeto educacional. Sinta-se livre para:
- Adicionar novos agentes
- Melhorar a geração procedural
- Implementar novas métricas de análise
- Otimizar pathfinding

## 📄 Licença

Projeto educacional - UNICAMP

---

**Autor**: Estudante de IA para Jogos  
**Data**: 2025-2026  
**Última Atualização**: Maio de 2026
