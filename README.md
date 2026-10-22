# Gerador de Etiquetas de Controle de Gravação de Pacotes

Script em Python que lê XMLs de NF-e e gera um PDF com etiquetas de **controle de gravação de pacotes**, no formato de bobina contínua de **50 mm de largura** (impressoras térmicas de etiqueta).

É gerada **uma etiqueta por item** de cada nota, já preenchida com os dados da NF-e e com o canal de venda (Shopee / Mercado Livre) marcado automaticamente.

## O que vai na etiqueta

```
   CONTROLE DE GRAVAÇÃO
        DE PACOTES

DATA:  ______________
NOME:  ______________
ITEM:  ______________
QTD:   ______________
CONFERIDO POR: ______
NF:    ______________

SHOPEE         [x]
MERCADO LIVRE  [ ]
OUTRO: ______________

ASSINATURA: _________
```

| Campo          | Origem no XML da NF-e                     |
|----------------|-------------------------------------------|
| DATA           | `ide/dhEmi` (data de emissão, dd/mm/aaaa) |
| NOME           | `dest/xNome` (destinatário)               |
| ITEM           | `det/prod/xProd` (descrição do produto)   |
| QTD            | `det/prod/qCom`                           |
| NF             | `ide/nNF`                                 |
| CONFERIDO POR  | constante `CONFERENTE` no script          |
| Canal de venda | detectado em `infIntermed/idCadIntTran` e `infAdic/infCpl` |

Textos longos (nome ou descrição do item) quebram em várias linhas — nada é cortado. Se a etiqueta precisar de mais espaço que a altura mínima, ela cresce automaticamente.

## Requisitos

- Python 3.8+
- [ReportLab](https://pypi.org/project/reportlab/)

```bash
pip install reportlab
```

## Estrutura de pastas

```
gerar_etiquetas.py
xml/                 <- coloque aqui os XMLs das notas
  processados/       <- criada automaticamente; XMLs já usados vão para cá
etiquetas.pdf        <- PDF gerado
```

## Uso

Uso padrão (lê todos os `.xml` da pasta `xml`, gera `etiquetas.pdf`, move os XMLs para `xml/processados` e abre o PDF):

```bash
python gerar_etiquetas.py
```

Outros exemplos:

```bash
python gerar_etiquetas.py nota1.xml nota2.xml   # XMLs específicos (não são movidos)
python gerar_etiquetas.py -o saida.pdf          # nome do PDF de saída
python gerar_etiquetas.py --altura 80           # altura mínima de 80 mm
python gerar_etiquetas.py --auto                # altura automática, sem mínimo
python gerar_etiquetas.py --manter              # não move os XMLs para 'processados'
python gerar_etiquetas.py --nao-abrir           # não abre o PDF ao final
```

### Opções

| Opção            | Padrão          | Descrição                                                        |
|------------------|-----------------|------------------------------------------------------------------|
| `xmls`           | pasta `xml`     | Arquivos XML a processar                                         |
| `-o`, `--saida`  | `etiquetas.pdf` | Caminho do PDF gerado                                            |
| `--altura`       | `100`           | Altura mínima da etiqueta em mm (igual ao papel do driver)       |
| `--auto`         | —               | Usa só a altura necessária para o conteúdo                       |
| `--manter`       | —               | Não move os XMLs lidos para `xml/processados`                    |
| `--nao-abrir`    | —               | Não abre o PDF automaticamente (a abertura só funciona no Windows) |

XMLs inválidos (sem `infNFe`) são ignorados com um aviso, e o restante é processado normalmente.

## Configuração

As constantes no topo do script permitem ajustar o layout:

| Constante    | Valor padrão | Significado                                  |
|--------------|--------------|----------------------------------------------|
| `LARGURA`    | 50 mm        | Largura da bobina                            |
| `XE`, `XD`   | 3 mm / 46 mm | Margem esquerda e limite direito do conteúdo |
| `TAM`        | 7,5 pt       | Tamanho da fonte                             |
| `PASSO`      | 5,2 mm       | Espaçamento entre linhas                     |
| `CONFERENTE` | `"Diego"`    | Nome impresso em "CONFERIDO POR"             |

## Gerando um executável (opcional)

O script já está preparado para rodar empacotado (ele procura a pasta `xml` ao lado do `.exe`). Com o PyInstaller:

```bash
pip install pyinstaller
pyinstaller --onefile gerar_etiquetas.py
```

Copie o `gerar_etiquetas.exe` da pasta `dist` para onde quiser, crie a pasta `xml` ao lado dele e é só dar dois cliques. Em caso de erro, a janela fica aberta até pressionar Enter.

## Impressão

Na hora de imprimir, use o tamanho de papel do driver da impressora (50 × 100 mm por padrão) e escala **100% / tamanho real**, sem "ajustar à página", para manter as medidas.
