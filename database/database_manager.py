import oracledb
from datetime import datetime

oracledb.init_oracle_client(lib_dir=r"C:\instantclient")

class Database:
    def __init__(self):
        self.connection = None
        self.is_connected = False

    def connect(self):
        try:
            self.connection = oracledb.connect(
                user="",
                password="",
                dsn=""
            )
            self.is_connected = True
            print("Conexão executada com sucesso.")
        except oracledb.DatabaseError as e:
            self.is_connected = False
            print(f"Erro ao conectar ao banco: {e}")

    def disconnect(self):
        if self.connection:
            try:
                self.connection.close()
                print("Conexão encerrada")
            except Exception as e:
                print(f"Erro ao encerrar conexão: {e}")
            finally:
                self.connection = None
                self.is_connected = False
                
    def esta_conectado(self):
        """Retorna True se a conexão estiver ativa e válida com o banco."""
        if self.connection is None or not self.is_connected:
            return False
        try:
            # Consulta simples para verificar a conexão
            cursor = self.connection.cursor()
            cursor.execute("SELECT SYSDATE FROM DUAL")
            cursor.fetchone()  # Obtém um único resultado
            return True
        except oracledb.DatabaseError:
            self.is_connected = False
            return False
        
    def ensure_connection(self):
        if not self.is_connected:
            print("Tentando reconectar ao banco...")
            self.connect()

    def buscar_camaras(self, data_abate):
        self.ensure_connection()
        if not self.is_connected:
            return []

        sql = """
            SELECT  H.DATA_ABATE,
                    C.CODIGO_CAMARA,
                    C.DESCRICAO
                FROM SIGMA_PEC.HISTORICO_ABERTURA_CAMARA H
                INNER JOIN SIGMA_MAT.CAMARA C
                    ON C.ID_CAMARA = H.ID_CAMARA
                WHERE H.DATA_ABATE = TO_DATE(:data_abate, 'dd/mm/YYYY')
        """
        try:
            cursor = self.connection.cursor()
            cursor.execute(sql, data_abate=data_abate)
            columns = [col[0] for col in cursor.description]
            resultados = [dict(zip(columns, row)) for row in cursor.fetchall()]
            cursor.close()
            return resultados
        except oracledb.DatabaseError as e:
            print(f"Erro ao buscar câmaras: {e}")
            self.is_connected = False
            return []

    def buscar_carcacas_por_camara(self, codigo_camara, data_abate):
        self.ensure_connection()
        if not self.is_connected:
            return []

        sql = """
            SELECT HI.ID_REGISTRO_ABATE,
                HI.VALOR_PH,
                HI.BANDA,
                R.SEQUENCIA_ABATE,
                C.CODIGO_CAMARA
            FROM SIGMA_PEC.HISTORICO_ABERTURA_CAMARA_ITEM HI
            INNER JOIN SIGMA_PEC.HISTORICO_ABERTURA_CAMARA HC
                ON HC.ID_HISTORICO_ABERTURA_CAMARA = HI.ID_HISTORICO_ABERTURA_CAMARA
            INNER JOIN SIGMA_MAT.CAMARA C
                ON C.ID_CAMARA = HC.ID_CAMARA
            INNER JOIN SIGMA_PEC.REGISTRO_ABATE R
                ON R.ID_REGISTRO_ABATE = HI.ID_REGISTRO_ABATE
            WHERE HC.DATA_ABATE = TO_DATE(:data_abate, 'dd/mm/YYYY')
            AND C.CODIGO_CAMARA = :codigo_camara
        """
        try:
            cursor = self.connection.cursor()
            cursor.execute(sql, codigo_camara=codigo_camara, data_abate=data_abate)
            columns = [col[0] for col in cursor.description]
            resultados = [dict(zip(columns, row)) for row in cursor.fetchall()]
            cursor.close()
            return resultados
        except oracledb.DatabaseError as e:
            print(f"Erro ao buscar carcaças: {e}")
            self.is_connected = False
            return []

    def buscar_carcaca(self, registro_abate, banda):
        self.ensure_connection()
        if not self.is_connected:
            return []

        sql = """
            SELECT H.ID_HIST_ABERTURA_CAMARA_ITEM,
                    H.ID_REGISTRO_ABATE,
                    RA.DATA_ABATE,
                    RA.SEQUENCIA_ABATE,
                    H.BANDA,
                    H.VALOR_PH,
                    C.CODIGO_CAMARA
            FROM SIGMA_PEC.HISTORICO_ABERTURA_CAMARA_ITEM H
            INNER JOIN SIGMA_PEC.REGISTRO_ABATE RA ON H.ID_REGISTRO_ABATE = RA.ID_REGISTRO_ABATE
            INNER JOIN SIGMA_PEC.HISTORICO_ABERTURA_CAMARA HC ON HC.ID_HISTORICO_ABERTURA_CAMARA = H.ID_HISTORICO_ABERTURA_CAMARA
            INNER JOIN SIGMA_MAT.CAMARA C ON C.ID_CAMARA = HC.ID_CAMARA
            WHERE H.ID_REGISTRO_ABATE = :registro_abate AND H.BANDA = :banda
        """
        try:
            cursor = self.connection.cursor()
            cursor.execute(sql, registro_abate=registro_abate, banda=banda)
            columns = [col[0] for col in cursor.description]
            resultados = [dict(zip(columns, row)) for row in cursor.fetchall()]
            cursor.close()
            return resultados
        except oracledb.DatabaseError as e:
            print(f"Erro ao buscar carcaça: {e}")
            self.is_connected = False
            return []

    def inserir_ph_unica_carcaca(self, id_historico_abertura_camara_item, valor_ph):
        self.ensure_connection()
        if not self.is_connected:
            print("Banco desconectado. Não foi possível atualizar o pH.")
            return

        sql = """
            UPDATE SIGMA_PEC.HISTORICO_ABERTURA_CAMARA_ITEM UH
                SET UH.VALOR_PH = :VALOR_PH
            WHERE UH.ID_HIST_ABERTURA_CAMARA_ITEM = :ID_HIST_ABERTURA_CAMARA_ITEM
        """
        try:
            cursor = self.connection.cursor()
            cursor.execute(sql, VALOR_PH=valor_ph, ID_HIST_ABERTURA_CAMARA_ITEM=id_historico_abertura_camara_item)
            self.connection.commit()
            print(f"pH atualizado para a carcaça com ID {id_historico_abertura_camara_item}!")
        except oracledb.DatabaseError as e:
            print(f"Erro ao atualizar pH: {e}")
            self.connection.rollback()
            self.is_connected = False
        finally:
            cursor.close()
