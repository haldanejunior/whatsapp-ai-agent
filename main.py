import re
import json
import ollama

from banco import criar_tabelas, carregar_dados_iniciais

from tools import (
    consultar_estoque,
    consultar_preco,
    calcular_orcamento,
    registrar_locacao,
    consultar_locacao,
    consultar_locacoes_cliente,
    finalizar_locacao
)


# ==========================================
# CONFIGURAÇÕES
# ==========================================

MODELO = "qwen3:1.7b"

SYSTEM_PROMPT = """
Você é o assistente virtual da empresa Aluga Fácil.

A empresa trabalha com locação de equipamentos.

REGRAS:

- Responda sempre em português brasileiro.
- Seja educado, objetivo e profissional.
- Dê respostas relativamente curtas.

PREÇO E ESTOQUE:

- Nunca invente preços.
- Nunca invente estoque.
- Para consultar preço, use consultar_preco.
- Para consultar estoque, use consultar_estoque.
- Para orçamento, use calcular_orcamento.
- Nunca faça cálculos por conta própria.

LOCAÇÕES:

- Para consultar uma locação pelo número,
  use consultar_locacao.

- Para listar locações de um cliente pelo telefone,
  use consultar_locacoes_cliente.

- Se o cliente disser que deseja devolver,
  finalizar ou encerrar uma locação,
  use finalizar_locacao.

- Se o cliente quiser finalizar uma locação
  mas não informar o número da locação,
  pergunte qual é o número.

- Nunca diga que uma locação foi finalizada
  sem finalizar_locacao retornar sucesso=True.

- Se o cliente demonstrar intenção de criar
  uma nova locação, esse fluxo será controlado
  pelo sistema Python.
"""


# ==========================================
# SESSÕES POR TELEFONE
# ==========================================

# Cada número de telefone terá sua própria sessão.
sessoes = {}


def normalizar_telefone(telefone):
    """Mantém somente os números do telefone."""
    return re.sub(r"\D", "", str(telefone))


def criar_sessao(telefone):
    telefone = normalizar_telefone(telefone)

    return {
        "telefone": telefone,

        "historico": [
            {
                "role": "system",
                "content": SYSTEM_PROMPT
            }
        ],

        "estado": "normal",
        "orcamento_atual": None,

        "dados_locacao": {
            "nome_cliente": None,
            "telefone": telefone,
            "equipamento": None,
            "quantidade": None,
            "dias": None
        }
    }


def obter_sessao(telefone):
    telefone = normalizar_telefone(telefone)

    if not telefone:
        raise ValueError("O telefone não pode estar vazio.")

    if not 10 <= len(telefone) <= 13:
        raise ValueError(
            "Informe um telefone com 10 a 13 dígitos, "
            "incluindo o código do país, se houver."
        )

    if telefone not in sessoes:
        sessoes[telefone] = criar_sessao(telefone)

    return sessoes[telefone]


# ==========================================
# INICIALIZA BANCO
# ==========================================

criar_tabelas()
carregar_dados_iniciais()


# ==========================================
# NÚMEROS POR EXTENSO
# ==========================================

NUMEROS = {
    "um": 1,
    "uma": 1,
    "dois": 2,
    "duas": 2,
    "três": 3,
    "tres": 3,
    "quatro": 4,
    "cinco": 5,
    "seis": 6,
    "sete": 7,
    "oito": 8,
    "nove": 9,
    "dez": 10
}


def converter_numero(valor):
    if valor is None:
        return None

    valor = str(valor).lower().strip()

    if valor.isdigit():
        return int(valor)

    return NUMEROS.get(valor)


# ==========================================
# LIMPA DADOS DA LOCAÇÃO DA SESSÃO
# ==========================================

def limpar_locacao(sessao):
    telefone = sessao["telefone"]

    sessao["dados_locacao"] = {
        "nome_cliente": None,
        "telefone": telefone,
        "equipamento": None,
        "quantidade": None,
        "dias": None
    }

    sessao["orcamento_atual"] = None
    sessao["estado"] = "normal"


# ==========================================
# CAMPOS FALTANTES
# ==========================================

def campos_faltantes(sessao):
    dados_locacao = sessao["dados_locacao"]
    faltando = []

    # O telefone já é conhecido, pois identifica a sessão.
    if not dados_locacao["nome_cliente"]:
        faltando.append("nome")

    if not dados_locacao["equipamento"]:
        faltando.append("equipamento")

    if dados_locacao["quantidade"] is None:
        faltando.append("quantidade")

    if dados_locacao["dias"] is None:
        faltando.append("dias")

    return faltando


