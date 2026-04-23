import copy
import re
import unicodedata
import zipfile
from pathlib import Path
from urllib.parse import urljoin
from xml.sax.saxutils import escape

import requests
from bs4 import BeautifulSoup


BASE_URL = "https://www.guimavelveiculos.com.br"
START_URL = f"{BASE_URL}/search"
OUTPUT_XLSX_FILE = "estoque_google_planilhas.xlsx"
REQUEST_TIMEOUT = 30
CARD_SELECTOR = ".card__wrapper a.card"
PAGE_SELECTOR = ".pagination__list a.pagination__page[href]"
TECHNICAL_SELECTOR = ".card__technical__information"
TECHNICAL_VALUE_SELECTOR = ".card__technical__information__value"
TECHNICAL_ICON_SELECTOR = ".card__technical__information__icon"
IMAGE_ATTRIBUTES = ("src", "data-src", "data-lazy", "srcset")
SHEET_COLUMNS = [
    "MARCA",
    "NOME",
    "CARROCERIA",
    "ANO",
    "COR",
    "CAMBIO",
    "KM",
    "TIPO",
    "VALOR",
    "FOTO"
]
TECHNICAL_FIELDS = {
    "icon--calendar": "ANO",
    "icon--color-palette": "COR",
    "icon--transmission": "CAMBIO",
    "icon--speedometer": "KM",
    "icon--fuel": "TIPO",
}
BODYWORK_TYPES = ("SEDAN", "SUV", "RET", "CAMINHONETE")
BODYWORK_KEYWORDS = {
    "CAMINHONETE": {
        "keywords": {
            "picape",
            "pickup",
            "cabine simples",
            "cabine dupla",
            "cs",
            "cd",
            "utilitario",
        },
        "models": {
            "saveiro",
            "strada",
            "ranger",
            "hilux",
            "amarok",
            "s10",
            "montana",
            "frontier",
            "l200",
            "toro",
            "maverick",
        },
    },
    "SUV": {
        "keywords": {
            "suv",
            "crossover",
            "4x4",
            "4wd",
            "awd",
        },
        "models": {
            "tracker",
            "nivus",
            "t cross",
            "tcross",
            "taos",
            "tiguan",
            "compass",
            "renegade",
            "pulse",
            "fastback",
            "kicks",
            "creta",
            "hrv",
            "hr-v",
            "wrv",
            "wr-v",
            "corolla cross",
            "rav4",
            "equinox",
            "territory",
            "ecosport",
            "duster",
            "captur",
            "asx",
            "outlander",
            "sportage",
            "sorento",
            "c4 cactus",
        },
    },
    "SEDAN": {
        "keywords": {
            "sedan",
        },
        "models": {
            "civic",
            "city",
            "corolla",
            "versa",
            "sentra",
            "cronos",
            "virtus",
            "voyage",
            "jetta",
            "prisma",
            "onix plus",
            "hb20s",
            "yaris sedan",
            "logan",
            "fluence",
            "ka sedan",
            "cerato",
        },
    },
    "RET": {
        "keywords": {
            "hatch",
            "liftback",
            "sportback",
            "wagon",
            "perua",
        },
        "models": {
            "gol",
            "polo",
            "fox",
            "up",
            "onix",
            "hb20",
            "argo",
            "mobi",
            "kwid",
            "208",
            "308",
            "sandero",
            "fit",
            "march",
            "c3",
            "palio",
            "uno",
            "etios",
            "yaris",
            "cooper",
        },
    },
}
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

    texto = " ".join(str(valor).split()).strip()
    return texto or None


def normalizar_texto_busca(valor):
    texto = limpar_texto(valor)
    if not texto:
        return ""

    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(caractere for caractere in texto if not unicodedata.combining(caractere))
    texto = texto.lower()
    return re.sub(r"[^a-z0-9]+", " ", texto).strip()


def apagar_arquivo_saida(caminho_arquivo):
    caminho = Path(caminho_arquivo)
    if caminho.exists():
        caminho.unlink()


def obter_html(session, url):
    response = session.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    return BeautifulSoup(response.text, "html.parser")


def obter_texto_visivel(elemento):
    if not elemento:
        return None

    elemento_copia = copy.copy(elemento)
    for oculto in elemento_copia.select('[style*="display:none"]'):
        oculto.decompose()

    texto = limpar_texto(elemento_copia.get_text(" ", strip=True))
    if texto:
        return texto

    return limpar_texto(elemento.get_text(" ", strip=True))


def selecionar_primeiro_texto(raiz, seletores):
    for seletor in seletores:
        elemento = raiz.select_one(seletor)
        texto = obter_texto_visivel(elemento)
        if texto:
            return texto

    return None


def selecionar_primeiro_atributo(raiz, seletores, atributos):
    for seletor in seletores:
        elemento = raiz.select_one(seletor)
        if not elemento:
            continue

        for atributo in atributos:
            valor = limpar_texto(elemento.get(atributo))
            if valor:
                return valor

    return None


def normalizar_url_imagem(url_imagem):
    if not url_imagem:
        return None

    valor_limpo = url_imagem.split(",")[0].split(" ")[0]
    return urljoin(BASE_URL, valor_limpo)


