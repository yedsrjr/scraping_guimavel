import json
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


BASE_URL = "https://www.guimavelveiculos.com.br"
START_URL = f"{BASE_URL}/search"
OUTPUT_FILE = "estoque.JSON"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/135.0.0.0 Safari/537.36"
    )
}


def limpar_texto(valor):
    if not valor:
        return None

    texto = " ".join(valor.split()).strip()
    return texto or None


def obter_html(session, url):
    response = session.get(url, headers=HEADERS, timeout=30)
    response.raise_for_status()
    return BeautifulSoup(response.text, "html.parser")


def extrair_info_tecnica(card):
    dados = {
        "ANO": None,
        "COR": None,
        "CAMBIO": None,
        "KM": None,
        "TIPO": None,
    }

    for bloco in card.select(".card__technical__information"):
        icone = bloco.select_one(".card__technical__information__icon")
        valor = bloco.select_one(".card__technical__information__value")

        if not icone or not valor:
            continue

        classes_icone = icone.get("class", [])
        texto_valor = limpar_texto(valor.get_text(" ", strip=True))

        if "icon--calendar" in classes_icone:
            dados["ANO"] = texto_valor
        elif "icon--color-palette" in classes_icone:
            dados["COR"] = texto_valor
        elif "icon--transmission" in classes_icone:
            dados["CAMBIO"] = texto_valor
        elif "icon--speedometer" in classes_icone:
            dados["KM"] = texto_valor
        elif "icon--fuel" in classes_icone:
            dados["TIPO"] = texto_valor

    return dados


def extrair_veiculo(card):
    nome = limpar_texto(card.select_one(".card__title").get_text(" ", strip=True))
    marca = limpar_texto(card.select_one(".card__brand").get_text(" ", strip=True))
    imagem = card.select_one(".card__image")
    foto = None

    if imagem:
        foto = limpar_texto(imagem.get("src")) or limpar_texto(imagem.get("data-src"))
        if foto:
            foto = urljoin(BASE_URL, foto)

    veiculo = {
        "NOME": nome,
        "MARCA": marca,
        "FOTO": foto,
    }
    veiculo.update(extrair_info_tecnica(card))
    return veiculo


def extrair_total_paginas(soup):
    paginas = []

    for link in soup.select(".pagination__list a.pagination__page[href]"):
        texto = limpar_texto(link.get_text(" ", strip=True))
        if texto and texto.isdigit():
            paginas.append(int(texto))

    return max(paginas, default=1)


def montar_url_pagina(numero_pagina):
    if numero_pagina <= 1:
        return START_URL
    return f"{START_URL}/pagina.{numero_pagina}"


def raspar_estoque():
    session = requests.Session()
    veiculos = []
    nomes_vistos = set()

    primeira_pagina = obter_html(session, START_URL)
    total_paginas = extrair_total_paginas(primeira_pagina)
    print(f"Total de páginas identificado: {total_paginas}")

    for numero_pagina in range(1, total_paginas + 1):
        url = montar_url_pagina(numero_pagina)
        print(f"Processando página {numero_pagina}: {url}")

        soup = primeira_pagina if numero_pagina == 1 else obter_html(session, url)

        cards = soup.select(".card__wrapper a.card")
        print(f"Cards encontrados: {len(cards)}")

        for card in cards:
            try:
                veiculo = extrair_veiculo(card)
                chave_unica = (
                    veiculo["NOME"],
                    veiculo["MARCA"],
                    veiculo["ANO"],
                )

                if chave_unica in nomes_vistos:
                    continue

                nomes_vistos.add(chave_unica)
                veiculos.append(veiculo)
            except Exception as exc:
                print(f"Erro ao processar card: {exc}")

    return veiculos


def salvar_json(dados, arquivo):
    with open(arquivo, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=4)


def main():
    veiculos = raspar_estoque()
    salvar_json(veiculos, OUTPUT_FILE)
    print(f"\nTotal de veículos coletados: {len(veiculos)}")
    print(f"Arquivo gerado com sucesso: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