# ==========================================
# DETECTA INTENÇÃO DE LOCAÇÃO
# ==========================================

def quer_alugar(mensagem):
    texto = mensagem.lower()

    palavras = [
        "quero alugar",
        "quero locar",
        "quero reservar",
        "gostaria de alugar",
        "gostaria de locar",
        "vou alugar",
        "fechar locação",
        "fechar a locação",
        "fechar locacao",
        "fechar a locacao"
    ]

    return any(palavra in texto for palavra in palavras)


# ==========================================
# CONFIRMAÇÃO
# ==========================================

def resposta_positiva(mensagem):
    texto = mensagem.strip().lower()

    respostas = {
        "sim",
        "s",
        "confirmo",
        "confirmar",
        "pode",
        "pode sim",
        "quero",
        "fechado",
        "ok",
        "certo"
    }

    return texto in respostas


def resposta_negativa(mensagem):
    texto = mensagem.strip().lower()

    respostas = {
        "não",
        "nao",
        "n",
        "cancelar",
        "cancela",
        "não quero",
        "nao quero"
    }

    return texto in respostas


# ==========================================
# EXTRAI DADOS DA LOCAÇÃO
# ==========================================

def extrair_dados_locacao(mensagem, sessao):
    texto = mensagem.strip()
    texto_lower = texto.lower()

    dados = {
        "nome_cliente": None,
        "equipamento": None,
        "quantidade": None,
        "dias": None
    }

    # --------------------------------------
    # EQUIPAMENTO
    # --------------------------------------

    equipamentos = {
        "martelete": "martelete",
        "betoneira": "betoneira",
        "furadeira": "furadeira",
        "serra mármore": "serra mármore",
        "serra marmore": "serra mármore",
        "compactador": "compactador de solo"
    }

    for palavra, equipamento in equipamentos.items():
        if palavra in texto_lower:
            dados["equipamento"] = equipamento
            break

    # --------------------------------------
    # DIAS
    # --------------------------------------

    padrao_numero = (
        r"\d+|um|uma|dois|duas|três|tres|quatro|"
        r"cinco|seis|sete|oito|nove|dez"
    )

    padrao_dias = re.search(
        rf"\b({padrao_numero})\s+dias?\b",
        texto_lower
    )

    if padrao_dias:
        dados["dias"] = converter_numero(
            padrao_dias.group(1)
        )

    # --------------------------------------
    # QUANTIDADE
    # --------------------------------------

    padrao_quantidade = re.search(
        rf"\b({padrao_numero})\s+"
        r"(unidade|unidades|"
        r"martelete|marteletes|"
        r"betoneira|betoneiras|"
        r"furadeira|furadeiras|"
        r"compactador|compactadores)\b",
        texto_lower
    )

    if padrao_quantidade:
        dados["quantidade"] = converter_numero(
            padrao_quantidade.group(1)
        )

    # --------------------------------------
    # NOME EM FRASES COMO:
    # "meu nome é Haldane"
    # "sou Haldane"
    # --------------------------------------

    padrao_nome = re.search(
        r"(?:meu nome é|meu nome e|sou)\s+"
        r"([a-záàâãéèêíïóôõöúç ]+)",
        texto_lower,
        re.IGNORECASE
    )

    if padrao_nome:
        nome = padrao_nome.group(1).strip()
        dados["nome_cliente"] = nome.title()

    # --------------------------------------
    # NOME INFORMADO SOZINHO
    # Exemplo: "Haldane"
    # --------------------------------------

    else:
        candidato = re.sub(
            r"[^a-záàâãéèêíïóôõöúç ]",
            "",
            texto_lower
        ).strip()

        frases_que_nao_sao_nome = {
            "oi",
            "ola",
            "olá",
            "bom dia",
            "boa tarde",
            "boa noite",
            "quero",
            "quero alugar",
            "quero locar",
            "quero reservar"
        }

        palavras_de_locacao = [
            "alugar",
            "locar",
            "reservar",
            "locação",
            "locacao"
        ]

        tem_palavra_de_locacao = any(
            palavra in candidato
            for palavra in palavras_de_locacao
        )

        if (
            candidato
            and len(candidato.split()) <= 5
            and candidato not in frases_que_nao_sao_nome
            and not tem_palavra_de_locacao
            and dados["equipamento"] is None
            and dados["dias"] is None
            and dados["quantidade"] is None
            and sessao["dados_locacao"]["nome_cliente"] is None
        ):
            dados["nome_cliente"] = candidato.title()

    return dados


