import serial
import serial.tools.list_ports
import threading
import time
import re


class PhmetroReader:
    def __init__(self, callback_status=None):
        self.callback_status = callback_status
        self.phmetro_conectado = False
        self.porta_phmetro = None
        self.leitura_ativa = False
        self.lock_serial = threading.Lock()  # 🔒 adiciona o lock
        self.thread_monitoramento = threading.Thread(target=self.monitorar_conexao, daemon=True)
        self.thread_monitoramento.start()

    def encontrar_porta_phmetro(self):
        for porta_info in serial.tools.list_ports.comports():
            try:
                with self.lock_serial:  # 🔒 trava acesso serial
                    with serial.Serial(porta_info.device, baudrate=9600, timeout=1) as ser:
                        comando = bytes([0x10]) + b'MDR\r'
                        ser.write(comando)
                        time.sleep(0.5)
                        resposta = ser.read(100).decode(errors='ignore')
                        if "HI98161" in resposta:
                            return porta_info.device
            except Exception:
                continue
        return None

    def monitorar_conexao(self):
        while True:
            if not self.leitura_ativa:
                porta = self.encontrar_porta_phmetro()
                conectado = porta is not None

                if conectado != self.phmetro_conectado:
                    self.phmetro_conectado = conectado
                    self.porta_phmetro = porta if conectado else None
                    if self.callback_status:
                        self.callback_status(conectado)
            time.sleep(2)

    def obter_porta(self):
        return self.porta_phmetro

    def ler_ph(self):
        if not self.phmetro_conectado or not self.porta_phmetro:
            return None

        resposta = None
        try:
            self.leitura_ativa = True
            with self.lock_serial:  # 🔒 trava acesso serial
                with serial.Serial(self.porta_phmetro, baudrate=9600, timeout=0.5) as ser:
                    comando = bytes([0x10]) + b'RAS\r'
                    ser.write(comando)
                    resposta = ser.read_until(b'\x03')
                    print(f"Resposta crua: {resposta}")
        except Exception as e:
            print(f"Erro ao ler pH: {e}")
            return None
        finally:
            self.leitura_ativa = False

        if not resposta or not resposta.startswith(b'\x02') or not resposta.endswith(b'\x03'):
            return None

        try:
            conteudo = resposta[1:-1].decode(errors='ignore')
            print(f"Conteúdo decodificado: {conteudo}")
            idx = conteudo.find('RR+')
            if idx == -1:
                return None
            valor_raw = conteudo[idx+3:idx+9]
            return float(valor_raw)
        except Exception as e:
            print(f"Erro ao processar resposta: {e}")
            return None
