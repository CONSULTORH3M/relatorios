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

def escolher_modelo():
    arquivo = filedialog.askopenfilename(title="Selecionar modelo de impressão", filetypes=[("Todos arquivos", "*.*")])
    if arquivo:
        config = carregar_configuracoes()
        config["modelo"] = arquivo
        salvar_configuracoes(config)
        messagebox.showinfo("Salvo", f"Modelo salvo:\n{arquivo}")

def exportar_excel():
    if not tree.get_children():
        messagebox.showwarning("Aviso", "Não há dados para exportar.")
        return

    desktop = Path.home() / "Desktop"
    nome_arquivo = desktop / f"relatorio_vendas_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Relatório de Vendas"

    colunas = ("Produto", "Categoria", "Preço Unitário", "Quantidade", "Cliente", "Situação")
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
            m.nomeProduto, m.tipo, m.vlrUnitario, m.quantidade, m.usuario, m.dataMov, m.situacao, d.tipoDoc
        FROM 
            movdocs m
        JOIN 
            docs d ON m.idDoc = d.id
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
        if filtro_selecionado == "Categoria":
            query += " AND m.tipo LIKE %s"
            valores.append(f"%{filtro}%")
        elif filtro_selecionado == "Cliente":
            query += " AND m.usuario LIKE %s"
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
    if situacao == "Abertos":
        query += " AND m.situacao = 'ABERTO'"
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
            row["quantidade"], row["usuario"], row["situacao"]
        ))

    lbl_total.configure(text=f"Total Geral: R$ {total:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

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
        nome, categoria, preco, qtd, cliente, _ = linha
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

# Interface
ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")
app = ctk.CTk()
app.title("Relatório de Vendas - Sistema")
app.geometry("1150x700")

menu_bar = tk.Menu(app)
app.configure(menu=menu_bar)

menu_config = tk.Menu(menu_bar, tearoff=0)
menu_config.add_command(label="Definir Impressora...", command=definir_impressora)
menu_config.add_command(label="Selecionar Modelo de Impressão...", command=escolher_modelo)
menu_config.add_command(label="Exportar Excel", command=exportar_excel)
menu_bar.add_cascade(label="Configurações", menu=menu_config)

menu_ajuda = tk.Menu(menu_bar, tearoff=0)
menu_ajuda.add_command(label="Acesso Remoto (AnyDesk)", command=abrir_anydesk)
menu_bar.add_cascade(label="Ajuda", menu=menu_ajuda)

# Continue interface setup below...
# (filtros, botões organizados com labels identificadores, etc.)

... # (trecho anterior do código permanece o mesmo)

frame_filtros = ctk.CTkFrame(app)
frame_filtros.pack(padx=10, pady=10, fill="x")

# Primeira linha de filtros (coluna esquerda)
filtro_esquerda = ctk.CTkFrame(frame_filtros)
filtro_esquerda.grid(row=0, column=0, sticky="w")

lbl_filtro = ctk.CTkLabel(filtro_esquerda, text="Quebrar por:")
lbl_filtro.grid(row=0, column=0, padx=5, pady=2)

campo_filtro = ttk.Combobox(filtro_esquerda, values=["Categoria", "Cliente", "Produto", "Forma Pagamento"], state="readonly", width=18)
campo_filtro.set("Categoria")
campo_filtro.grid(row=1, column=0, padx=5, pady=2)

valor_filtro_texto = ctk.CTkEntry(filtro_esquerda, placeholder_text="Digite para filtrar", width=180)
valor_filtro_texto.grid(row=1, column=1, padx=5, pady=2)

# Segunda linha de filtros (coluna direita)
filtro_direita = ctk.CTkFrame(frame_filtros)
filtro_direita.grid(row=0, column=1, sticky="w")

lbl_tipo_doc = ctk.CTkLabel(filtro_direita, text="Tipo de Documento:")
lbl_tipo_doc.grid(row=0, column=0, padx=5, pady=2)

campo_tipo_doc = ttk.Combobox(filtro_direita, values=["Todos", "PDV", "OS", "NFCE", "NFE"], state="readonly", width=15)
campo_tipo_doc.set("Todos")
campo_tipo_doc.grid(row=1, column=0, padx=5, pady=2)

lbl_situacao = ctk.CTkLabel(filtro_direita, text="Situação:")
lbl_situacao.grid(row=0, column=1, padx=5, pady=2)

campo_situacao = ttk.Combobox(filtro_direita, values=["Todos", "Abertos", "Fechados"], state="readonly", width=15)
campo_situacao.set("Todos")
campo_situacao.grid(row=1, column=1, padx=5, pady=2)

# Filtros de data visíveis permanentemente
lbl_data_ini = ctk.CTkLabel(frame_filtros, text="Data Inicial:")
lbl_data_ini.grid(row=1, column=0, sticky="w", padx=5)

filtro_data_ini = DateEntry(frame_filtros, date_pattern='dd/mm/yyyy')
filtro_data_ini.set_date(datetime.today().replace(day=1))
filtro_data_ini.grid(row=1, column=0, sticky="w", padx=100)

lbl_data_fim = ctk.CTkLabel(frame_filtros, text="Data Final:")
lbl_data_fim.grid(row=1, column=1, sticky="w", padx=5)

filtro_data_fim = DateEntry(frame_filtros, date_pattern='dd/mm/yyyy')
filtro_data_fim.set_date(datetime.today())
filtro_data_fim.grid(row=1, column=1, sticky="w", padx=100)

# Linha de botões
frame_botoes = ctk.CTkFrame(app)
frame_botoes.pack(padx=10, pady=0, fill="x")

btn_filtrar = ctk.CTkButton(frame_botoes, text="Filtrar", command=carregar_dados)
btn_filtrar.pack(side="left", padx=5, pady=5)

btn_pdf = ctk.CTkButton(frame_botoes, text="Visualizar PDF", command=gerar_pdf_preview)
btn_pdf.pack(side="left", padx=5, pady=5)

btn_sair = ctk.CTkButton(frame_botoes, text="❌ Sair", text_color="white", fg_color="red", command=app.destroy)
btn_sair.pack(side="right", padx=5, pady=5)

... # (continua com a Treeview e demais elementos)


colunas = ("Produto", "Categoria", "Preço Unitário", "Quantidade", "Cliente", "Situação")
tree = ttk.Treeview(app, columns=colunas, show="headings")
for col in colunas:
    tree.heading(col, text=col)
    tree.column(col, width=140)
tree.pack(padx=10, pady=(10, 0), fill="both", expand=True)

lbl_total = ctk.CTkLabel(app, text="Total Geral: R$ 0,00", font=("Arial", 16, "bold"))
lbl_total.pack(pady=10)

app.mainloop()