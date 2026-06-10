[中文](README.zh-CN.md) | [English](README.md) | [日本語](README.ja.md) | [한국어](README.ko.md) | [Español](README.es.md) | Português | [Français](README.fr.md)

<p align="center">
  <img src="assets/logo.svg" width="128" height="128" alt="WeeklyViz Logo">
</p>

<h1 align="center">WeeklyViz</h1>

<p align="center">
  <strong>Gerador Profissional de Relatórios Semanais HTML Offline e Skill de Agente</strong>
</p>

<p align="center">
  <a href=""><img src="https://img.shields.io/badge/version-0.1.1-blue.svg" alt="Version"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-green.svg" alt="License"></a>
  <a href=""><img src="https://img.shields.io/badge/platform-Codex_/_Claude_Code-purple.svg" alt="Platform"></a>
</p>

<p align="center">
  Converta atualizações de texto, planilhas e documentos em <strong>relatórios semanais HTML offline profissionais, responsivos, editáveis e com rastreabilidade de origem</strong>, gerados automaticamente pelo seu Agente de IA.
</p>

É uma Claude Skill e ferramenta independente construída sob a especificação [Agent Skills](https://agentskills.io). Foi projetada para funcionar perfeitamente com Agentes de IA (como Claude Code, Cursor ou Codex). Em vez de executar scripts Python ou codificar você mesmo, basta instalar a skill e deixar que o seu Agente de IA faça todo o trabalho pesado.

---

## 🖼️ Exemplo de Resultado

<p align="center">
  <a href="assets/red-shiji-weekly-report.jpg">
    <img src="assets/red-shiji-weekly-report.jpg" width="860" alt="Exemplo de relatório semanal editorial gerado pelo WeeklyViz">
  </a>
</p>

<p align="center"><sub>Um relatório editorial completo gerado com o WeeklyViz: resumo executivo, cartões de KPI, progresso de metas, visualizações, atualizações de projetos, riscos e próximas ações. Clique na imagem para vê-la na resolução original.</sub></p>

---

## ✨ Recursos Principais

| Recurso | Descrição |
|---------|-----------|
| 📊 **Extração de Várias Fontes** | Processa arquivos `.xlsx`, `.csv`, `.docx`, `.md` e `.txt` automaticamente para extrair métricas e listas de progresso. |
| 🎨 **Design Editorial Responsivo** | Oferece três temas embutidos (`Executive`, `Editorial`, `Product Operations`) com layouts responsivos e sem requisições de rede externas. |
| 🔗 **Rastreabilidade de Origem** | Mapeia automaticamente cada KPI, barra de progresso, gráfico e item de volta ao arquivo e linha originais usando IDs hash estáveis. |
| ✏️ **Edição Inline Interativa** | O relatório HTML final suporta edição de textos e números em tempo real, ajustes de tema e exportação simples para PDF/impressão. |
| 📈 **Apache ECharts Integrado** | Inclui runtime local do ECharts (`echarts.min.js`) para criar gráficos de linhas, barras, roscas e funis sem acesso à internet. |

---

## 🚀 Como Usar (Muito Simples)

### 1. Instalar a Skill
Adicione o WeeklyViz à pasta de habilidades do seu Agente de IA:

*   **Claude Code**: Clone este repositório dentro de `.claude/skills/weeklyviz` na raiz do seu projeto.
*   **Cursor**: Clone este repositório dentro de `.cursor/skills/weeklyviz` na raiz do seu projeto.
*   **Outros Agentes**: Coloque o repositório sob o caminho de instruções personalizadas do seu agente.

### 2. Apenas Peça ao seu Agente!
Você **não** precisa executar comandos Python nem escrever arquivos de configuração. Basta fornecer seus arquivos (planilhas, notas, textos copiados) ao seu Agente de IA e pedir:

> *"Ei Claude, use o WeeklyViz para gerar um relatório semanal a partir das minhas notas."*

O agente lerá automaticamente seus arquivos, extrairá os dados, validará os limites e compilará o relatório HTML final offline (`weekly-report.html`) para você de uma só vez.

---

## 🛠️ Detalhes do Desenvolvedor (Opcional)

Se você deseja executar o WeeklyViz manualmente via linha de comando:

```bash
# Extrair dados brutos para um pacote
python3 scripts/weeklyviz.py extract --input notes.md data.xlsx --output source-bundle.json

# Validar o esquema do modelo de relatório
python3 scripts/weeklyviz.py validate --report report-model.json

# Compilar em HTML offline autocontido
python3 scripts/weeklyviz.py render --report report-model.json --output weekly-report.html
```

---

## 📋 Versões de Lançamento

*   **v0.1.1** (2026-06-09)
    - Estrutura de diretórios aplanada na pasta raiz para instalação e execução padrão do agente.
    - Design e atualização premium do modelo `Editorial` com fundos pontilhados, barra de estilo macOS, sombras sólidas deslocadas, listas de tópicos e barras laterais.
    - Política de segurança para excluir dados locais sensíveis do Shiji no repositório público do GitHub.
*   **v0.1.0** (2026-06-09)
    - Lançamento inicial.
```