# ==========================================
# ATUALIZA DADOS DA SESSÃO
# ==========================================

def atualizar_estado(sessao, dados):
    dados_locacao = sessao["dados_locacao"]

    nome = dados.get("nome_cliente")
    equipamento = dados.get("equipamento")
    quantidade = dados.get("quantidade")
    dias = dados.get("dias")

    if nome:
        dados_locacao["nome_cliente"] = nome

    if equipamento:
        dados_locacao["equipamento"] = equipamento

    if quantidade is not None and quantidade > 0:
        dados_locacao["quantidade"] = quantidade

    if dias is not None and dias > 0:
        dados_locacao["dias"] = dias


# ==========================================
# TEXTO DOS CAMPOS FALTANTES
# ==========================================

def mensagem_campos_faltantes(faltando):
    nomes = {
        "nome": "seu nome",
        "equipamento": "qual equipamento deseja",
        "quantidade": "quantas unidades deseja",
        "dias": "por quantos dias deseja alugar"
    }

    itens = [nomes[campo] for campo in faltando]

    if len(itens) == 1:
        return f"Para continuar, informe {itens[0]}."

    if len(itens) == 2:
        texto = f"{itens[0]} e {itens[1]}"
    else:
        texto = ", ".join(itens[:-1]) + " e " + itens[-1]

    return (
        "Para continuar com a locação, preciso de "
        + texto
        + "."
    )


# ==========================================
# PROCESSA LOCAÇÃO DE UMA SESSÃO
# ==========================================

def processar_locacao(sessao, mensagem):
    dados_locacao = sessao["dados_locacao"]

    # --------------------------------------
    # AGUARDANDO CONFIRMAÇÃO
    # --------------------------------------

    if sessao["estado"] == "aguardando_confirmacao":

        if resposta_positiva(mensagem):
            resultado = registrar_locacao(
                nome_cliente=dados_locacao["nome_cliente"],
                telefone=dados_locacao["telefone"],
                equipamento=dados_locacao["equipamento"],
                quantidade=dados_locacao["quantidade"],
                dias=dados_locacao["dias"]
            )

            if resultado.get("sucesso"):
                print("\nAgente: Locação registrada com sucesso!")

                print(
                    f"Equipamento: {resultado['equipamento']}"
                )
                print(
                    f"Quantidade: {resultado['quantidade']}"
                )
                print(
                    f"Dias: {resultado['dias']}"
                )
                print(
                    f"Valor total: R$ {resultado['valor_total']:.2f}"
                )
                print(
                    f"Estoque restante: {resultado['estoque_restante']}"
                )
                print(
                    f"Número da locação: {resultado['locacao_id']}"
                )

                limpar_locacao(sessao)
                return

            print(
                "\nAgente:",
                resultado.get(
                    "mensagem",
                    "Não foi possível registrar a locação."
                )
            )
            return

        if resposta_negativa(mensagem):
            print(
                "\nAgente: Tudo bem. "
                "A locação não foi registrada."
            )

            limpar_locacao(sessao)
            return

        print(
            "\nAgente: Por favor, responda "
            "'sim' para confirmar ou 'não' para cancelar."
        )
        return

    # --------------------------------------
    # EXTRAI E ATUALIZA OS DADOS
    # --------------------------------------

    dados_extraidos = extrair_dados_locacao(
        mensagem,
        sessao
    )

    atualizar_estado(
        sessao,
        dados_extraidos
    )

    print(
        "\n[Estado da locação:",
        dados_locacao,
        "]"
    )

    faltando = campos_faltantes(sessao)

    print("[Dados faltantes:", faltando, "]")

    # --------------------------------------
    # AINDA FALTAM DADOS
    # --------------------------------------

    if faltando:
        print(
            "\nAgente:",
            mensagem_campos_faltantes(faltando)
        )
        return

    # --------------------------------------
    # CALCULA ORÇAMENTO
    # --------------------------------------

    resultado = calcular_orcamento(
        equipamento=dados_locacao["equipamento"],
        dias=dados_locacao["dias"],
        quantidade=dados_locacao["quantidade"]
    )

    if resultado.get("erro"):
        print("\nAgente:", resultado["mensagem"])
        return

    if resultado.get("encontrado") is False:
        print("\nAgente:", resultado["mensagem"])
        dados_locacao["equipamento"] = None
        return

    if resultado.get("sucesso") is False:
        print("\nAgente:", resultado["mensagem"])
        dados_locacao["quantidade"] = None
        return

    # Guarda o orçamento na sessão do cliente.
    sessao["orcamento_atual"] = resultado
    sessao["estado"] = "aguardando_confirmacao"

    # --------------------------------------
    # MOSTRA RESUMO PARA CONFIRMAÇÃO
    # --------------------------------------

    print("\nAgente: Confira os dados da locação:")

    print(f"- Cliente: {dados_locacao['nome_cliente']}")
    print(f"- Telefone: {dados_locacao['telefone']}")
    print(f"- Equipamento: {resultado['equipamento']}")
    print(f"- Quantidade: {resultado['quantidade']}")
    print(f"- Dias: {resultado['dias']}")

    print(
        f"- Diária por unidade: "
        f"R$ {resultado['preco_diaria']:.2f}"
    )

    print(
        f"- Valor total: "
        f"R$ {resultado['valor_total']:.2f}"
    )

    print(
        "\nDeseja confirmar a locação? "
        "Responda sim ou não."
    )


