class BarcodeReader:
    def __init__(self):
        pass

    def read(self, codigo=None):
        # Caso o código seja passado como argumento, use ele, senão, peça a entrada
        if codigo is None:
            codigo = input("Escaneie o código de barras: ").strip()
        
        if not self._codigo_valido(codigo):
            raise ValueError("Etiqueta inválida: o código deve começar com 'R00000'.")
        
        id_registro_abate = self._extrair_codigo(codigo)
        banda = self._extrair_banda(codigo)
        
        return id_registro_abate, banda

    def _codigo_valido(self, codigo):
        return codigo.startswith("R00000") and len(codigo) >= 14

    def _extrair_codigo(self, codigo):
        return codigo[6:14]  # Extrai o código único do registro de abate

    def _extrair_banda(self, codigo):
        return codigo[14:15]  # Extrai a banda da etiqueta
