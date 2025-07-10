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


# Conectar ao banco MySQL
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


# Carregar dados com filtros
def carregar_dados():
    conexao = conectar_banco()
    if not conexao:
        return

    cursor = conexao.cursor(dictionary=True)

    query = "SELECT nomeProduto, tipo, vlrUnitario, quantidade, usuario, dataMov FROM movdocs WHERE 1=1"
    valores = []

    if filtro_nome.get():
        query += " AND nomeProduto LIKE %s"
        valores.append(f"%{filtro_nome.get()}%")
    if filtro_categoria.get():
        query += " AND tipo LIKE %s"
        valores.append(f"%{filtro_categoria.get()}%")
    if filtro_cliente.get():
        query += " AND usuario LIKE %s"
        valores.append(f"%{filtro_cliente.get()}%")
    if filtro_data_ini.get_date() and filtro_data_fim.get_date():
        # Converte para formato MySQL yyyy-mm-dd
        data_ini = filtro_data_ini.get_date().strftime('%Y-%m-%d')
        data_fim = filtro_data_fim.get_date().strftime('%Y-%m-%d')
        query += " AND dataMov BETWEEN %s AND %s"
        valores.append(data_ini)
        valores.append(data_fim)

    cursor.execute(query, valores)
    resultados = cursor.fetchall()
    conexao.close()

    if not resultados:
        messagebox.showinfo("Sem resultados", "Nenhum dado encontrado para os filtros aplicados.")

    atualizar_treeview(resultados)


# Atualizar Treeview e total
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


# Exportar para Excel (igual ao seu original, sem alterações)
def exportar_excel():
    if not tree.get_children():
        messagebox.showwarning("Aviso", "Não há dados para exportar.")
        return

    desktop = Path.home() / "Desktop"
    nome_arquivo = desktop / f"relatorio_vendas_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Relatório de Vendas"

    # Cabeçalhos
    colunas = ("Produto", "Categoria", "Preço Unitário", "Quantidade", "Cliente")
    ws.append(colunas)

    total = 0
    # Linhas
    for item in tree.get_children():
        valores = tree.item(item)["values"]
        preco = float(valores[2])
        qtd = float(valores[3])
        total += preco * qtd
        ws.append(valores)

    # Total no final
    ws.append([])
    ws.append(["", "", "", "TOTAL GERAL:", total])

    try:
        wb.save(nome_arquivo)
        messagebox.showinfo("Exportado", f"Arquivo salvo em:\n{nome_arquivo}")
    except Exception as e:
        messagebox.showerror("Erro ao salvar", str(e))


# Gerar PDF e abrir com visualizador padrão Windows (igual ao seu original)
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


# Interface gráfica
ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

app = ctk.CTk()
app.title("Relatório de Vendas - Sistema")
app.geometry("1100x650")

frame_filtros = ctk.CTkFrame(app)
frame_filtros.pack(padx=10, pady=10, fill="x")

# Importante: definir o mês atual para os DateEntry
hoje = datetime.today()
primeiro_dia = hoje.replace(day=1)
ultimo_dia_num = calendar.monthrange(hoje.year, hoje.month)[1]
ultimo_dia = hoje.replace(day=ultimo_dia_num)

# Filtros
filtro_nome = ctk.CTkEntry(frame_filtros, placeholder_text="Nome do Produto")
filtro_nome.grid(row=0, column=0, padx=5, pady=5)

filtro_categoria = ctk.CTkEntry(frame_filtros, placeholder_text="Categoria")
filtro_categoria.grid(row=0, column=1, padx=5, pady=5)

filtro_cliente = ctk.CTkEntry(frame_filtros, placeholder_text="Cliente / Usuário")
filtro_cliente.grid(row=0, column=2, padx=5, pady=5)

filtro_data_ini = DateEntry(frame_filtros, date_pattern='dd/mm/yyyy')
filtro_data_ini.set_date(primeiro_dia)
filtro_data_ini.grid(row=0, column=3, padx=5, pady=5)

filtro_data_fim = DateEntry(frame_filtros, date_pattern='dd/mm/yyyy')
filtro_data_fim.set_date(ultimo_dia)
filtro_data_fim.grid(row=0, column=4, padx=5, pady=5)

btn_filtrar = ctk.CTkButton(frame_filtros, text="Filtrar", command=carregar_dados)
btn_filtrar.grid(row=0, column=5, padx=5, pady=5)

btn_exportar = ctk.CTkButton(frame_filtros, text="Exportar Excel", command=exportar_excel)
btn_exportar.grid(row=0, column=6, padx=5, pady=5)

btn_pdf = ctk.CTkButton(frame_filtros, text="Visualizar PDF", command=gerar_pdf_preview)
btn_pdf.grid(row=0, column=7, padx=5, pady=5)

# Tabela
colunas = ("Produto", "Categoria", "Preço Unitário", "Quantidade", "Cliente")
tree = ttk.Treeview(app, columns=colunas, show="headings")
for col in colunas:
    tree.heading(col, text=col)
    tree.column(col, width=150)
tree.pack(padx=10, pady=(10, 0), fill="both", expand=True)

# Total Geral
lbl_total = ctk.CTkLabel(app, text="Total Geral: R$ 0,00", font=("Arial", 16, "bold"))
lbl_total.pack(pady=10)

app.mainloop()