# ==========================================
# FERRAMENTAS DO ATENDIMENTO NORMAL
# ==========================================

ferramentas = [
    consultar_estoque,
    consultar_preco,
    calcular_orcamento,
    consultar_locacao,
    consultar_locacoes_cliente,
    finalizar_locacao
]


mapa_ferramentas = {
    "consultar_estoque": consultar_estoque,
    "consultar_preco": consultar_preco,
    "calcular_orcamento": calcular_orcamento,
    "consultar_locacao": consultar_locacao,
    "consultar_locacoes_cliente": consultar_locacoes_cliente,
    "finalizar_locacao": finalizar_locacao
}


# ==========================================
# INTERFACE DE TERMINAL
# ==========================================

print("================================")
print("      AGENTE ALUGA FÁCIL")
print("================================")
print("Digite 'sair' no campo de telefone para encerrar.")
print("Informe o telefone antes de cada mensagem.")
print()


# ==========================================
# LOOP PRINCIPAL
# ==========================================

while True:
    telefone = input(
        "\nTelefone do cliente (ou 'sair'): "
    ).strip()

    if telefone.lower() == "sair":
        print("\nAgente encerrado.")
        break

    try:
        sessao = obter_sessao(telefone)
    except ValueError as erro:
        print(f"\nAviso: {erro}")
        continue

    mensagem = input("Cliente: ").strip()

    if not mensagem:
        continue

    # --------------------------------------
    # NOVA LOCAÇÃO OU CONTINUAÇÃO DE LOCAÇÃO
    # --------------------------------------

    if (
        sessao["estado"] != "normal"
        or quer_alugar(mensagem)
    ):
        if sessao["estado"] == "normal":
            limpar_locacao(sessao)
            sessao["estado"] = "coletando_locacao"

        processar_locacao(sessao, mensagem)
        continue

    # --------------------------------------
    # ATENDIMENTO NORMAL
    # --------------------------------------

    historico = sessao["historico"]

    historico.append(
        {
            "role": "user",
            "content": mensagem
        }
    )

    while True:
        resposta = ollama.chat(
            model=MODELO,
            messages=historico,
            tools=ferramentas,
            think=False
        )

        mensagem_ia = resposta["message"]

        historico.append(mensagem_ia)

        tool_calls = mensagem_ia.get("tool_calls")

        # ----------------------------------
        # RESPOSTA FINAL DO MODELO
        # ----------------------------------

        if not tool_calls:
            print(
                "\nAgente:",
                mensagem_ia.get("content", "")
            )
            break

        # ----------------------------------
        # EXECUTA AS FERRAMENTAS SOLICITADAS
        # ----------------------------------

        for chamada in tool_calls:
            nome_funcao = chamada["function"]["name"]
            argumentos = chamada["function"]["arguments"]

            print(
                f"\n[Agente usando ferramenta: "
                f"{nome_funcao}]"
            )

            funcao = mapa_ferramentas.get(nome_funcao)

            if funcao is None:
                resultado = {
                    "erro": True,
                    "mensagem": "Ferramenta não encontrada."
                }
            else:
                try:
                    resultado = funcao(**argumentos)
                except Exception as erro:
                    resultado = {
                        "erro": True,
                        "mensagem": str(erro)
                    }

            historico.append(
                {
                    "role": "tool",
                    "tool_name": nome_funcao,
                    "content": json.dumps(
                        resultado,
                        ensure_ascii=False
                    )
                }
            )