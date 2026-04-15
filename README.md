# Scrap Guimavel

Script em Python para raspar o estoque de veículos da Guimavel Veículos e gerar um arquivo `JSON` com os dados do catálogo.

## Objetivo

O projeto acessa a página de estoque:

`https://www.guimavelveiculos.com.br/search`

e coleta os veículos disponíveis, salvando o resultado em:

`estoque.JSON`

## Dados coletados

Cada veículo é exportado com os seguintes campos:

- `NOME`
- `MARCA`
- `ANO`
- `COR`
- `CAMBIO`
- `KM`
- `TIPO`
- `FOTO`

## Como funciona

O script:

1. Acessa a primeira página do estoque.
2. Descobre o total de páginas pela paginação do site.
3. Percorre apenas as páginas numeradas válidas.
4. Extrai os dados dos cards de veículos.
5. Evita duplicidade usando `NOME`, `MARCA` e `ANO`.
6. Salva o resultado final em `estoque.JSON`.

## Tecnologias usadas

- Python 3.11+
- `requests`
- `beautifulsoup4`

## Instalação

### 1. Instale as dependências

Se estiver usando Poetry:

```powershell
poetry install
```

### 2. Ative o ambiente virtual

Se quiser usar o ambiente local do projeto:

```powershell
poetry shell
```

Ou execute os comandos com `poetry run`.

## Como executar

Com Poetry:

```powershell
poetry run python .\app.py
```

Se você já estiver com um Python configurado no ambiente:

```powershell
python .\app.py
```

## Saída gerada

Ao final da execução, o projeto cria ou sobrescreve o arquivo:

`estoque.JSON`

Exemplo de estrutura:

```json
[
    {
        "NOME": "FORD ECOSPORT 1.5 TI-VCT FLEX TITANIUM AUTOMÁTICO",
        "MARCA": "FORD",
        "FOTO": "https://...",
        "ANO": "2019/ 2020",
        "COR": "Prata",
        "CAMBIO": "Automático",
        "KM": "120.000 KM",
        "TIPO": "Flex"
    }
]
```

## Estrutura do projeto

```text
scrap_guimavel/
|-- app.py
|-- estoque.JSON
|-- pyproject.toml
|-- poetry.lock
|-- README.md
```

## Arquivo principal

O comportamento principal está em [app.py](c:/Dev/Scrapping/scrap_guimavel/app.py).

As funções mais importantes são:

- `obter_html`: baixa e transforma o HTML em `BeautifulSoup`
- `extrair_info_tecnica`: lê ano, cor, câmbio, km e tipo
- `extrair_veiculo`: monta o dicionário final de cada card
- `extrair_total_paginas`: identifica o número máximo de páginas
- `raspar_estoque`: coordena toda a raspagem
- `salvar_json`: grava o arquivo final

## Regras atuais de extração

O scraper depende principalmente destes seletores do HTML:

- `.card__wrapper a.card`
- `.card__title`
- `.card__brand`
- `.card__image`
- `.card__technical__information`
- `.pagination__list a.pagination__page`

Se o site mudar a estrutura, esses seletores podem precisar de ajuste.

## Observações importantes

- O projeto depende de acesso à internet para buscar as páginas do estoque.
- O arquivo `estoque.JSON` é sobrescrito a cada execução.
- Algumas imagens podem vir em `src` ou `data-src`; o script já trata ambos.
- A quantidade de veículos pode mudar conforme o estoque do site muda.

## Possíveis melhorias

- Salvar também o link do anúncio
- Exportar para CSV ou Excel
- Adicionar testes automatizados
- Registrar logs em arquivo
- Parametrizar URL de entrada e nome do arquivo de saída

## Comandos úteis

Instalar dependências:

```powershell
poetry install
```

Executar o scraper:

```powershell
poetry run python .\app.py
```

## Manutenção

Se a raspagem parar de funcionar, revise:

1. Se a URL do estoque continua a mesma.
2. Se os seletores CSS do site mudaram.
3. Se a paginação ainda segue o padrão `/search/pagina.N`.
4. Se os campos da imagem continuam em `src` ou `data-src`.

## Licença

Uso interno do projeto.
