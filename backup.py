import customtkinter as ctk
import tkinter as tk
from tkinter import ttk, messagebox
from tkcalendar import DateEntry
import mysql.connector
import openpyxl
from pathlib import Path
from datetime import datetime
import calendar
import tempfile
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
import os

def conectar_banco():
    try:
        conexao = mysql.connector.connect(
            host="localhost",
            user="root",
            password="mysql147",
            database="sistema"
        )
        return conexao
    except mysql.connector.Error as e:
        messagebox.showerror("Erro de conexão", str(e))
        return None

def carregar_categorias():
    try:
        conn = conectar_banco()
        cursor = conn.cursor()
        cursor.execute("SELECT nomeCategoria FROM categorias ORDER BY nomeCategoria")
        categorias = [row[0] for row in cursor.fetchall()]
        conn.close()
        return ["TODOS"] + categorias
    except:
        return ["TODOS"]

def carregar_dados():
    conexao = conectar_banco()
    if not conexao:
        return

    cursor = conexao.cursor(dictionary=True)

    query = """
        SELECT 
            m.nomeProduto, 
            c.nomeCategoria AS tipo, 
            m.vlrUnitario, 
            m.quantidade, 
            m.usuario, 
            m.dataMov 
        FROM 
            movdocs m
        JOIN 
            produtos p ON m.nomeProduto = p.nomeProduto
        JOIN 
            categorias c ON p.idCategoria = c.id
        WHERE 
            1=1
    """
    valores = []

    if filtro_nome.get():
        query += " AND m.nomeProduto LIKE %s"
        valores.append(f"%{filtro_nome.get()}%")
    if filtro_categoria.get() and filtro_categoria.get() != "TODOS":
        query += " AND c.nomeCategoria = %s"
        valores.append(filtro_categoria.get())
    if filtro_cliente.get():
        query += " AND m.usuario LIKE %s"
        valores.append(f"%{filtro_cliente.get()}%")
    if filtro_data_ini.get_date() and filtro_data_fim.get_date():
        data_ini = filtro_data_ini.get_date().strftime('%Y-%m-%d')
        data_fim = filtro_data_fim.get_date().strftime('%Y-%m-%d')
        query += " AND m.dataMov BETWEEN %s AND %s"
        valores.append(data_ini)
        valores.append(data_fim)
    if filtro_situacao.get() != "TODOS":
        query += " AND m.situacao = %s"
        valores.append(filtro_situacao.get())

    try:
        cursor.execute(query, valores)
        resultados = cursor.fetchall()
        conexao.close()

        if not resultados:
            messagebox.showinfo("Sem resultados", "Nenhum dado encontrado para os filtros aplicados.")

        atualizar_treeview(resultados)

    except Exception as e:
        messagebox.showerror("Erro na consulta", str(e))
        conexao.close()

