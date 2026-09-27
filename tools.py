import re
import sqlite3
import unicodedata

from banco import conectar


# ==========================================
# CONFIGURAÇÕES
# ==========================================

TERMOS_GENERICOS = {
    "ferramenta",
    "ferramentas",
    "equipamento",
    "equipamentos",
    "maquina",
    "maquinas",
    "produto",
    "produtos"
}


# ==========================================
# FUNÇÕES AUXILIARES
# ==========================================

def normalizar_texto(texto):
    """Remove acentos e padroniza o texto."""
    texto = str(texto).strip().lower()

    texto = unicodedata.normalize("NFD", texto)

    return "".join(
        caractere
        for caractere in texto
        if unicodedata.category(caractere) != "Mn"
    )


def normalizar_telefone(telefone):
    """Mantém somente os números do telefone."""
    return re.sub(r"\D", "", str(telefone))


def equipamento_valido(equipamento):
    """Verifica se o cliente informou um equipamento específico."""
    if not isinstance(equipamento, str):
        return False

    nome = normalizar_texto(equipamento)

    return bool(nome) and nome not in TERMOS_GENERICOS


def buscar_produto(cursor, equipamento):
    """
    Busca um produto pelo nome, aceitando nomes parciais
    e diferenças de acentuação.
    """
    cursor.execute(
        """
        SELECT id, nome, quantidade, preco_diaria
        FROM produtos
        ORDER BY id
        """
    )

    produtos = cursor.fetchall()

    termo = normalizar_texto(equipamento)

    # Primeiro tenta encontrar o nome exato.
    for produto in produtos:
        nome_normalizado = normalizar_texto(produto[1])

        if nome_normalizado == termo:
            return produto

    # Depois tenta encontrar uma correspondência parcial.
    correspondencias = [
        produto
        for produto in produtos
        if termo in normalizar_texto(produto[1])
    ]

    if not correspondencias:
        return None

    # Se houver mais de uma correspondência,
    # prioriza o nome mais curto.
    correspondencias.sort(
        key=lambda produto: len(produto[1])
    )

    return correspondencias[0]


def validar_quantidade(valor, campo):
    """Converte e valida quantidades inteiras positivas."""
    try:
        numero = int(valor)
    except (TypeError, ValueError):
        return None

    if numero <= 0:
        return None

    return numero


def validar_telefone(telefone):
    """Valida um telefone com DDD e números."""
    if not isinstance(telefone, str):
        return None

    numero = normalizar_telefone(telefone)

    if not 10 <= len(numero) <= 13:
        return None

    return numero


def erro(mensagem, **dados):
    """Padroniza respostas de erro das ferramentas."""
    return {
        "sucesso": False,
        "erro": True,
        "mensagem": mensagem,
        **dados
    }


# ==========================================
# CONSULTAR ESTOQUE
# ==========================================

def consultar_estoque(equipamento: str):
    """
    Consulta a quantidade disponível de um equipamento.

    Args:
        equipamento: Nome do equipamento.

    Returns:
        Dados sobre o estoque e a disponibilidade.
    """

    if not equipamento_valido(equipamento):
        return {
            "encontrado": False,
            "precisa_especificar": True,
            "mensagem": "Informe qual equipamento deseja consultar."
        }

    conexao = conectar()

    try:
        cursor = conexao.cursor()

        produto = buscar_produto(
            cursor,
            equipamento
        )

        if produto is None:
            return {
                "encontrado": False,
                "mensagem": "Equipamento não encontrado."
            }

        produto_id, nome, quantidade, preco_diaria = produto

        return {
            "encontrado": True,
            "equipamento": nome,
            "quantidade": quantidade,
            "disponivel": quantidade > 0,
            "mensagem": (
                f"Há {quantidade} unidade(s) de {nome} "
                f"disponíveis."
                if quantidade > 0
                else f"No momento, não há unidades de {nome} disponíveis."
            )
        }

    finally:
        conexao.close()


# ==========================================
# CONSULTAR PREÇO
# ==========================================

def consultar_preco(equipamento: str):
    """
    Consulta o preço da diária de um equipamento.

    Args:
        equipamento: Nome do equipamento.

    Returns:
        Nome e preço da diária.
    """

    if not equipamento_valido(equipamento):
        return {
            "encontrado": False,
            "precisa_especificar": True,
            "mensagem": "Informe qual equipamento deseja consultar."
        }

    conexao = conectar()

    try:
        cursor = conexao.cursor()

        produto = buscar_produto(
            cursor,
            equipamento
        )

        if produto is None:
            return {
                "encontrado": False,
                "mensagem": "Equipamento não encontrado."
            }

        produto_id, nome, quantidade, preco_diaria = produto

        return {
            "encontrado": True,
            "equipamento": nome,
            "preco_diaria": preco_diaria,
            "mensagem": (
                f"A diária de {nome} custa "
                f"R$ {preco_diaria:.2f}."
            )
        }

    finally:
        conexao.close()


