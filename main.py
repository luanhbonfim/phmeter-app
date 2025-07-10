from datetime import datetime
from database.database_manager import Database
from devices.barcode_reader import BarcodeReader
from devices.phmetro_reader import PhmetroReader

from utils.etiquetas_utils import get_etiquetas, armazenar_etiquetas, zerar_armazenamento
from tkcalendar import DateEntry
import threading

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
        self.data_abate = None
        self.qant_ph_lido = 0
        
        self.valor_ph = None
        self.id_historico_abertura_camara_item = None
        self.etiquetas_lidas = {}
        
        self.phmetro_status_label = None
        self.phmetro_reader = PhmetroReader(callback_status=self.atualizar_status_phmetro)

        self.setup_ui()
        
        self.listen_for_db_updates()
            
    def setup_ui(self):
        self.root.grid_rowconfigure(0, weight=0)  # Linha superior (topo)
        self.root.grid_rowconfigure(1, weight=1)  # Linha centralizada para PH
        self.root.grid_rowconfigure(2, weight=0)  # Linha inferior (vazio)
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_columnconfigure(1, weight=4)

       # ✅ Painel esquerdo (LEFT FRAME) com PH enxuto e botões Confirmar/Cancelar
        self.left_frame = tk.Frame(self.root)
        self.left_frame.grid(row=0, column=0, rowspan=3, sticky="nsew", padx=10, pady=5)

        # Configuração das linhas (sem dar peso especial a nenhuma)
        for i in range(14):  # 0 a 13 (linhas adicionais para os novos botões)
            self.left_frame.grid_rowconfigure(i, weight=0)

        # Título
        tk.Label(self.left_frame, text="Funções", font=('Arial', 14, 'bold')).grid(row=0, column=0, pady=5, sticky="w")

        # Status Phmetro
        self.phmetro_status_label = tk.Label(self.left_frame, text="Phmetro: Desconectado", fg="red", font=('Arial', 12, 'bold'))
        self.phmetro_status_label.grid(row=1, column=0, pady=5, sticky="w")
        
        # Status banco footer
        self.db_status_label = tk.Label(self.root, text="Banco de Dados: Desconectado", fg="red", font=('Arial', 8, 'bold'))
        self.db_status_label.grid(row=100, column=0, pady=5, sticky="w")
        
        # Data
        tk.Label(self.left_frame, text="Selecionar Data:").grid(row=2, column=0, pady=5, sticky="w")
        self.date_entry = DateEntry(self.left_frame, date_pattern='dd/mm/yyyy', state="normal")
        self.date_entry.grid(row=3, column=0, pady=5, sticky="ew")

        self.button_selecionar_data = tk.Button(self.left_frame, text="Selecionar Data", command=self.selecionar_data)
        self.button_selecionar_data.grid(row=4, column=0, pady=5, sticky="ew")

        # Câmara
        tk.Label(self.left_frame, text="Selecionar Câmara:").grid(row=5, column=0, pady=5, sticky="w")
        self.combo_camaras = ttk.Combobox(self.left_frame, state="readonly")
        self.combo_camaras.grid(row=6, column=0, pady=5, sticky="ew")

        self.button_selecionar_camara = tk.Button(self.left_frame, text="Selecionar Câmara", command=self.selecionar_camara, state="disabled")
        self.button_selecionar_camara.grid(row=7, column=0, pady=5, sticky="ew")

        # Ativar leitura
        self.button_ativar_leitura = tk.Button(self.left_frame, text="Ativar Leitura de Código de Barras", command=self.toggle_leitura, state="disabled")
        self.button_ativar_leitura.grid(row=8, column=0, pady=5, sticky="ew")

        # Código de Barras
        self.label_codigo_barras = tk.Label(self.left_frame, text="Código de Barras:")
        self.label_codigo_barras.grid(row=9, column=0, pady=5, sticky="w")
        self.label_codigo_barras.grid_remove()

        self.entry_codigo_barras = tk.Entry(self.left_frame)
        self.entry_codigo_barras.grid(row=10, column=0, pady=5, sticky="ew")
        self.entry_codigo_barras.grid_remove()
        self.entry_codigo_barras.bind("<Return>", self.processar_codigo)

        # Frame para leitura de PH e botões
        self.frame_leitura_ph = tk.Frame(self.left_frame)
        self.frame_leitura_ph.grid(row=11, column=0, pady=10, sticky="ew")
        self.frame_leitura_ph.grid_remove()

        # Leitura do PH
        tk.Label(self.frame_leitura_ph, text="Leitura Atual do PH", font=('Arial', 12, 'bold')).grid(row=0, column=0, pady=5, sticky="w")
        self.label_valor_ph_lido = tk.Label(self.frame_leitura_ph, text="--", font=('Arial', 12), fg="blue")
        self.label_valor_ph_lido.grid(row=1, column=0, pady=5, sticky="ew")

        # ✅ Botão Confirmar (verde)
        self.botao_confirmar = tk.Button(self.frame_leitura_ph, text="Confirmar", bg="green", fg="white", command=self.confirmar_ph)
        self.botao_confirmar.grid(row=3, column=0, pady=5, sticky="ew")

        # ✅ Botão Cancelar (vermelho)
        self.botao_cancelar = tk.Button(self.frame_leitura_ph, text="Cancelar", bg="red", fg="white", command=self.cancelar_ph)
        self.botao_cancelar.grid(row=4, column=0, pady=5, sticky="ew")

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
        
        self.label_contador_ph = tk.Label(self.left_frame, text="PHs confirmados: 0", font=('Arial', 10, 'bold'), fg="green")
        self.label_contador_ph.grid(row=13, column=0, pady=10, sticky="sw")
        self.label_contador_ph.grid_remove()
     
     
    def listen_for_db_updates(self):
        """
        Função que executa uma verificação no banco de dados a cada 10 segundos
        e atualiza a interface gráfica com as informações mais recentes.
        """
        threading.Timer(3, self.check_for_db_updates).start()
        
    def check_for_db_updates(self):

        self.atualizar_status_banco()
 
        self.listen_for_db_updates()
    
    def atualizar_status_banco(self):
        if self.db.esta_conectado():
            self.db_status_label.config(text="Banco de Dados: Conectado", fg="green")
        else:
            self.db_status_label.config(text="Banco de Dados: Desconectado", fg="red")
            
    def resetar_informacoes_abate(self):
        # Resetar os labels de informações do abate
        self.label_id_registro_abate.config(text="ID_REGISTRO_ABATE: ")
        self.label_data_abate.config(text="DATA_ABATE: ")
        self.label_seq_abate.config(text="SEQUENCIA_ABATE: ")
        self.label_banda.config(text="BANDA: ")
        self.valor_ph = None
        self.id_historico_abertura_camara_item = None
        
        # Resetar o label do pH lido
        self.label_valor_ph.config(text="VALOR PH: ")
        self.label_valor_ph_lido.config(text="--")
          
    def confirmar_ph(self):
        if not self.db.esta_conectado():
            self.atualizar_status_banco()
            messagebox.showerror("Erro", "Banco de dados desconectado. Não é possível confirmar o pH.")
            return

        # Verifica se há uma etiqueta lida (se existe um ID válido da carcaça)
        if not self.id_historico_abertura_camara_item:
            messagebox.showwarning("Aviso", "Nenhuma etiqueta foi lida. Não é possível confirmar o pH.")
            return

        try:
            print(self.valor_ph)
            print(self.id_historico_abertura_camara_item)
            self.db.inserir_ph_unica_carcaca(self.id_historico_abertura_camara_item, self.valor_ph)

            armazenar_etiquetas(self.id_historico_abertura_camara_item, self.valor_ph)
            
            self.qant_ph_lido += 1
            self.label_contador_ph.config(text=f"PHs confirmados: {self.qant_ph_lido}")
            self.carregar_carcacas()
            self.resetar_informacoes_abate()
        except Exception as e:
            self.resetar_informacoes_abate()
            self.atualizar_status_banco()
            print(f"Erro ao confirmar pH: {e}")
            messagebox.showerror("Erro ao confirmar pH", str(e))

    def cancelar_ph(self):
        self.valor_ph = None
        self.id_historico_abertura_camara_item = None
        self.label_valor_ph_lido.config(text="--")
        self.label_valor_ph.config(text="VALOR PH: ")
        self.resetar_informacoes_abate()
        
    def ler_ph(self):
        if not self.selected_camara:
            messagebox.showwarning("Aviso", "Selecione uma câmara antes de ler o pH.")
            return

        try:
            valor_ph = self.phmetro_reader.ler_ph()
            if valor_ph is not None:
                self.label_valor_ph_lido.config(text=f"{valor_ph:.2f}")
                self.label_valor_ph.config(text=f"VALOR PH: {valor_ph:.2f}")
                
                self.valor_ph = valor_ph
            else:
                self.label_valor_ph_lido.config(text="--")
        except Exception as e:
            messagebox.showerror("Erro ao ler pH", str(e))
            self.label_valor_ph_lido.config(text="--")
            self.valor_ph = None
            

    
    def limpar_tabelas(self):
        # Limpa as tabelas de carcaças
        self.tree_carcacas_none_ph.delete(*self.tree_carcacas_none_ph.get_children())
        self.tree_carcacas_ph.delete(*self.tree_carcacas_ph.get_children())
             
    def selecionar_data(self):
        data_str = self.date_entry.get()
        try:
            data_obj = datetime.strptime(data_str, "%d/%m/%Y")
            data_formatada = data_obj.strftime("%d/%m/%Y")

            self.combo_camaras.set('')
            self.carregar_camaras(data_formatada)
            self.data_abate = data_formatada
            
            self.qant_ph_lido = 0
            self.label_contador_ph.config(text=f"PHs confirmados: {self.qant_ph_lido}")
            zerar_armazenamento()

            if not self.camaras:
                messagebox.showwarning("Aviso", "Não há câmaras disponíveis para a data selecionada.")
                self.combo_camaras.set('')
                self.limpar_tabelas()
                return

            self.combo_camaras.config(state="readonly")
            self.button_selecionar_camara.config(state="normal")
            self.button_ativar_leitura.config(state="disabled")
            self.label_codigo_barras.grid_remove()
            self.entry_codigo_barras.grid_remove()
            self.frame_leitura_ph.grid_remove()
            self.label_contador_ph.grid_remove() 
            self.button_ativar_leitura.config(text="Ativar Leitura de Código de Barras")
            self.valor_ph = None
            self.id_historico_abertura_camara_item = None
            if self.leitura_ativa:
                self.leitura_ativa = not self.leitura_ativa
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
            self.qant_ph_lido = 0
            self.label_contador_ph.config(text="PHs confirmados: 0")
            zerar_armazenamento()
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
            self.label_codigo_barras.grid()
            self.entry_codigo_barras.grid()
            self.frame_leitura_ph.grid()
            self.label_contador_ph.grid()  # Exibe o contador de PH
            self.button_ativar_leitura.config(text="Desativar Leitura")
        else:
            self.label_codigo_barras.grid_remove()
            self.entry_codigo_barras.grid_remove()
            self.frame_leitura_ph.grid_remove()
            self.label_contador_ph.grid_remove()  # Oculta o contador de PH
            self.button_ativar_leitura.config(text="Ativar Leitura de Código de Barras")
            self.valor_ph = None
            self.id_historico_abertura_camara_item = None


    def processar_codigo(self, event):
        if not self.leitura_ativa:
            return
        
        self.valor_ph = None
        self.id_historico_abertura_camara_item = None

        codigo = self.entry_codigo_barras.get().strip()
        self.entry_codigo_barras.delete(0, tk.END)

        try:
            registro_abate, banda = self.leitor.read(codigo)
            resultados = self.db.buscar_carcaca(registro_abate, banda)
            print(resultados)

            if not resultados:
                messagebox.showerror("Erro", "Etiqueta não encontrada.")
                return

            carcaca = resultados[0]
            camara_real = carcaca["CODIGO_CAMARA"]
            self.id_historico_abertura_camara_item = carcaca["ID_HIST_ABERTURA_CAMARA_ITEM"]

            if str(carcaca["CODIGO_CAMARA"]) != str(self.selected_camara):
                messagebox.showwarning(
                    "Etiqueta Incorreta",
                    f"A etiqueta pertence à câmara {camara_real}, mas a câmara selecionada é {self.selected_camara}."
                )
                return
            
            data_abate_banco = datetime.strptime(str(carcaca["DATA_ABATE"]), "%Y-%m-%d %H:%M:%S").date()
            data_abate_selecionada = datetime.strptime(str(self.data_abate), "%d/%m/%Y").date()

            if data_abate_banco != data_abate_selecionada:
                data_real_formatada = data_abate_banco.strftime("%d/%m/%Y")
                data_selecionada_formatada = data_abate_selecionada.strftime("%d/%m/%Y")

                messagebox.showwarning(
                    "Data Incorreta",
                    f"A etiqueta pertence à data de abate {data_real_formatada} e câmara {camara_real}, "
                    f"mas a data selecionada é {data_selecionada_formatada} e câmara é {self.selected_camara}."
                )
                return

            if carcaca["VALOR_PH"] is not None:
                messagebox.showwarning(
                    "Etiqueta já lida",
                    "Esta carcaça já possui um valor de pH registrado, não é possível realizar a leitura novamente."
                )
                return

            # Atualiza as informações no painel direito
            self.label_id_registro_abate.config(text=f"ID_REGISTRO_ABATE: {carcaca['ID_REGISTRO_ABATE']}")
            self.label_data_abate.config(text=f"DATA_ABATE: {carcaca['DATA_ABATE']}")
            self.label_seq_abate.config(text=f"SEQUENCIA_ABATE: {carcaca['SEQUENCIA_ABATE']}")
            self.label_banda.config(text=f"BANDA: {carcaca['BANDA']}")

            # Ler o pH automaticamente e atualizar o label
            self.ler_ph()

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

    def atualizar_status_phmetro(self, conectado):
        if self.phmetro_status_label:
            status = "Conectado" if conectado else "Desconectado"
            cor = "green" if conectado else "red"
            self.phmetro_status_label.config(text=f"Phmetro: {status}", fg=cor)
        
def main():
    root = tk.Tk()
    app = App(root)
    root.state("zoomed")  # Inicia a janela maximizada
    root.resizable(True, True)  # Permite redimensionamento
    root.mainloop()

if __name__ == "__main__":
    main()