def atualizar_treeview(registros):
    for item in tree.get_children():
        tree.delete(item)

    total = 0
    for row in registros:
        valor_total = float(row["vlrUnitario"]) * float(row["quantidade"])
        total += valor_total
        tree.insert("", "end", values=(
            row["nomeProduto"], row["tipo"], row["vlrUnitario"],
            row["quantidade"], row["usuario"]
        ))

    lbl_total.configure(text=f"Total Geral: R$ {total:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

def exportar_excel():
    if not tree.get_children():
        messagebox.showwarning("Aviso", "Não há dados para exportar.")
        return

    desktop = Path.home() / "Desktop"
    nome_arquivo = desktop / f"relatorio_vendas_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Relatório de Vendas"

    colunas = ("Produto", "Categoria", "Preço Unitário", "Quantidade", "Cliente")
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

def gerar_pdf_preview():
    dados = []
    for item in tree.get_children():
        valores = tree.item(item)["values"]
        dados.append(valores)

    if not dados:
        messagebox.showwarning("PDF vazio", "Nenhum dado visível para gerar PDF.")
        return

    temp_pdf = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    c = canvas.Canvas(temp_pdf.name, pagesize=A4)
    width, height = A4

    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(width / 2, height - 40, "RELATÓRIO DE VENDAS")

    y = height - 80
    c.setFont("Helvetica-Bold", 10)
    c.drawString(40, y, "Produto")
    c.drawString(180, y, "Categoria")
    c.drawString(280, y, "Preço Unit.")
    c.drawString(360, y, "Quantidade")
    c.drawString(440, y, "Cliente")
    y -= 20

    c.setFont("Helvetica", 10)
    total = 0
    for linha in dados:
        nome, categoria, preco, qtd, cliente = linha
        preco = float(preco)
        qtd = float(qtd)
        total += preco * qtd

        if y < 50:
            c.showPage()
            y = height - 80
            c.setFont("Helvetica-Bold", 10)
            c.drawString(40, y, "Produto")
            c.drawString(180, y, "Categoria")
            c.drawString(280, y, "Preço Unit.")
            c.drawString(360, y, "Quantidade")
            c.drawString(440, y, "Cliente")
            y -= 20
            c.setFont("Helvetica", 10)

        c.drawString(40, y, str(nome)[:25])
        c.drawString(180, y, str(categoria)[:15])
        c.drawString(280, y, f"R$ {preco:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
        c.drawString(370, y, str(qtd))
        c.drawString(440, y, str(cliente)[:20])
        y -= 15

    y -= 20
    c.setFont("Helvetica-Bold", 12)
    c.drawString(40, y, f"TOTAL GERAL: R$ {total:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

    c.save()
    temp_pdf.close()

    os.startfile(temp_pdf.name)

ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

app = ctk.CTk()
app.title("Relatório de Vendas - Sistema")
app.geometry("1150x700")

frame_filtros = ctk.CTkFrame(app)
frame_filtros.pack(padx=10, pady=10, fill="x")

hoje = datetime.today()
primeiro_dia = hoje.replace(day=1)
ultimo_dia = hoje.replace(day=calendar.monthrange(hoje.year, hoje.month)[1])

filtro_nome = ctk.CTkEntry(frame_filtros, placeholder_text="Nome do Produto")
filtro_nome.grid(row=0, column=0, padx=5, pady=5)

filtro_categoria = ctk.CTkComboBox(frame_filtros, values=carregar_categorias())
filtro_categoria.set("TODOS")
filtro_categoria.grid(row=0, column=1, padx=5, pady=5)

filtro_cliente = ctk.CTkEntry(frame_filtros, placeholder_text="Cliente / Usuário")
filtro_cliente.grid(row=0, column=2, padx=5, pady=5)

filtro_data_ini = DateEntry(frame_filtros, date_pattern='dd/mm/yyyy')
filtro_data_ini.set_date(primeiro_dia)
filtro_data_ini.grid(row=0, column=3, padx=5, pady=5)

filtro_data_fim = DateEntry(frame_filtros, date_pattern='dd/mm/yyyy')
filtro_data_fim.set_date(ultimo_dia)
filtro_data_fim.grid(row=0, column=4, padx=5, pady=5)

filtro_situacao = ctk.CTkComboBox(frame_filtros, values=["TODOS", "ABERTO", "FECHADO", "CANCELADO"])
filtro_situacao.set("TODOS")
filtro_situacao.grid(row=0, column=5, padx=5, pady=5)

btn_filtrar = ctk.CTkButton(frame_filtros, text="Filtrar", command=carregar_dados)
btn_filtrar.grid(row=0, column=6, padx=5, pady=5)

btn_exportar = ctk.CTkButton(frame_filtros, text="Exportar Excel", command=exportar_excel)
btn_exportar.grid(row=0, column=7, padx=5, pady=5)

btn_pdf = ctk.CTkButton(frame_filtros, text="Visualizar PDF", command=gerar_pdf_preview)
btn_pdf.grid(row=0, column=8, padx=5, pady=5)

colunas = ("Produto", "Categoria", "Preço Unitário", "Quantidade", "Cliente")
tree = ttk.Treeview(app, columns=colunas, show="headings")
for col in colunas:
    tree.heading(col, text=col)
    tree.column(col, width=150)
tree.pack(padx=10, pady=(10, 0), fill="both", expand=True)

lbl_total = ctk.CTkLabel(app, text="Total Geral: R$ 0,00", font=("Arial", 16, "bold"))
lbl_total.pack(pady=10)

app.mainloop()