# ==========================================
# CALCULAR ORÇAMENTO
# ==========================================

def calcular_orcamento(
    equipamento: str,
    dias: int,
    quantidade: int = 1
):
    """
    Calcula o orçamento de uma locação.

    Args:
        equipamento: Nome do equipamento.
        dias: Quantidade de dias da locação.
        quantidade: Quantidade de unidades desejadas.

    Returns:
        Dados do orçamento ou uma mensagem de erro.
    """

    if not equipamento_valido(equipamento):
        return {
            "encontrado": False,
            "precisa_especificar": True,
            "mensagem": "Informe qual equipamento deseja alugar."
        }

    dias = validar_quantidade(dias, "dias")
    quantidade = validar_quantidade(
        quantidade,
        "quantidade"
    )

    if dias is None:
        return erro(
            "A quantidade de dias deve ser um número inteiro positivo."
        )

    if quantidade is None:
        return erro(
            "A quantidade de unidades deve ser um número inteiro positivo."
        )

    conexao = conectar()

    try:
        cursor = conexao.cursor()

        produto = buscar_produto(
            cursor,
            equipamento
        )

        if produto is None:
            return {
                "encontrado": False,
                "mensagem": "Equipamento não encontrado."
            }

        produto_id, nome, estoque, preco_diaria = produto

        if estoque < quantidade:
            return {
                "sucesso": False,
                "estoque_insuficiente": True,
                "mensagem": (
                    f"Estoque insuficiente para {nome}. "
                    f"Disponíveis: {estoque} unidade(s)."
                ),
                "equipamento": nome,
                "quantidade_solicitada": quantidade,
                "estoque_disponivel": estoque
            }

        valor_total = (
            preco_diaria
            * dias
            * quantidade
        )

        return {
            "sucesso": True,
            "encontrado": True,
            "equipamento": nome,
            "quantidade": quantidade,
            "dias": dias,
            "preco_diaria": preco_diaria,
            "valor_total": round(valor_total, 2)
        }

    finally:
        conexao.close()


# ==========================================
# REGISTRAR LOCAÇÃO
# ==========================================

def registrar_locacao(
    nome_cliente: str,
    telefone: str,
    equipamento: str,
    quantidade: int,
    dias: int
):
    """
    Registra uma locação no banco de dados.

    O registro só acontece depois de receber todos os
    dados obrigatórios e confirmar a disponibilidade.

    Args:
        nome_cliente: Nome do cliente.
        telefone: Telefone do cliente.
        equipamento: Nome do equipamento.
        quantidade: Quantidade de unidades.
        dias: Quantidade de dias.

    Returns:
        Confirmação do registro, com o número da locação.
    """

    if not isinstance(nome_cliente, str) or not nome_cliente.strip():
        return erro("O nome do cliente não foi informado.")

    telefone = validar_telefone(telefone)

    if telefone is None:
        return erro(
            "Informe um telefone válido com DDD."
        )

    if not equipamento_valido(equipamento):
        return {
            "sucesso": False,
            "precisa_especificar": True,
            "mensagem": "Informe qual equipamento deseja alugar."
        }

    dias = validar_quantidade(dias, "dias")
    quantidade = validar_quantidade(
        quantidade,
        "quantidade"
    )

    if dias is None:
        return erro(
            "A quantidade de dias deve ser um número inteiro positivo."
        )

    if quantidade is None:
        return erro(
            "A quantidade de unidades deve ser um número inteiro positivo."
        )

    conexao = conectar()

    try:
        cursor = conexao.cursor()

        # Inicia uma transação para evitar que o estoque
        # seja alterado sem que a locação seja registrada.
        cursor.execute("BEGIN IMMEDIATE")

        produto = buscar_produto(
            cursor,
            equipamento
        )

        if produto is None:
            conexao.rollback()

            return {
                "sucesso": False,
                "mensagem": "Equipamento não encontrado."
            }

        produto_id, nome_produto, estoque, preco_diaria = produto

        if estoque < quantidade:
            conexao.rollback()

            return {
                "sucesso": False,
                "estoque_insuficiente": True,
                "mensagem": (
                    f"Estoque insuficiente. "
                    f"Disponíveis: {estoque} unidade(s)."
                )
            }

        # Procura o cliente pelo telefone.
        cursor.execute(
            """
            SELECT id, nome, telefone
            FROM clientes
            """
        )

        clientes = cursor.fetchall()

        cliente = next(
            (
                item
                for item in clientes
                if normalizar_telefone(item[2]) == telefone
            ),
            None
        )

        if cliente is None:
            cursor.execute(
                """
                INSERT INTO clientes (nome, telefone)
                VALUES (?, ?)
                """,
                (
                    nome_cliente.strip(),
                    telefone
                )
            )

            cliente_id = cursor.lastrowid
            nome_salvo = nome_cliente.strip()

        else:
            cliente_id = cliente[0]
            nome_salvo = cliente[1]

        valor_total = round(
            preco_diaria * quantidade * dias,
            2
        )

        # Registra a locação.
        cursor.execute(
            """
            INSERT INTO locacoes (
                cliente_id,
                produto_id,
                quantidade,
                dias,
                valor_total,
                status
            )
            VALUES (?, ?, ?, ?, ?, 'ativa')
            """,
            (
                cliente_id,
                produto_id,
                quantidade,
                dias,
                valor_total
            )
        )

        locacao_id = cursor.lastrowid

        # Atualiza o estoque dentro da mesma transação.
        cursor.execute(
            """
            UPDATE produtos
            SET quantidade = quantidade - ?
            WHERE id = ?
              AND quantidade >= ?
            """,
            (
                quantidade,
                produto_id,
                quantidade
            )
        )

        if cursor.rowcount != 1:
            conexao.rollback()

            return erro(
                "Não foi possível atualizar o estoque. "
                "Verifique a disponibilidade e tente novamente."
            )

        conexao.commit()

        return {
            "sucesso": True,
            "locacao_id": locacao_id,
            "cliente": nome_salvo,
            "telefone": telefone,
            "equipamento": nome_produto,
            "quantidade": quantidade,
            "dias": dias,
            "preco_diaria": preco_diaria,
            "valor_total": valor_total,
            "estoque_restante": estoque - quantidade,
            "status": "ativa"
        }

    except Exception as excecao:
        conexao.rollback()

        return erro(
            f"Erro ao registrar a locação: {excecao}"
        )

    finally:
        conexao.close()


