etiquetas_lidas = []

def get_etiquetas():
    return etiquetas_lidas

def armazenar_etiquetas(id_historico_abertura_camara_item, valor_ph):
    indice = len(etiquetas_lidas)
    etiqueta = [indice, [
        id_historico_abertura_camara_item,
        valor_ph
    ]]
    etiquetas_lidas.append(etiqueta)
    print(etiquetas_lidas)

def zerar_armazenamento():
    etiquetas_lidas.clear()