def extrair_info_tecnica(card):
    dados = {campo: None for campo in TECHNICAL_FIELDS.values()}

    for bloco in card.select(TECHNICAL_SELECTOR):
        icone = bloco.select_one(TECHNICAL_ICON_SELECTOR)
        valor = bloco.select_one(TECHNICAL_VALUE_SELECTOR)

        if not icone or not valor:
            continue

        classes_icone = set(icone.get("class", []))
        texto_valor = obter_texto_visivel(valor)
        if not texto_valor:
            continue

        for classe_icone, nome_campo in TECHNICAL_FIELDS.items():
            if classe_icone in classes_icone:
                dados[nome_campo] = texto_valor
                break

    return dados


def extrair_veiculo(card):
    link_relativo = limpar_texto(card.get("href"))
    link_anuncio = urljoin(BASE_URL, link_relativo) if link_relativo else None

    veiculo = {
        "NOME": selecionar_primeiro_texto(card, [".card__title", "img[alt]"]),
        "MARCA": selecionar_primeiro_texto(card, [".card__brand"]),
        "VALOR": selecionar_primeiro_texto(card, [".card__sell__value"]),
        "FOTO": normalizar_url_imagem(
            selecionar_primeiro_atributo(card, [".card__image", "img"], IMAGE_ATTRIBUTES)
        ),
        "LINK": link_anuncio,
    }
    veiculo.update(extrair_info_tecnica(card))
    veiculo["CARROCERIA"] = inferir_carroceria(veiculo)
    return veiculo


def inferir_carroceria(veiculo):
    texto_base = " ".join(
        filter(
            None,
            [
                normalizar_texto_busca(veiculo.get("MARCA")),
                normalizar_texto_busca(veiculo.get("NOME")),
            ],
        )
    )

    if not texto_base:
        return "RET"

    pontuacoes = {tipo: 0 for tipo in BODYWORK_TYPES}

    for tipo, sinais in BODYWORK_KEYWORDS.items():
        for palavra in sinais["keywords"]:
            palavra_normalizada = normalizar_texto_busca(palavra)
            if palavra_normalizada and palavra_normalizada in texto_base:
                pontuacoes[tipo] += 3

        for modelo in sinais["models"]:
            modelo_normalizado = normalizar_texto_busca(modelo)
            if modelo_normalizado and modelo_normalizado in texto_base:
                pontuacoes[tipo] += 2

    if "sedan" in texto_base:
        pontuacoes["SEDAN"] += 3
    if "hatch" in texto_base:
        pontuacoes["RET"] += 3
    if "suv" in texto_base:
        pontuacoes["SUV"] += 3
    if "picape" in texto_base or "pickup" in texto_base:
        pontuacoes["CAMINHONETE"] += 4

    tipo_escolhido = max(BODYWORK_TYPES, key=lambda tipo: pontuacoes[tipo])
    return tipo_escolhido if pontuacoes[tipo_escolhido] > 0 else "RET"


def extrair_total_paginas(soup):
    paginas = []

    for link in soup.select(PAGE_SELECTOR):
        texto = limpar_texto(link.get_text(" ", strip=True))
        if texto and texto.isdigit():
            paginas.append(int(texto))

    return max(paginas, default=1)


def montar_url_pagina(numero_pagina):
    if numero_pagina <= 1:
        return START_URL
    return f"{START_URL}/pagina.{numero_pagina}"


def obter_chave_duplicidade(veiculo):
    if veiculo.get("LINK"):
        return veiculo["LINK"]

    return (
        veiculo.get("NOME"),
        veiculo.get("MARCA"),
        veiculo.get("ANO"),
        veiculo.get("FOTO"),
    )


def raspar_estoque():
    veiculos = []
    chaves_vistas = set()

    with requests.Session() as session:
        primeira_pagina = obter_html(session, START_URL)
        total_paginas = extrair_total_paginas(primeira_pagina)
        print(f"Total de paginas identificado: {total_paginas}")

        for numero_pagina in range(1, total_paginas + 1):
            url = montar_url_pagina(numero_pagina)
            print(f"Processando pagina {numero_pagina}: {url}")

            soup = primeira_pagina if numero_pagina == 1 else obter_html(session, url)
            cards = soup.select(CARD_SELECTOR)
            print(f"Cards encontrados: {len(cards)}")

            for card in cards:
                veiculo = extrair_veiculo(card)
                chave_unica = obter_chave_duplicidade(veiculo)

                if chave_unica in chaves_vistas:
                    continue

                chaves_vistas.add(chave_unica)
                veiculos.append(veiculo)

    return veiculos


def montar_linhas_planilha(dados):
    linhas = [SHEET_COLUMNS]

    for item in dados:
        linhas.append([item.get(coluna) for coluna in SHEET_COLUMNS])

    return linhas


def coluna_excel(numero):
    letras = []

    while numero > 0:
        numero, resto = divmod(numero - 1, 26)
        letras.append(chr(65 + resto))

    return "".join(reversed(letras))


