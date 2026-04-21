# Scrap Guimavel

Script em Python para raspar o estoque de veículos da Guimavel Veículos e gerar uma planilha `.xlsx` com os dados dos cards do site.

## Objetivo

O projeto acessa a página de estoque:

`https://www.guimavelveiculos.com.br/search`

e coleta os veículos disponíveis para salvar no arquivo:

`estoque_google_planilhas.xlsx`

## Dados coletados

Cada veículo é exportado com os seguintes campos:

- `FOTO`
- `MARCA`
- `NOME`
- `ANO`
- `COR`
- `CAMBIO`
- `KM`
- `TIPO`
- `VALOR`

## Ordem na planilha

A planilha segue a ordem visual do card do site:

1. `FOTO`
2. `MARCA`
3. `NOME`
4. `ANO`
5. `COR`
6. `CAMBIO`
7. `KM`
8. `TIPO`
9. `VALOR`

Essa ordem é controlada pela constante `SHEET_COLUMNS` no arquivo [app.py](/c:/Dev/Scrapping/scrap_guimavel/app.py).

## Como funciona

O script:

1. Acessa a primeira página do estoque.
2. Descobre o total de páginas pela paginação do site.
3. Percorre todas as páginas válidas do estoque.
4. Localiza os cards com o seletor `.card__wrapper a.card`.
5. Extrai os dados visíveis de cada veículo.
6. Evita duplicidade usando o link do anúncio como chave principal.
7. Apaga a planilha anterior.
8. Gera uma nova planilha `.xlsx`.

## Estrutura do card usada na raspagem

O scraper foi ajustado para ler o HTML base dos cards do estoque, incluindo:

- `.card__brand`
- `.card__title`
- `.card__image`
- `.card__technical__information`
- `.card__sell__value`

Mapeamento atual dos campos técnicos:

- `icon--calendar` → `ANO`
- `icon--color-palette` → `COR`
- `icon--transmission` → `CAMBIO`
- `icon--speedometer` → `KM`
- `icon--fuel` → `TIPO`

O valor do veículo é extraído de:

- `.card__sell__value`

## Tecnologias usadas

- Python 3.11+
- `requests`
- `beautifulsoup4`

## Instalação

Instale as dependências com Poetry:

```powershell
poetry install
```

## Como executar

Com Poetry:

```powershell
poetry run python .\app.py
```

Ou diretamente com Python:

```powershell
python .\app.py
```

## Saída gerada

Ao final da execução, o projeto recria o arquivo:

`estoque_google_planilhas.xlsx`

O arquivo anterior é removido antes da nova geração.

## Estrutura do projeto

```text
scrap_guimavel/
|-- app.py
|-- estoque_google_planilhas.xlsx
|-- pyproject.toml
|-- poetry.lock
|-- README.md
```

## Arquivo principal

O comportamento principal está em [app.py](/c:/Dev/Scrapping/scrap_guimavel/app.py).

Funções importantes:

- `obter_html`: baixa e transforma o HTML em `BeautifulSoup`
- `extrair_info_tecnica`: lê ano, cor, câmbio, km e tipo
- `extrair_veiculo`: monta os dados finais de cada card
- `extrair_total_paginas`: identifica o número máximo de páginas
- `raspar_estoque`: coordena toda a raspagem
- `salvar_xlsx`: grava a planilha final

## Observações importantes

- O projeto depende de acesso à internet para buscar o estoque.
- A quantidade de veículos pode mudar conforme o site atualiza o estoque.
- Algumas imagens podem vir em `src`, `data-src`, `data-lazy` ou `srcset`.
- O script remove trechos ocultos do HTML, como o `span` escondido no ano, para manter apenas o valor visível.

## Manutenção

Se a raspagem parar de funcionar, revise:

1. Se a URL do estoque continua a mesma.
2. Se os seletores CSS dos cards mudaram.
3. Se a paginação ainda segue o padrão `/search/pagina.N`.
4. Se o valor do veículo continua em `.card__sell__value`.
5. Se os campos da imagem continuam disponíveis nos atributos esperados.

## Licença

Uso interno do projeto.