# ==========================================
# CONSULTAR LOCAÇÃO POR NÚMERO
# ==========================================

def consultar_locacao(locacao_id: int):
    """
    Consulta uma locação pelo seu número.

    Args:
        locacao_id: Número identificador da locação.

    Returns:
        Dados da locação encontrada.
    """

    locacao_id = validar_quantidade(
        locacao_id,
        "locacao_id"
    )

    if locacao_id is None:
        return {
            "encontrado": False,
            "mensagem": "Informe um número de locação válido."
        }

    conexao = conectar()

    try:
        cursor = conexao.cursor()

        cursor.execute(
            """
            SELECT
                locacoes.id,
                clientes.nome,
                clientes.telefone,
                produtos.nome,
                locacoes.quantidade,
                locacoes.dias,
                locacoes.valor_total,
                locacoes.status
            FROM locacoes
            INNER JOIN clientes
                ON clientes.id = locacoes.cliente_id
            INNER JOIN produtos
                ON produtos.id = locacoes.produto_id
            WHERE locacoes.id = ?
            """,
            (locacao_id,)
        )

        locacao = cursor.fetchone()

        if locacao is None:
            return {
                "encontrado": False,
                "mensagem": "Locação não encontrada."
            }

        (
            id_locacao,
            nome_cliente,
            telefone,
            equipamento,
            quantidade,
            dias,
            valor_total,
            status
        ) = locacao

        return {
            "encontrado": True,
            "locacao_id": id_locacao,
            "cliente": nome_cliente,
            "telefone": telefone,
            "equipamento": equipamento,
            "quantidade": quantidade,
            "dias": dias,
            "valor_total": valor_total,
            "status": status
        }

    finally:
        conexao.close()


# ==========================================
# CONSULTAR LOCAÇÕES DE UM CLIENTE
# ==========================================