def montar_shared_strings(linhas):
    strings = []
    indices = {}

    for linha in linhas:
        for valor in linha:
            texto = "" if valor is None else str(valor)
            if texto not in indices:
                indices[texto] = len(strings)
                strings.append(texto)

    itens = "".join(f"<si><t>{escape(texto)}</t></si>" for texto in strings)
    xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        f'count="{sum(len(linha) for linha in linhas)}" uniqueCount="{len(strings)}">'
        f"{itens}"
        "</sst>"
    )
    return indices, xml


def montar_sheet_xml(linhas, indices_strings):
    xml_linhas = []

    for numero_linha, linha in enumerate(linhas, start=1):
        celulas = []
        for numero_coluna, valor in enumerate(linha, start=1):
            referencia = f"{coluna_excel(numero_coluna)}{numero_linha}"
            texto = "" if valor is None else str(valor)
            indice_string = indices_strings[texto]
            celulas.append(f'<c r="{referencia}" t="s"><v>{indice_string}</v></c>')

        xml_linhas.append(f'<row r="{numero_linha}">{"".join(celulas)}</row>')

    dimensao = f"A1:{coluna_excel(len(SHEET_COLUMNS))}{len(linhas)}"
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f'<dimension ref="{dimensao}"/>'
        "<sheetViews><sheetView workbookViewId=\"0\"/></sheetViews>"
        "<sheetFormatPr defaultRowHeight=\"15\"/>"
        f"<sheetData>{''.join(xml_linhas)}</sheetData>"
        "</worksheet>"
    )


def montar_arquivos_xlsx(linhas):
    indices_strings, shared_strings_xml = montar_shared_strings(linhas)
    sheet_xml = montar_sheet_xml(linhas, indices_strings)

    return {
        "[Content_Types].xml": (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/xl/workbook.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
            '<Override PartName="/xl/worksheets/sheet1.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
            '<Override PartName="/xl/styles.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'
            '<Override PartName="/xl/sharedStrings.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sharedStrings+xml"/>'
            '<Override PartName="/docProps/core.xml" '
            'ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>'
            '<Override PartName="/docProps/app.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>'
            "</Types>"
        ),
        "_rels/.rels": (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
            'Target="xl/workbook.xml"/>'
            '<Relationship Id="rId2" '
            'Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" '
            'Target="docProps/core.xml"/>'
            '<Relationship Id="rId3" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" '
            'Target="docProps/app.xml"/>'
            "</Relationships>"
        ),
        "docProps/app.xml": (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties" '
            'xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">'
            "<Application>Python</Application>"
            "</Properties>"
        ),
        "docProps/core.xml": (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
            'xmlns:dc="http://purl.org/dc/elements/1.1/" '
            'xmlns:dcterms="http://purl.org/dc/terms/" '
            'xmlns:dcmitype="http://purl.org/dc/dcmitype/" '
            'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
            "<dc:title>Estoque Guimavel</dc:title>"
            "<dc:creator>scrap_guimavel</dc:creator>"
            "</cp:coreProperties>"
        ),
        "xl/workbook.xml": (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
            "<bookViews><workbookView/></bookViews>"
            "<sheets><sheet name=\"Estoque\" sheetId=\"1\" r:id=\"rId1\"/></sheets>"
            "</workbook>"
        ),
        "xl/_rels/workbook.xml.rels": (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
            'Target="worksheets/sheet1.xml"/>'
            '<Relationship Id="rId2" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" '
            'Target="styles.xml"/>'
            '<Relationship Id="rId3" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/sharedStrings" '
            'Target="sharedStrings.xml"/>'
            "</Relationships>"
        ),
        "xl/styles.xml": (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            '<fonts count="1"><font><sz val="11"/><name val="Calibri"/></font></fonts>'
            '<fills count="2"><fill><patternFill patternType="none"/></fill>'
            '<fill><patternFill patternType="gray125"/></fill></fills>'
            '<borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>'
            '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>'
            '<cellXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/></cellXfs>'
            '<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>'
            "</styleSheet>"
        ),
        "xl/sharedStrings.xml": shared_strings_xml,
        "xl/worksheets/sheet1.xml": sheet_xml,
    }


def salvar_xlsx(dados, caminho_arquivo):
    linhas = montar_linhas_planilha(dados)
    arquivos_xlsx = montar_arquivos_xlsx(linhas)

    with zipfile.ZipFile(caminho_arquivo, "w", compression=zipfile.ZIP_DEFLATED) as xlsx:
        for nome_arquivo, conteudo in arquivos_xlsx.items():
            xlsx.writestr(nome_arquivo, conteudo)


def main():
    try:
        veiculos = raspar_estoque()
        apagar_arquivo_saida(OUTPUT_XLSX_FILE)
        salvar_xlsx(veiculos, OUTPUT_XLSX_FILE)
        print(f"\nTotal de veiculos coletados: {len(veiculos)}")
        print(f"Planilha gerada com sucesso: {OUTPUT_XLSX_FILE}")
    except requests.RequestException as exc:
        print(f"Erro de rede ao acessar o estoque: {exc}")
        raise
    except Exception as exc:
        print(f"Erro ao gerar a planilha: {exc}")
        raise


if __name__ == "__main__":
    main()
