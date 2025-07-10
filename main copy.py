from datetime import datetime
from database.database_manager import Database
from devices.barcode_reader import BarcodeReader
from tkcalendar import DateEntry  # Importando o widget de seleção de data

import tkinter as tk
from tkinter import ttk, messagebox, PhotoImage

class App:
    def __init__(self, root):
        self.root = root
        self.root.title("PH Meter App")
        root.iconbitmap("./image/better.ico")
        
        self.db = Database()
        self.db.connect()
        self.leitor = BarcodeReader()

        self.selected_camara = None
        self.leitura_ativa = False

        self.setup_ui()

    def setup_ui(self):
        self.root.grid_rowconfigure(0, weight=1)  # Primeira linha com maior peso
        self.root.grid_rowconfigure(1, weight=4)  # Linha 1 expandindo mais
        self.root.grid_columnconfigure(0, weight=1)  # Coluna 0 com peso 1 (painel esquerdo)
        self.root.grid_columnconfigure(1, weight=4)  # Coluna 1 com peso 4 (painel direito)

        # Painel esquerdo
        self.left_frame = tk.Frame(self.root)
        self.left_frame.grid(row=0, column=0, rowspan=2, sticky="nsew", padx=10, pady=10)
        self.left_frame.grid_rowconfigure(0, weight=1)
        self.left_frame.grid_columnconfigure(0, weight=1)
        
        tk.Label(self.left_frame, text="Funções", font=('Arial', 14, 'bold')).pack(pady=5)

        tk.Label(self.left_frame, text="Selecionar Data:").pack(pady=5)
        self.date_entry = DateEntry(self.left_frame, date_pattern='dd/mm/yyyy', state="normal")  # Caixa de data sem valor inicial
        self.date_entry.pack(pady=5)

        # Botão "Selecionar Data"
        self.button_selecionar_data = tk.Button(self.left_frame, text="Selecionar Data", command=self.selecionar_data)
        self.button_selecionar_data.pack(pady=5)

        tk.Label(self.left_frame, text="Selecionar Câmara:").pack(pady=5)
        self.combo_camaras = ttk.Combobox(self.left_frame, state="disabled")  # Começa desabilitado
        self.combo_camaras.pack(pady=5)

        self.button_selecionar_camara = tk.Button(self.left_frame, text="Selecionar Câmara", command=self.selecionar_camara, state="disabled")
        self.button_selecionar_camara.pack(pady=5)

        self.button_ativar_leitura = tk.Button(self.left_frame, text="Ativar Leitura de Código de Barras", command=self.toggle_leitura, state="disabled")
        self.button_ativar_leitura.pack(pady=5)

        self.label_codigo_barras = tk.Label(self.left_frame, text="Código de Barras:")
        self.label_codigo_barras.pack()  # Adiciona o label à tela
        self.label_codigo_barras.pack_forget()  # Esconde o label
        self.entry_codigo_barras = tk.Entry(self.left_frame)
        self.entry_codigo_barras.pack(pady=5)
        self.entry_codigo_barras.pack_forget()
        self.entry_codigo_barras.bind("<Return>", self.processar_codigo)

        # Painel direito
        self.right_frame = tk.Frame(self.root)
        self.right_frame.grid(row=0, column=1, rowspan=2, sticky="nsew", padx=10, pady=10)
        self.right_frame.grid_rowconfigure(0, weight=1)
        self.right_frame.grid_columnconfigure(0, weight=1)
        self.right_frame.grid_columnconfigure(1, weight=1)

        # Informações do abate
        self.info_abate_frame = tk.Frame(self.right_frame)
        self.info_abate_frame.pack(fill="x", pady=5)

        tk.Label(self.info_abate_frame, text="Informações do Abate", font=('Arial', 12, 'bold')).pack(anchor="w")
        self.label_id_registro_abate = tk.Label(self.info_abate_frame, text="ID_REGISTRO_ABATE: ")
        self.label_data_abate = tk.Label(self.info_abate_frame, text="DATA_ABATE: ")
        self.label_seq_abate = tk.Label(self.info_abate_frame, text="SEQUENCIA_ABATE: ")
        self.label_banda = tk.Label(self.info_abate_frame, text="BANDA: ")
        self.label_valor_ph = tk.Label(self.info_abate_frame, text="VALOR_PH: ")

        for lbl in [self.label_id_registro_abate, self.label_data_abate, self.label_seq_abate, self.label_banda, self.label_valor_ph]:
            lbl.pack(anchor="w")

        # Tabelas
        tabelas_frame = tk.Frame(self.right_frame)
        tabelas_frame.pack(fill="both", expand=True)

        self.tree_carcacas_none_ph_label = tk.Label(tabelas_frame, text="Carcaças com PH None", font=('Arial', 12, 'bold'))
        self.tree_carcacas_none_ph_label.grid(row=0, column=0, padx=10, pady=5)

        self.tree_carcacas_none_ph = ttk.Treeview(tabelas_frame, columns=("ID_REGISTRO_ABATE", "VALOR_PH", "BANDA", "SEQUENCIA_ABATE", "CODIGO_CAMARA"), show="headings")
        for col in self.tree_carcacas_none_ph["columns"]:
            self.tree_carcacas_none_ph.heading(col, text=col.replace("_", " ").title())
            self.tree_carcacas_none_ph.column(col, width=100)
        self.tree_carcacas_none_ph.grid(row=1, column=0, padx=10, pady=5, sticky="nsew")

        self.tree_carcacas_ph_label = tk.Label(tabelas_frame, text="Carcaças com PH", font=('Arial', 12, 'bold'))
        self.tree_carcacas_ph_label.grid(row=0, column=1, padx=10, pady=5)

        self.tree_carcacas_ph = ttk.Treeview(tabelas_frame, columns=("ID_REGISTRO_ABATE", "VALOR_PH", "BANDA", "SEQUENCIA_ABATE", "CODIGO_CAMARA"), show="headings")
        for col in self.tree_carcacas_ph["columns"]:
            self.tree_carcacas_ph.heading(col, text=col.replace("_", " ").title())
            self.tree_carcacas_ph.column(col, width=100)
        self.tree_carcacas_ph.grid(row=1, column=1, padx=10, pady=5, sticky="nsew")

        tabelas_frame.grid_rowconfigure(1, weight=1)
        tabelas_frame.grid_columnconfigure(0, weight=1)
        tabelas_frame.grid_columnconfigure(1, weight=1)
        
    def limpar_tabelas(self):
        # Limpa as tabelas de carcaças
        self.tree_carcacas_none_ph.delete(*self.tree_carcacas_none_ph.get_children())
        self.tree_carcacas_ph.delete(*self.tree_carcacas_ph.get_children())
            
    def selecionar_data(self):
        data_str = self.date_entry.get()
        try:
            data_obj = datetime.strptime(data_str, "%d/%m/%Y")
            data_formatada = data_obj.strftime("%d/%m/%Y")  # <- formato dd/mm/yyyy para Oracle

            self.combo_camaras.set('')
            self.carregar_camaras(data_formatada)

            if not self.camaras:
                messagebox.showwarning("Aviso", "Não há câmaras disponíveis para a data selecionada.")
                self.combo_camaras.set('')
                self.limpar_tabelas()
                return

            self.combo_camaras.config(state="normal")
            self.button_selecionar_camara.config(state="normal")
            self.button_ativar_leitura.config(state="disabled")
            self.entry_codigo_barras.pack_forget()
            self.label_codigo_barras.pack_forget()
            self.button_ativar_leitura.config(text="Ativar Leitura de Código de Barras")
            self.limpar_tabelas()

        except ValueError:
            messagebox.showerror("Erro", "Data inválida. Use o formato dd/mm/aaaa.")
            self.combo_camaras.set('')
            self.limpar_tabelas()
            self.combo_camaras.config(state="disabled")
            self.button_selecionar_camara.config(state="disabled")

    def carregar_camaras(self, data_selecionada):
        self.camaras = self.db.buscar_camaras(data_selecionada)
        self.combo_camaras['values'] = [f"{c['CODIGO_CAMARA']}" for c in self.camaras]

    def selecionar_camara(self):
        camara = self.combo_camaras.get()  # Obtém a câmara selecionada
        if camara:
            self.selected_camara = camara
            self.carregar_carcacas()  # Carrega as carcaças da câmara selecionada
            
            if not self.tree_carcacas_none_ph.get_children() and not self.tree_carcacas_ph.get_children():
                # Verifica se não há carcaças (etiquetas) nas tabelas
                messagebox.showwarning("Aviso", f"Não há etiquetas (carcaças) disponíveis para a câmara {self.selected_camara}.")
                return
            
            self.button_ativar_leitura.config(state="normal")  # Ativa o botão de leitura
        else:
            messagebox.showwarning("Aviso", "Selecione uma câmara.")
            self.selected_camara = None
            self.button_ativar_leitura.config(state="disabled")  # Desativa o botão de leitura

    def carregar_carcacas(self):
        self.tree_carcacas_none_ph.delete(*self.tree_carcacas_none_ph.get_children())
        self.tree_carcacas_ph.delete(*self.tree_carcacas_ph.get_children())

        data_selecionada = self.date_entry.get()  # Pegando a data selecionada
        carcacas = self.db.buscar_carcacas_por_camara(self.selected_camara, data_selecionada)

        for c in carcacas:
            tree = self.tree_carcacas_none_ph if c.get('VALOR_PH') is None else self.tree_carcacas_ph
            tree.insert("", "end", values=(c.get('ID_REGISTRO_ABATE', ''),
                                          c.get('VALOR_PH', ''),
                                          c.get('BANDA', ''),
                                          c.get('SEQUENCIA_ABATE', ''),
                                          c.get('CODIGO_CAMARA', '')))

    def toggle_leitura(self):
        if not self.selected_camara:
            messagebox.showwarning("Aviso", "Selecione uma câmara primeiro.")
            return

        self.leitura_ativa = not self.leitura_ativa
        if self.leitura_ativa:
            self.label_codigo_barras.pack(pady=5) 
            self.entry_codigo_barras.pack(pady=5)
            self.button_ativar_leitura.config(text="Desativar Leitura")
        else:
            self.label_codigo_barras.pack_forget() 
            self.entry_codigo_barras.pack_forget()
            self.button_ativar_leitura.config(text="Ativar Leitura de Código de Barras")

    def processar_codigo(self, event):
        if not self.leitura_ativa:
            return

        codigo = self.entry_codigo_barras.get().strip()
        self.entry_codigo_barras.delete(0, tk.END)

        try:
            registro_abate, banda = self.leitor.read(codigo)
            resultados = self.db.buscar_carcaca(registro_abate, banda)

            if not resultados:
                messagebox.showerror("Erro", "Etiqueta não encontrada.")
                return

            carcaca = resultados[0]
            
            # Verifica se a carcaça pertence à câmara selecionada
            if str(carcaca["CODIGO_CAMARA"]) != str(self.selected_camara):
                camara_real = carcaca["CODIGO_CAMARA"]
                messagebox.showwarning(
                    "Etiqueta Incorreta",
                    f"A etiqueta pertence à câmara {camara_real}, mas a câmara selecionada é {self.selected_camara}."
                )
                return
            
            # Verifica se a carcaça já possui um valor de pH
            if carcaca["VALOR_PH"] is not None:
                messagebox.showwarning(
                    "Etiqueta já lida",
                    "Esta carcaça já possui um valor de pH registrado, não é possível realizar a leitura novamente."
                )
                return

            # Atualiza as informações de abate caso tudo esteja correto
            self.atualizar_info_abate(carcaca)

        except Exception as e:
            messagebox.showerror("Erro", str(e))

    def atualizar_info_abate(self, c):
        self.label_id_registro_abate.config(text=f"ID_REGISTRO_ABATE: {c.get('ID_REGISTRO_ABATE', '')}")
        self.label_data_abate.config(text=f"DATA_ABATE: {c.get('DATA_ABATE', '')}")
        self.label_seq_abate.config(text=f"SEQUENCIA_ABATE: {c.get('SEQUENCIA_ABATE', '')}")
        self.label_banda.config(text=f"BANDA: {c.get('BANDA', '')}")
        self.label_valor_ph.config(text=f"VALOR_PH: {c.get('VALOR_PH', '')}")

    def close(self):
        self.db.disconnect()
        self.root.destroy()

def main():
    root = tk.Tk()
    app = App(root)
    root.state("zoomed")  # Inicia a janela maximizada
    root.resizable(True, True)  # Permite redimensionamento
    root.mainloop()

if __name__ == "__main__":
    main()
