import sqlite3


ARQUIVO_BANCO = "dados.db"


def conectar():
    return sqlite3.connect(ARQUIVO_BANCO)


def criar_tabelas():
    conexao = conectar()
    cursor = conexao.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS produtos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            quantidade INTEGER NOT NULL,
            preco_diaria REAL NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS clientes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            telefone TEXT NOT NULL UNIQUE
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS locacoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente_id INTEGER NOT NULL,
            produto_id INTEGER NOT NULL,
            quantidade INTEGER NOT NULL,
            dias INTEGER NOT NULL,
            valor_total REAL NOT NULL,
            status TEXT NOT NULL DEFAULT 'ativa',
            FOREIGN KEY (cliente_id) REFERENCES clientes(id),
            FOREIGN KEY (produto_id) REFERENCES produtos(id)
        )
    """)

    conexao.commit()
    conexao.close()


def cadastrar_produto(nome, quantidade, preco_diaria):
    conexao = conectar()
    cursor = conexao.cursor()

    cursor.execute(
        """
        INSERT INTO produtos (
            nome,
            quantidade,
            preco_diaria
        )
        VALUES (?, ?, ?)
        """,
        (nome, quantidade, preco_diaria)
    )

    conexao.commit()
    conexao.close()


def cadastrar_produto_se_nao_existir(
    nome,
    quantidade,
    preco_diaria
):
    conexao = conectar()
    cursor = conexao.cursor()

    cursor.execute(
        """
        SELECT id
        FROM produtos
        WHERE nome = ?
        """,
        (nome,)
    )

    produto = cursor.fetchone()

    if produto is None:
        cursor.execute(
            """
            INSERT INTO produtos (
                nome,
                quantidade,
                preco_diaria
            )
            VALUES (?, ?, ?)
            """,
            (nome, quantidade, preco_diaria)
        )

        conexao.commit()

    conexao.close()


def carregar_dados_iniciais():
    cadastrar_produto_se_nao_existir(
        "Betoneira 400L",
        3,
        120.00
    )

    cadastrar_produto_se_nao_existir(
        "Martelete 10kg",
        5,
        80.00
    )

    cadastrar_produto_se_nao_existir(
        "Furadeira",
        8,
        45.00
    )

    cadastrar_produto_se_nao_existir(
        "Serra Mármore",
        4,
        60.00
    )

    cadastrar_produto_se_nao_existir(
        "Compactador de Solo",
        2,
        180.00
    )


def cadastrar_cliente(nome, telefone):
    conexao = conectar()
    cursor = conexao.cursor()

    cursor.execute(
        """
        SELECT id, nome, telefone
        FROM clientes
        WHERE telefone = ?
        """,
        (telefone,)
    )

    cliente = cursor.fetchone()

    if cliente is not None:
        conexao.close()

        return {
            "cadastrado": False,
            "ja_existia": True,
            "id": cliente[0],
            "nome": cliente[1],
            "telefone": cliente[2]
        }

    cursor.execute(
        """
        INSERT INTO clientes (
            nome,
            telefone
        )
        VALUES (?, ?)
        """,
        (nome, telefone)
    )

    cliente_id = cursor.lastrowid

    conexao.commit()
    conexao.close()

    return {
        "cadastrado": True,
        "id": cliente_id,
        "nome": nome,
        "telefone": telefone
    }


def buscar_cliente_por_telefone(telefone):
    conexao = conectar()
    cursor = conexao.cursor()

    cursor.execute(
        """
        SELECT id, nome, telefone
        FROM clientes
        WHERE telefone = ?
        """,
        (telefone,)
    )

    cliente = cursor.fetchone()

    conexao.close()

    return cliente


def buscar_produto_por_nome(nome):
    conexao = conectar()
    cursor = conexao.cursor()

    cursor.execute(
        """
        SELECT id, nome, quantidade, preco_diaria
        FROM produtos
        WHERE nome LIKE ?
        """,
        (f"%{nome}%",)
    )

    produto = cursor.fetchone()

    conexao.close()

    return produto


def atualizar_estoque(
    produto_id,
    nova_quantidade
):
    conexao = conectar()
    cursor = conexao.cursor()

    cursor.execute(
        """
        UPDATE produtos
        SET quantidade = ?
        WHERE id = ?
        """,
        (nova_quantidade, produto_id)
    )

    conexao.commit()
    conexao.close()


def registrar_locacao(
    cliente_id,
    produto_id,
    quantidade,
    dias,
    valor_total
):
    conexao = conectar()
    cursor = conexao.cursor()

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

    conexao.commit()
    conexao.close()

    return locacao_id
def consultar_locacao_por_id(locacao_id):
    conexao = conectar()
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

    conexao.close()

    return locacao


def listar_locacoes_por_telefone(telefone):
    conexao = conectar()
    cursor = conexao.cursor()

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
        INNER JOIN clientes
            ON clientes.id = locacoes.cliente_id
        INNER JOIN produtos
            ON produtos.id = locacoes.produto_id
        WHERE clientes.telefone = ?
        ORDER BY locacoes.id DESC
        """,
        (telefone,)
    )

    locacoes = cursor.fetchall()

    conexao.close()

    return locacoes


def atualizar_status_locacao(locacao_id, novo_status):
    conexao = conectar()
    cursor = conexao.cursor()

    cursor.execute(
        """
        UPDATE locacoes
        SET status = ?
        WHERE id = ?
        """,
        (novo_status, locacao_id)
    )

    conexao.commit()
    conexao.close()