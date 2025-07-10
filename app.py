import customtkinter as ctk
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog
from tkcalendar import DateEntry
import mysql.connector
import openpyxl
from pathlib import Path
from datetime import datetime
import calendar
import tempfile
import os
import subprocess
import json
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
import uuid
from tkinter import Toplevel

CONFIG_FILE = "config.json"

def carregar_configuracoes():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"impressora": "", "modelo": ""}

def salvar_configuracoes(config):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4)

def definir_impressora():
    config = carregar_configuracoes()
    nova = simpledialog.askstring("Impressora", "Digite o nome da impressora:", initialvalue=config.get("impressora", ""))
    if nova:
        config["impressora"] = nova
        salvar_configuracoes(config)
        messagebox.showinfo("Salvo", f"Impressora definida:\n{nova}")

def escolher_logo():
    arquivo = filedialog.askopenfilename(title="Selecionar logotipo", filetypes=[("Todos arquivos", "*.*")])
    if arquivo:
        config = carregar_configuracoes()
        config["logo"] = arquivo
        salvar_configuracoes(config)
        messagebox.showinfo("Salvo", f"Logo Salvo:\n{arquivo}")

def exportar_excel():
    if not tree.get_children():
        messagebox.showwarning("Aviso", "Não há dados para exportar.")
        return

    desktop = Path.home() / "Desktop"
    nome_arquivo = desktop / f"relatorio_vendas_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Relatório de Vendas"

    colunas = ("Produto", "Tipo", "Preço Unitário", "Quantidade", "Cliente", "Situação")
    ws.append(colunas)

    total = 0
    for item in tree.get_children():
        valores = tree.item(item)["values"]
        preco = float(valores[2])
        qtd = float(valores[3])
        total += preco * qtd
        ws.append(valores)

    ws.append([])
    ws.append(["", "", "", "TOTAL GERAL:", total])

    try:
        wb.save(nome_arquivo)
        messagebox.showinfo("Exportado", f"Arquivo salvo em:\n{nome_arquivo}")
    except Exception as e:
        messagebox.showerror("Erro ao salvar", str(e))

def abrir_anydesk():
    try:
        caminho_anydesk = os.path.join(os.getcwd(), "anydesk.exe")
        subprocess.Popen([caminho_anydesk], shell=True)
    except Exception as e:
        messagebox.showerror("Erro", f"Falha ao abrir o AnyDesk:\n{e}")

def conectar_banco():
    try:
        return mysql.connector.connect(
            host="localhost",
            user="root",
            password="mysql147",
            database="sistema"
        )
    except mysql.connector.Error as e:
        messagebox.showerror("Erro de conexão", str(e))
        return None

def carregar_dados():
    conexao = conectar_banco()
    if not conexao:
        return

    cursor = conexao.cursor(dictionary=True)
    query = """
SELECT 
    m.nomeProduto,
    m.tipo,
    m.vlrUnitario,
    m.quantidade,
    p.nome AS cliente_nome,
    m.dataMov,
    m.situacao,
    d.tipoDoc
FROM movdocs m
JOIN docs d ON m.numero = d.numero
LEFT JOIN pessoas p ON m.usuario = p.tipoPessoa
WHERE 1=1
"""
    valores = []

    data_ini = filtro_data_ini.get_date().strftime('%Y-%m-%d')
    data_fim = filtro_data_fim.get_date().strftime('%Y-%m-%d')
    query += " AND m.dataMov BETWEEN %s AND %s"
    valores.extend([data_ini, data_fim])

    filtro = valor_filtro_texto.get().strip()
    filtro_selecionado = campo_filtro.get()

    if filtro:
        if filtro_selecionado == "tipo":
            query += " AND m.tipo LIKE %s"
            valores.append(f"%{filtro}%")
        elif filtro_selecionado == "Cliente":
            query += " AND p.nome LIKE %s"
            valores.append(f"%{filtro}%")
        elif filtro_selecionado == "Produto":
            query += " AND m.nomeProduto LIKE %s"
            valores.append(f"%{filtro}%")
        elif filtro_selecionado == "Forma Pagamento":
            query += " AND m.formaPagamento LIKE %s"
            valores.append(f"%{filtro}%")

    tipo_doc = campo_tipo_doc.get()
    if tipo_doc != "Todos":
        query += " AND d.tipoDoc = %s"
        valores.append(tipo_doc)

    situacao = campo_situacao.get()
    if situacao == "Emitidos":
        query += " AND m.situacao = 'Emitidos'"
        
    if situacao == "Cancelados":
        query += " AND m.situacao = 'Cancelados'"
        
    elif situacao == "Fechados":
        query += " AND m.situacao = 'FECHADO'"

    cursor.execute(query, valores)
    resultados = cursor.fetchall()
    conexao.close()

    if not resultados:
        messagebox.showinfo("Sem resultados", "Nenhum dado encontrado para os filtros aplicados.")

    atualizar_treeview(resultados)

