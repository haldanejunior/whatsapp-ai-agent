# 🏗️ Agente Aluga Fácil | Assistente Virtual com IA Local

Um agente virtual inteligente desenvolvido em Python para automatizar o atendimento de locação de equipamentos para construção civil. Operando com modelos de inteligência artificial executados localmente (Ollama), o sistema garante privacidade total dos dados e ausência de custos com APIs externas para inferência[cite: 5]. O assistente interage de forma natural, gerenciando todo o ciclo de vida do aluguel diretamente pelo terminal, possuindo uma arquitetura modular preparada para integração com plataformas de mensagens.

## 🚀 Funcionalidades Principais

*   **Conversação Contextual:** Compreende intenções e extrai entidades (nome do cliente, equipamento, quantidade, período) utilizando o modelo `qwen3:1.7b` integrado ao fluxo de chamadas de ferramentas (Tool Calling)[cite: 5].
*   **Consulta de Estoque e Preços:** Verifica dinamicamente a disponibilidade de itens cadastrados e informa os valores exatos das diárias, impedindo que a IA invente informações[cite: 5, 7].
*   **Geração de Orçamentos:** Calcula valores totais de forma determinística com base na diária do produto, alertando o usuário caso a quantidade solicitada exceda o estoque disponível no momento[cite: 7].
*   **Gestão de Locações:** Registra novos clientes a partir do telefone, cria registros de locação com status "ativa" e deduz os equipamentos do inventário utilizando transações seguras no banco de dados[cite: 7].
*   **Devoluções e Finalizações:** Permite que o cliente encerre contratos, atualizando o status da locação para "finalizada" e retornando automaticamente as unidades ao estoque[cite: 7].
*   **Isolamento de Sessão:** Mantém o histórico, o estado da negociação (ex: aguardando confirmação) e o contexto da conversa isolados para cada número de telefone[cite: 5].

## 🛠️ Tecnologias Utilizadas

*   **Python:** Lógica central, expressões regulares para sanitização de dados e gerenciamento de estado das sessões[cite: 5, 7].
*   **Ollama:** Motor de inferência local para execução offline de modelos de linguagem (LLMs)[cite: 5].
*   **SQLite:** Banco de dados relacional leve (armazenado no arquivo local `dados.db`[cite: 4]) para persistência das tabelas de produtos, clientes e locações[cite: 3].
*   **python-dotenv:** Gestão de variáveis de ambiente para manutenção segura de chaves e configurações[cite: 8].

## ⚙️ Estrutura do Projeto

*   `main.py`: Ponto de entrada da aplicação, contendo o loop principal de interação, prompts de sistema e o pipeline de comunicação com o Ollama[cite: 5].
*   `banco.py`: Inicialização do banco de dados, definição das tabelas e injeção do catálogo inicial de equipamentos (como betoneiras e marteletes)[cite: 3].
*   `tools.py`: Implementação robusta das ferramentas consumidas pela IA, com validação de tipos, normalização de strings e consultas SQL parametrizadas[cite: 7].
*   `teste_locacao.py`: Script auxiliar para verificação isolada de operações de leitura e atualização no banco[cite: 6].

## 🏃‍♂️ Como Executar Localmente

1. Certifique-se de ter o [Ollama](https://ollama.com/) instalado e o modelo ativo em sua máquina (rodando `ollama run qwen3:1.7b`).
2. Clone este repositório e acesse a pasta raiz.
3. (Opcional) Crie e ative um ambiente virtual (`.venv`).
4. Execute o script principal:
   ```bash
   python main.py
   ```
5. Digite um número de telefone no terminal (com 10 a 13 dígitos) para iniciar a sessão e comece a testar o fluxo de atendimento[cite: 5].