def consultar_locacoes_cliente(telefone: str):
    """
    Lista as locações de um cliente usando o telefone.

    Args:
        telefone: Telefone do cliente com DDD.

    Returns:
        Lista de locações encontradas.
    """

    telefone = validar_telefone(telefone)

    if telefone is None:
        return {
            "encontrado": False,
            "mensagem": "Informe um telefone válido com DDD."
        }

    conexao = conectar()

    try:
        cursor = conexao.cursor()

        cursor.execute(
            """
            SELECT id, telefone
            FROM clientes
            """
        )

        clientes = cursor.fetchall()

        cliente = next(
            (
                item
                for item in clientes
                if normalizar_telefone(item[1]) == telefone
            ),
            None
        )

        if cliente is None:
            return {
                "encontrado": False,
                "mensagem": (
                    "Não encontramos um cliente com esse telefone."
                )
            }

        cliente_id = cliente[0]

        cursor.execute(
            """
            SELECT
                locacoes.id,
                produtos.nome,
                locacoes.quantidade,
                locacoes.dias,
                locacoes.valor_total,
                locacoes.status
            FROM locacoes
            INNER JOIN produtos
                ON produtos.id = locacoes.produto_id
            WHERE locacoes.cliente_id = ?
            ORDER BY locacoes.id DESC
            """,
            (cliente_id,)
        )

        locacoes = cursor.fetchall()

        if not locacoes:
            return {
                "encontrado": True,
                "locacoes": [],
                "mensagem": "O cliente não possui locações registradas."
            }

        resultado = []

        for locacao in locacoes:
            (
                id_locacao,
                equipamento,
                quantidade,
                dias,
                valor_total,
                status
            ) = locacao

            resultado.append(
                {
                    "locacao_id": id_locacao,
                    "equipamento": equipamento,
                    "quantidade": quantidade,
                    "dias": dias,
                    "valor_total": valor_total,
                    "status": status
                }
            )

        return {
            "encontrado": True,
            "telefone": telefone,
            "locacoes": resultado
        }

    finally:
        conexao.close()


# ==========================================
# FINALIZAR LOCAÇÃO / DEVOLVER EQUIPAMENTO
# ==========================================

def finalizar_locacao(locacao_id: int):
    """
    Finaliza uma locação ativa e devolve as unidades
    ao estoque. Não permite finalizar duas vezes.

    Args:
        locacao_id: Número identificador da locação.

    Returns:
        Resultado da finalização e estoque atualizado.
    """

    locacao_id = validar_quantidade(
        locacao_id,
        "locacao_id"
    )

    if locacao_id is None:
        return {
            "sucesso": False,
            "mensagem": "Informe um número de locação válido."
        }

    conexao = conectar()

    try:
        cursor = conexao.cursor()

        cursor.execute("BEGIN IMMEDIATE")

        cursor.execute(
            """
            SELECT
                locacoes.id,
                clientes.nome,
                clientes.telefone,
                produtos.nome,
                locacoes.quantidade,
                locacoes.dias,
                locacoes.valor_total,
                locacoes.status,
                produtos.id
            FROM locacoes
            INNER JOIN clientes
                ON clientes.id = locacoes.cliente_id
            INNER JOIN produtos
                ON produtos.id = locacoes.produto_id
            WHERE locacoes.id = ?
            """,
            (locacao_id,)
        )

        locacao = cursor.fetchone()

        if locacao is None:
            conexao.rollback()

            return {
                "sucesso": False,
                "mensagem": "Locação não encontrada."
            }

        (
            id_locacao,
            nome_cliente,
            telefone,
            equipamento,
            quantidade,
            dias,
            valor_total,
            status,
            produto_id
        ) = locacao

        if status != "ativa":
            conexao.rollback()

            return {
                "sucesso": False,
                "mensagem": (
                    f"Esta locação não está ativa. "
                    f"Status atual: {status}."
                ),
                "status": status,
                "locacao_id": id_locacao
            }

        # Devolve as unidades ao estoque.
        cursor.execute(
            """
            UPDATE produtos
            SET quantidade = quantidade + ?
            WHERE id = ?
            """,
            (
                quantidade,
                produto_id
            )
        )

        if cursor.rowcount != 1:
            conexao.rollback()

            return erro(
                "Não foi possível atualizar o estoque."
            )

        novo_estoque = cursor.execute(
            """
            SELECT quantidade
            FROM produtos
            WHERE id = ?
            """,
            (produto_id,)
        ).fetchone()[0]

        # Altera o status da locação.
        cursor.execute(
            """
            UPDATE locacoes
            SET status = 'finalizada'
            WHERE id = ?
              AND status = 'ativa'
            """,
            (locacao_id,)
        )

        if cursor.rowcount != 1:
            conexao.rollback()

            return erro(
                "Não foi possível finalizar a locação."
            )

        conexao.commit()

        return {
            "sucesso": True,
            "locacao_id": id_locacao,
            "cliente": nome_cliente,
            "telefone": telefone,
            "equipamento": equipamento,
            "quantidade_devolvida": quantidade,
            "estoque_atual": novo_estoque,
            "status": "finalizada",
            "mensagem": "Locação finalizada com sucesso."
        }

    except Exception as excecao:
        conexao.rollback()

        return erro(
            f"Erro ao finalizar a locação: {excecao}"
        )

    finally:
        conexao.close()