def atualizar_treeview(registros):
    for item in tree.get_children():
        tree.delete(item)

    total = 0
    for row in registros:
        valor_total = float(row["vlrUnitario"]) * float(row["quantidade"])
        total += valor_total
        tree.insert("", "end", values=(
            row["nomeProduto"], row["tipo"], row["vlrUnitario"],
            row["quantidade"], row["cliente_nome"], row["situacao"]
        ))

    lbl_total.configure(text=f"Total Geral: R$ {total:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
# Conecte ao banco e monte um dicionário id → nome
import mysql.connector

def obter_dados_empresa():
    conexao = conectar_banco()
    if not conexao:
        return {"empresa": "EMPRESA", "cpfCnpj": "00.000.000/0000-00"}

    cursor = conexao.cursor(dictionary=True)
    cursor.execute("SELECT nome, cpfCnpj FROM empresas WHERE id = 1 LIMIT 1")
    resultado = cursor.fetchone()
    conexao.close()

    if resultado:
        return {"empresa": resultado["nome"], "cpfCnpj": resultado["cpfCnpj"]}
    else:
        return {"empresa": "EMPRESA", "cpfCnpj": "00.000.000/0000-00"}

# várias formas de previsualição conforme a QUEBRA
def gerar_pdf_preview():
    agrupamento = campo_filtro.get()
    
    if agrupamento == "Produto":
        gerar_pdf_por_produto()
    elif agrupamento == "Cliente":
        gerar_pdf_por_cliente()
    elif agrupamento == "Tipo":
        gerar_pdf_por_tipo()
    elif agrupamento == "Forma Pagamento":
        gerar_pdf_por_forma_pagamento()
    else:
        gerar_pdf_simples()
        
# GERAR A PREVISUALIZACAO DO RELATORIO EM PDF
def gerar_pdf_por_cliente():
    agrupamento = "Cliente"
    dados_agrupados = {}

    for item in tree.get_children():
        produto, tipo, preco, qtd, cliente, situacao = tree.item(item)["values"]
        preco = float(preco)
        qtd = float(qtd)
        total = preco * qtd

        chave = str(cliente)
        if chave not in dados_agrupados:
            dados_agrupados[chave] = []

        dados_agrupados[chave].append({
            "produto": str(produto),
            "tipo": str(tipo),
            "preco": preco,
            "qtd": qtd,
            "situacao": str(situacao),
            "total": total
        })

    if not dados_agrupados:
        messagebox.showwarning("PDF vazio", "Nenhum dado visível para gerar PDF.")
        return

    nome_pdf = os.path.join(tempfile.gettempdir(), f"relatorio_{uuid.uuid4().hex}.pdf")
    c = canvas.Canvas(nome_pdf, pagesize=A4)
    width, height = A4

    dados_empresa = obter_dados_empresa()
    c.setFont("Helvetica-Bold", 14)
    c.drawString(40, height - 40, f"RELATÓRIO POR {agrupamento.upper()}")

    c.setFont("Helvetica", 10)
    c.drawString(40, height - 60, str(dados_empresa["empresa"]))
    c.drawString(40, height - 72, str(dados_empresa["cpfCnpj"]))
    c.drawRightString(width - 40, height - 40, f"Emissão: {datetime.now().strftime('%d/%m/%Y')}")

    periodo_txt = f"Período: {filtro_data_ini.get_date().strftime('%d/%m/%Y')} até {filtro_data_fim.get_date().strftime('%d/%m/%Y')}"
    c.drawString(40, height - 90, periodo_txt)

    y = height - 120
    total_geral = 0

    for cliente, itens in dados_agrupados.items():
        c.setFont("Helvetica-Bold", 11)
        c.setFillColorRGB(0.9, 0.9, 1)
        c.rect(30, y, width - 60, 20, fill=1)
        c.setFillColorRGB(0, 0, 0)
        c.drawString(35, y + 5, f"🔸 CLIENTE: {cliente}")
        y -= 25

        c.setFont("Helvetica-Bold", 9)
        c.drawString(40, y, "Produto")
        c.drawString(200, y, "Tipo")
        c.drawString(300, y, "Qtd")
        c.drawString(340, y, "Preço Unit.")
        c.drawString(440, y, "Total")
        y -= 15

        total_cliente = 0
        for item in itens:
            if y < 60:
                c.showPage()
                y = height - 60

            c.setFont("Helvetica", 8)
            c.drawString(40, y, item["produto"])
            c.drawString(200, y, item["tipo"])
            c.drawString(300, y, str(item["qtd"]))
            c.drawString(340, y, f"R$ {item['preco']:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
            c.drawString(440, y, f"R$ {item['total']:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
            total_cliente += item["total"]
            total_geral += item["total"]
            y -= 13

        y -= 10
        c.setFont("Helvetica-Bold", 9)
        c.drawString(340, y, f"Total: R$ {total_cliente:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
        y -= 20

    c.setFont("Helvetica-Bold", 10)
    c.drawString(35, y, f"TOTAL GERAL: R$ {total_geral:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

    c.save()
    os.startfile(nome_pdf)
def obter_nomes_clientes():
    conn = mysql.connector.connect(
        host='localhost',
        user='root',
        password='mysql147',
        database='sistema'
    )
    cursor = conn.cursor()
    cursor.execute("SELECT idCliForn, nomeCliForn FROM movdocs")
    dados = cursor.fetchall()
    conn.close()
    return {str(id_): nome for id_, nome in dados}
 
# PDF COM QUEBRA POR PRODUTO
def gerar_pdf_por_produto():
    agrupamentos = "Produtos"
    clientes_dict = obter_nomes_clientes()

    dados_agrupados = {}
    for item in tree.get_children():
        produto, categoria, preco, qtd, cliente, situacao = tree.item(item)["values"]
        preco = float(preco)
        qtd = float(qtd)
        total = preco * qtd

        if produto not in dados_agrupados:
            dados_agrupados[produto] = []

        dados_agrupados[produto].append({
            "categoria": categoria,
            "preco": preco,
            "qtd": qtd,
            "cliente": cliente,
            "situacao": situacao,
            "total": total
        })

    if not dados_agrupados:
        messagebox.showwarning("PDF vazio", "Nenhum dado visível para gerar PDF.")
        return

    nome_pdf = os.path.join(tempfile.gettempdir(), f"relatorio_produtos_{uuid.uuid4().hex}.pdf")
    c = canvas.Canvas(nome_pdf, pagesize=A4)
    width, height = A4

    dados_empresa = obter_dados_empresa()

    c.setFont("Helvetica-Bold", 14)
    c.drawString(40, height - 40, "RELATÓRIO DE VENDAS por PRODUTO")

    c.setFont("Helvetica", 10)
    c.drawString(40, height - 58, dados_empresa["empresa"])
    c.drawString(40, height - 70, dados_empresa["cpfCnpj"])
    c.drawRightString(width - 40, height - 40, f"Emissão: {datetime.now().strftime('%d/%m/%Y')}")

    periodo_txt = f"Período: {filtro_data_ini.get_date().strftime('%d/%m/%Y')} até {filtro_data_fim.get_date().strftime('%d/%m/%Y')}"
    c.drawString(40, height - 83, periodo_txt)

    y = height - 110
    total_geral = 0

    for produto, itens in dados_agrupados.items():
        codigo = abs(hash(produto)) % 999
        c.setFont("Helvetica-Bold", 9)
        c.setFillColorRGB(0.8, 0.85, 1)
        c.rect(30, y, width - 60, 25, fill=1)
        c.setFillColorRGB(0, 0, 0)

        c.setFont("Helvetica-Bold", 11)
        c.drawString(35, y + 7, f"■ PRODUTO: {produto}   Cód: {codigo}")
        y -= 25

        # Cabeçalho das colunas
        c.setFont("Helvetica-Bold", 8)
        c.drawString(35, y, "Cliente")
        c.drawString(270, y, "Nº Doc.")
        c.drawString(350, y, "Qtd")
        c.drawString(400, y, "Preço Unit.")
        c.drawString(470, y, "Total")
        c.drawString(520, y, "Situação")
        c.drawString(560, y, "Tipo")
        y -= 15

        total_agrupado = 0
        for item in itens:
            if y < 70:
                c.showPage()
                y = height - 60

            c.setFont("Helvetica", 8)
            id_cliente = str(item.get("cliente", ""))
            nome_cliente = clientes_dict.get(id_cliente, f"ID: {id_cliente}")
            c.drawString(35, y, nome_cliente[:40])

# Nº Documento no lugar do preço unitário original
            c.drawString(270, y, str(item.get("id_documento", "")))

            c.drawString(350, y, str(item["qtd"]))

# Preço Unitário agora mais à direita
            c.drawString(400, y, f"R$ {item['preco']:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

            c.drawString(470, y, f"R$ {item['total']:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

            c.drawString(520, y, str(item["situacao"]))
            c.drawString(560, y, str(item["categoria"])[:15])
            total_agrupado += item["total"]
            total_geral += item["total"]
            y -= 13

        y -= 5
        c.setFont("Helvetica-Bold", 9)
        c.setFillColorRGB(0.9, 0.9, 1)
        c.rect(30, y, width - 60, 15, fill=1)
        c.setFillColorRGB(0, 0, 0)
        texto_total = f"Total Produto:  R$ {total_agrupado:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        c.drawRightString(width - 35, y + 3, texto_total)
        y -= 25

    if y < 60:
        c.showPage()
        y = height - 60

    c.setFont("Helvetica-Bold", 10)
    c.drawString(35, y, f"TOTAL GERAL:     R$ {total_geral:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

    c.save()
    os.startfile(nome_pdf)

# GERAR PDF POR FORMA DE PAGAMENTO
def gerar_pdf_por_forma_pagamento():
    agrupamento = "Forma de Pagamento"
    dados_agrupados = {}

    for item in tree.get_children():
        produto, tipo, preco, qtd, cliente, situacao = tree.item(item)["values"]
        preco = float(preco)
        qtd = float(qtd)
        total = preco * qtd

        forma_pagamento = "Indefinido"
        try:
            # Se você tiver a formaPagamento no Treeview, substitua aqui
            forma_pagamento = cliente  # <-- ajustar se campo correto estiver disponível
        except:
            pass

        chave = str(forma_pagamento)
        if chave not in dados_agrupados:
            dados_agrupados[chave] = []

        dados_agrupados[chave].append({
            "produto": str(produto),
            "tipo": str(tipo),
            "preco": preco,
            "qtd": qtd,
            "situacao": str(situacao),
            "total": total
        })

    if not dados_agrupados:
        messagebox.showwarning("PDF vazio", "Nenhum dado visível para gerar PDF.")
        return

    nome_pdf = os.path.join(tempfile.gettempdir(), f"relatorio_pagamento_{uuid.uuid4().hex}.pdf")
    c = canvas.Canvas(nome_pdf, pagesize=A4)
    width, height = A4

    dados_empresa = obter_dados_empresa()
    c.setFont("Helvetica-Bold", 14)
    c.drawString(40, height - 40, f"RELATÓRIO POR {agrupamento.upper()}")

    c.setFont("Helvetica", 10)
    c.drawString(40, height - 60, dados_empresa["empresa"])
    c.drawString(40, height - 72, dados_empresa["cpfCnpj"])
    c.drawRightString(width - 40, height - 40, f"Emissão: {datetime.now().strftime('%d/%m/%Y')}")

    periodo_txt = f"Período: {filtro_data_ini.get_date().strftime('%d/%m/%Y')} até {filtro_data_fim.get_date().strftime('%d/%m/%Y')}"
    c.drawString(40, height - 90, periodo_txt)

    y = height - 120
    total_geral = 0

    for forma, itens in dados_agrupados.items():
        c.setFont("Helvetica-Bold", 11)
        c.setFillColorRGB(0.9, 0.9, 1)
        c.rect(30, y, width - 60, 20, fill=1)
        c.setFillColorRGB(0, 0, 0)
        c.drawString(35, y + 5, f"💳 FORMA DE PAGAMENTO: {forma}")
        y -= 25

        c.setFont("Helvetica-Bold", 9)
        c.drawString(40, y, "Produto")
        c.drawString(200, y, "Tipo")
        c.drawString(300, y, "Qtd")
        c.drawString(340, y, "Preço Unit.")
        c.drawString(440, y, "Total")
        y -= 15

        total_fp = 0
        for item in itens:
            if y < 60:
                c.showPage()
                y = height - 60

            c.setFont("Helvetica", 8)
            c.drawString(40, y, item["produto"])
            c.drawString(200, y, item["tipo"])
            c.drawString(300, y, str(item["qtd"]))
            c.drawString(340, y, f"R$ {item['preco']:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
            c.drawString(440, y, f"R$ {item['total']:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
            total_fp += item["total"]
            total_geral += item["total"]
            y -= 13

        y -= 10
        c.setFont("Helvetica-Bold", 9)
        c.drawString(340, y, f"Total: R$ {total_fp:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
        y -= 20

    c.setFont("Helvetica-Bold", 10)
    c.drawString(35, y, f"TOTAL GERAL: R$ {total_geral:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

    c.save()
    os.startfile(nome_pdf)
    
# GERAR PDF POR TIPO = S SERVIÇO OU P PRODUTO
def gerar_pdf_por_tipo():
    agrupamento = "tipo"
    dados_agrupados = {}

    for item in tree.get_children():
        produto, tipo, preco, qtd, cliente, situacao = tree.item(item)["values"]
        preco = float(preco)
        qtd = float(qtd)
        total = preco * qtd

        chave = str(tipo)
        if chave not in dados_agrupados:
            dados_agrupados[chave] = []

        dados_agrupados[chave].append({
            "produto": str(produto),
            "cliente": str(cliente),
            "preco": preco,
            "qtd": qtd,
            "situacao": str(situacao),
            "total": total
        })

    if not dados_agrupados:
        messagebox.showwarning("PDF vazio", "Nenhum dado visível para gerar PDF.")
        return

    nome_pdf = os.path.join(tempfile.gettempdir(), f"relatorio_tipo_{uuid.uuid4().hex}.pdf")
    c = canvas.Canvas(nome_pdf, pagesize=A4)
    width, height = A4

    dados_empresa = obter_dados_empresa()
    c.setFont("Helvetica-Bold", 14)
    c.drawString(40, height - 40, f"RELATÓRIO POR {agrupamento.upper()}")

    c.setFont("Helvetica", 10)
    c.drawString(40, height - 60, dados_empresa["empresa"])
    c.drawString(40, height - 72, dados_empresa["cpfCnpj"])
    c.drawRightString(width - 40, height - 40, f"Emissão: {datetime.now().strftime('%d/%m/%Y')}")

    periodo_txt = f"Período: {filtro_data_ini.get_date().strftime('%d/%m/%Y')} até {filtro_data_fim.get_date().strftime('%d/%m/%Y')}"
    c.drawString(40, height - 90, periodo_txt)

    y = height - 120
    total_geral = 0

    for tipo, itens in dados_agrupados.items():
        c.setFont("Helvetica-Bold", 11)
        c.setFillColorRGB(0.9, 0.9, 1)
        c.rect(30, y, width - 60, 20, fill=1)
        c.setFillColorRGB(0, 0, 0)
        c.drawString(35, y + 5, f"📦 TIPO: {tipo}")
        y -= 25

        c.setFont("Helvetica-Bold", 9)
        c.drawString(40, y, "Produto")
        c.drawString(200, y, "Cliente")
        c.drawString(300, y, "Qtd")
        c.drawString(340, y, "Preço Unit.")
        c.drawString(440, y, "Total")
        y -= 15

        total_cat = 0
        for item in itens:
            if y < 60:
                c.showPage()
                y = height - 60

            c.setFont("Helvetica", 8)
            c.drawString(40, y, item["produto"])
            c.drawString(200, y, item["cliente"])
            c.drawString(300, y, str(item["qtd"]))
            c.drawString(340, y, f"R$ {item['preco']:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
            c.drawString(440, y, f"R$ {item['total']:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
            total_cat += item["total"]
            total_geral += item["total"]
            y -= 13

        y -= 10
        c.setFont("Helvetica-Bold", 9)
        c.drawString(340, y, f"Total: R$ {total_cat:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
        y -= 20

    c.setFont("Helvetica-Bold", 10)
    c.drawString(35, y, f"TOTAL GERAL: R$ {total_geral:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

    c.save()
    os.startfile(nome_pdf)
    
##########################################
def abrir_busca_produto(entry_modelo):
    janela = tk.Toplevel()
    janela.title("Buscar Produto")
    janela.geometry("600x400")
    janela.transient()

    entry_pesquisa = tk.Entry(janela, width=40)
    entry_pesquisa.pack(pady=10)

    tree = ttk.Treeview(janela, columns=("id", "descricao", "preco"), show="headings")
    tree.heading("id", text="ID")
    tree.heading("descricao", text="Descrição")
    tree.heading("preco", text="Preço")
    tree.column("id", width=50)
    tree.column("descricao", width=200)
    tree.column("preco", width=80)
    tree.pack(expand=True, fill="both")

    def buscar():
        termo = entry_pesquisa.get().strip()
        conexao = mysql.connector.connect(
            host="localhost",
            user="root",
            password="mysql147",
            database="sistema"
        )
        cursor = conexao.cursor()
        if termo:
            cursor.execute("""
                SELECT id, nome, vlrVenda 
                FROM produtos 
                WHERE nome LIKE %s
            """, (f"%{termo}%",))
        else:
            cursor.execute("""
                SELECT id, nome, vlrVenda 
                FROM produtos
            """)
        resultados = cursor.fetchall()
        cursor.close()
        conexao.close()

        for item in tree.get_children():
            tree.delete(item)

        for row in resultados:
            tree.insert("", "end", values=row)

    def selecionar_item(event):
        item = tree.selection()
        if item:
            valores = tree.item(item, "values")
            id_produto = valores[0]
            nome_produto = valores[1]

            entry_modelo.delete(0, tk.END)
            entry_modelo.insert(0, nome_produto)
            janela.destroy()

    botao_buscar = tk.Button(janela, text="Buscar", command=buscar)
    botao_buscar.pack(pady=5)

    tree.bind("<Double-1>", selecionar_item)

    buscar()  # Mostra todos os produtos ao abrir a janela
  

    tree.bind("<Double-1>", selecionar_item)


def abrir_busca_cliente():
    janela_busca = tk.Toplevel()  # <-- corrigido aqui
    janela_busca.title("Buscar Cliente")
    janela_busca.geometry("600x400")

    tree = ttk.Treeview(janela_busca, columns=("id", "nome", "cpf"), show="headings")
    tree.heading("id", text="ID")
    tree.heading("nome", text="Nome")
    tree.heading("cpf", text="CPF/CNPJ")
    tree.column("id", width=50)
    tree.column("nome", width=300)
    tree.column("cpf", width=150)
    tree.pack(fill="both", expand=True, padx=10, pady=10)

    def selecionar_cliente(event=None):
        item = tree.selection()
        if item:
            valores = tree.item(item[0])["values"]
            valor_filtro_texto.delete(0, tk.END)
            valor_filtro_texto.insert(0, f"{valores[1]}")  # ou valores[0] se quiser o ID
            janela_busca.destroy()

    tree.bind("<Double-1>", selecionar_cliente)

    try:
        conn = mysql.connector.connect(
            host='localhost',
            user='root',
            password='mysql147',
            database='sistema'
        )
        cursor = conn.cursor()
        cursor.execute("SELECT id, nome, cpfCnpj FROM pessoas WHERE tipoPessoa = 1 AND idempresa = 1")

        for linha in cursor.fetchall():
            tree.insert("", "end", values=linha)

        cursor.close()
        conn.close()

    except Exception as e:
        messagebox.showerror("Erro", f"Erro ao buscar clientes:\n{e}")

        
        
def acionar_lupa(entry_modelo):
    filtro = campo_filtro.get()
    if filtro == "Produto":
        abrir_busca_produto(entry_modelo)
    elif filtro == "Cliente":
        abrir_busca_cliente()
    else:
        messagebox.showinfo("Info", f"Busca não disponível para o filtro: {filtro}")
        
        
ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")
app = ctk.CTk()
app.title("Gerador de Relatorio Vendas - EvoluTI")
app.geometry("1150x700")

menu_bar = tk.Menu(app)
app.configure(menu=menu_bar)

menu_config = tk.Menu(menu_bar, tearoff=0)
menu_config.add_command(label="Definir Impressora...", command=definir_impressora)
menu_config.add_command(label="Selecionar Logotipo...", command=escolher_logo)
menu_config.add_command(label="Exportar Excel", command=exportar_excel)
menu_bar.add_cascade(label="Configurações", menu=menu_config)

menu_ajuda = tk.Menu(menu_bar, tearoff=0)
menu_ajuda.add_command(label="Acesso Remoto (AnyDesk)", command=abrir_anydesk)
menu_bar.add_cascade(label="Ajuda", menu=menu_ajuda)


# (filtros, botões organizados com labels identificadores, etc.)

frame_filtros = ctk.CTkFrame(app)
frame_filtros.pack(padx=10, pady=10, fill="x")

# LINHA 1: Data Inicial e Data Final (TOPO AGORA)
linha_datas = ctk.CTkFrame(frame_filtros)
linha_datas.pack(fill="x", pady=2)

frame_datas = ctk.CTkFrame(linha_datas)
frame_datas.pack(side="left", padx=5)

lbl_data_ini = ctk.CTkLabel(frame_datas, text="Data Inicial:")
lbl_data_ini.grid(row=0, column=0, padx=5, pady=2)

filtro_data_ini = DateEntry(frame_datas, date_pattern='dd/mm/yyyy')
filtro_data_ini.set_date(datetime.today().replace(day=1))
filtro_data_ini.grid(row=1, column=0, padx=5, pady=2)

lbl_data_fim = ctk.CTkLabel(frame_datas, text="Data Final:")
lbl_data_fim.grid(row=0, column=1, padx=5, pady=2)

filtro_data_fim = DateEntry(frame_datas, date_pattern='dd/mm/yyyy')
filtro_data_fim.set_date(datetime.today())
filtro_data_fim.grid(row=1, column=1, padx=5, pady=2)

# LINHA 2: Filtro modelo + Tipo Doc + Situação
linha_filtros = ctk.CTkFrame(frame_filtros)
linha_filtros.pack(fill="x", pady=2)

# -- Filtro MODELO com lupa ao lado
# -- Filtro MODELO com lupa e botão de limpar
frame_quebra = ctk.CTkFrame(linha_filtros)
frame_quebra.pack(side="left", padx=5)

lbl_filtro = ctk.CTkLabel(frame_quebra, text="SELECIONE O MODELO:")
lbl_filtro.grid(row=0, column=0, sticky="w", columnspan=4)

campo_filtro = ttk.Combobox(frame_quebra, values=["Tipo", "Cliente", "Produto", "Forma Pagamento"], state="readonly", width=18)
campo_filtro.set("Tipo")
campo_filtro.grid(row=1, column=0, padx=(0, 5), pady=2)

valor_filtro_texto = ctk.CTkEntry(frame_quebra, placeholder_text="Digite para filtrar", width=180)
valor_filtro_texto.grid(row=1, column=1, padx=(0, 5))

# Botão de lupa
btn_lupa = ctk.CTkButton(frame_quebra, text="🔍", width=35, command=lambda: acionar_lupa(valor_filtro_texto))
btn_lupa.grid(row=1, column=2, padx=(0, 5))

# Botão de limpar campo
btn_limpar = ctk.CTkButton(frame_quebra, text="❌", width=35, fg_color="gray", command=lambda: valor_filtro_texto.delete(0, tk.END))
btn_limpar.grid(row=1, column=3, padx=(0, 5))


# -- Tipo Doc + Situação (direita)
frame_tipo_situacao = ctk.CTkFrame(linha_filtros)
frame_tipo_situacao.pack(side="right", padx=5)

lbl_tipo_doc = ctk.CTkLabel(frame_tipo_situacao, text="Tipo de Documento:")
lbl_tipo_doc.grid(row=0, column=0, padx=5, pady=2)

campo_tipo_doc = ttk.Combobox(frame_tipo_situacao, values=["Todos", "PDV", "OS", "NFCE", "NFE"], state="readonly", width=15)
campo_tipo_doc.set("Todos")
campo_tipo_doc.grid(row=1, column=0, padx=5, pady=2)

lbl_situacao = ctk.CTkLabel(frame_tipo_situacao, text="Situação:")
lbl_situacao.grid(row=0, column=1, padx=5, pady=2)

campo_situacao = ttk.Combobox(frame_tipo_situacao, values=["Todos", "Emitidos",  "Cancelados", "Fechados"], state="readonly", width=15)
campo_situacao.set("Todos")
campo_situacao.grid(row=1, column=1, padx=5, pady=2)


# Linha de botões
frame_botoes = ctk.CTkFrame(app)
frame_botoes.pack(padx=10, pady=0, fill="x")

# Botão SAIR (à direita, permanece igual)
btn_sair = ctk.CTkButton(frame_botoes, text="❌ Sair", text_color="white", fg_color="red", command=app.destroy)
btn_sair.pack(side="right", padx=5, pady=5)

# Botão FILTRAR (à esquerda)
btn_filtrar = ctk.CTkButton(frame_botoes, text="Filtrar", command=carregar_dados)
btn_filtrar.pack(side="left", padx=5, pady=5)

# Botão GERAR MODELO (centralizado)
btn_pdf = ctk.CTkButton(frame_botoes, text="GERAR MODELO", command=gerar_pdf_preview)
btn_pdf.pack(pady=5)  # remove side=left

... # (continua com a Treeview e demais elementos)


colunas = ("Produto", "Tipo", "Preço Unitário", "Quantidade", "Cliente", "Situação")
tree = ttk.Treeview(app, columns=colunas, show="headings")
for col in colunas:
    tree.heading(col, text=col)
    tree.column(col, width=140)
tree.pack(padx=10, pady=(10, 0), fill="both", expand=True)

lbl_total = ctk.CTkLabel(app, text="Total Geral: R$ 0,00", font=("Arial", 16, "bold"))
lbl_total.pack(pady=10)

app.mainloop()