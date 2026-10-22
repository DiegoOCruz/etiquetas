"""Gera etiquetas de bobina contínua, 50 mm de largura (PDF) de controle de gravação de pacotes a partir de XMLs de NF-e.

Uso:
    python gerar_etiquetas.py                 # lê todos os .xml da pasta 'xml' -> etiquetas.pdf
    python gerar_etiquetas.py a.xml b.xml     # XMLs específicos
    python gerar_etiquetas.py -o saida.pdf
"""
import argparse
import glob
import io
import os
import shutil
import sys
import xml.etree.ElementTree as ET
from datetime import datetime

from reportlab.lib.units import mm
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas

NS = {"n": "http://www.portalfiscal.inf.br/nfe"}
LARGURA = 50 * mm            # largura da bobina (padrão da impressora)
XE, XD = 3 * mm, 46 * mm     # margem esquerda / limite direito do conteúdo (cabeçote imprime ~48 mm)
FONTE, FONTE_B = "Helvetica", "Helvetica-Bold"
TAM = 7.5    # pt
PASSO = 5.2 * mm   # distância entre linhas
CONFERENTE = "Diego"


def txt(no, caminho):
    el = no.find(caminho, NS)
    return (el.text or "").strip() if el is not None and el.text else ""


def ler_nfe(caminho):
    """Retorna uma lista de dicts (um por item da nota)."""
    inf = ET.parse(caminho).getroot().find(".//n:infNFe", NS)
    if inf is None:
        raise ValueError("infNFe não encontrado")

    emissao = txt(inf, "n:ide/n:dhEmi")
    try:
        data = datetime.fromisoformat(emissao).strftime("%d/%m/%Y")
    except ValueError:
        data = ""

    contexto = " ".join([txt(inf, "n:infIntermed/n:idCadIntTran"), txt(inf, "n:infAdic/n:infCpl")]).lower()
    if "shopee" in contexto:
        canal = "shopee"
    elif "mercado livre" in contexto or "mercadolivre" in contexto:
        canal = "ml"
    else:
        canal = "outro"

    base = {
        "data": data,
        "nome": txt(inf, "n:dest/n:xNome"),
        "nf": txt(inf, "n:ide/n:nNF"),
        "canal": canal,
    }
    itens = []
    for det in inf.findall("n:det", NS):
        qtd = float(txt(det, "n:prod/n:qCom") or 0)
        itens.append({**base, "item": txt(det, "n:prod/n:xProd"),
                      "qtd": str(int(qtd)) if qtd == int(qtd) else str(qtd)})
    return itens


def quebrar(texto, largura, fonte, tam):
    """Quebra o texto em linhas que caibam em 'largura' (nada é cortado)."""
    linhas, atual = [], ""
    for palavra in texto.split():
        while stringWidth(palavra, fonte, tam) > largura:  # palavra maior que a linha
            n = len(palavra)
            while n > 1 and stringWidth(palavra[:n], fonte, tam) > largura:
                n -= 1
            if atual:
                linhas.append(atual)
                atual = ""
            linhas.append(palavra[:n])
            palavra = palavra[n:]
        teste = f"{atual} {palavra}".strip()
        if stringWidth(teste, fonte, tam) <= largura:
            atual = teste
        else:
            linhas.append(atual)
            atual = palavra
    if atual:
        linhas.append(atual)
    return linhas or [""]


def campo(c, y, rotulo, valor=""):
    """Desenha 'ROTULO: valor' com linha sublinhada; valores longos quebram em mais linhas.
    Retorna o novo y."""
    x0 = XE + stringWidth(rotulo, FONTE, TAM) + 1 * mm
    c.setFont(FONTE, TAM)
    c.drawString(XE, y, rotulo)
    c.setLineWidth(0.4)
    for i, linha in enumerate(quebrar(valor, XD - x0 - 0.5 * mm, FONTE_B, TAM)):
        c.line(x0 if i == 0 else XE, y - 0.9 * mm, XD, y - 0.9 * mm)
        c.setFont(FONTE_B, TAM)
        c.drawString((x0 if i == 0 else XE) + 0.5 * mm, y, linha)
        y -= PASSO
    return y


def caixa(c, x, y, marcada):
    lado = 3.4 * mm
    c.setLineWidth(0.7)
    c.rect(x, y - 0.6 * mm, lado, lado)
    if marcada:
        c.setLineWidth(1.1)
        c.line(x + 0.6 * mm, y, x + lado - 0.6 * mm, y + lado - 1.2 * mm)
        c.line(x + 0.6 * mm, y + lado - 1.2 * mm, x + lado - 0.6 * mm, y)


def desenhar(c, e, topo):
    """Desenha a etiqueta a partir de 'topo' e retorna o y logo abaixo do último elemento."""
    y = topo - 5.5 * mm
    c.setFont(FONTE_B, TAM)
    c.drawCentredString((XE + XD) / 2, y, "CONTROLE DE GRAVAÇÃO")
    y -= PASSO * 0.8
    c.drawCentredString((XE + XD) / 2, y, "DE PACOTES")
    y -= PASSO * 1.5

    y = campo(c, y, "DATA:", e["data"])
    y = campo(c, y, "NOME:", e["nome"])
    y = campo(c, y, "ITEM:", e["item"])
    y = campo(c, y, "QTD:", e["qtd"])
    y = campo(c, y, "CONFERIDO POR:", CONFERENTE)
    y = campo(c, y, "NF:", e["nf"])
    y -= PASSO * 0.3

    c.setFont(FONTE, TAM)
    for rotulo, chave in (("SHOPEE", "shopee"), ("MERCADO LIVRE", "ml")):
        c.drawString(XE, y, rotulo)
        caixa(c, XE + stringWidth(rotulo, FONTE, TAM) + 2 * mm, y, e["canal"] == chave)
        y -= PASSO
    y = campo(c, y, "OUTRO:")
    y -= PASSO * 1.2
    y = campo(c, y, "ASSINATURA:")
    return y


def altura_necessaria(e):
    """Mede quanto a etiqueta precisa (varia com o tamanho do nome/item)."""
    ref = 1000 * mm
    y = desenhar(canvas.Canvas(io.BytesIO(), pagesize=(LARGURA, ref)), e, ref)
    return ref - y + 1.5 * mm


def pagina(c, e, altura_fixa=None):
    h = altura_necessaria(e)
    if altura_fixa:
        h = max(h, altura_fixa)  # nunca menor que o necessário (nada é cortado)
    c.setPageSize((LARGURA, h))
    c.setLineWidth(0.5)
    c.rect(1 * mm, 0.6 * mm, 47 * mm, h - 1.2 * mm)
    desenhar(c, e, h)


def pasta_base():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def main():
    aqui = pasta_base()
    ap = argparse.ArgumentParser()
    ap.add_argument("xmls", nargs="*", help="arquivos XML (padrão: pasta 'xml')")
    ap.add_argument("-o", "--saida", default=os.path.join(aqui, "etiquetas.pdf"))
    ap.add_argument("--altura", type=float, default=100,
                    help="altura mínima da etiqueta em mm (padrão: 100, igual ao papel do driver)")
    ap.add_argument("--auto", action="store_true", help="altura automática, sem mínimo")
    ap.add_argument("--manter", action="store_true", help="não mover os XMLs para 'processados'")
    ap.add_argument("--nao-abrir", action="store_true", help="não abrir o PDF ao final")
    args = ap.parse_args()

    usa_pasta = not args.xmls
    arquivos = args.xmls or sorted(glob.glob(os.path.join(aqui, "xml", "*.xml")))
    if not arquivos:
        raise SystemExit(f"Nenhum XML encontrado. Coloque os arquivos em: {os.path.join(aqui, 'xml')}")

    c = canvas.Canvas(args.saida, pagesize=(LARGURA, 60 * mm))
    c.setTitle("Etiquetas de controle")
    total = 0
    lidos = []
    for arq in arquivos:
        try:
            itens = ler_nfe(arq)
        except Exception as exc:
            print(f"[ignorado] {os.path.basename(arq)}: {exc}")
            continue
        for e in itens:
            pagina(c, e, None if args.auto else args.altura * mm)
            c.showPage()
            total += 1
        lidos.append(arq)
    if total == 0:
        raise SystemExit("Nenhuma etiqueta gerada.")
    c.save()
    print(f"{total} etiqueta(s) geradas em {args.saida}")
    if usa_pasta and not args.manter:
        destino = os.path.join(aqui, "xml", "processados")
        os.makedirs(destino, exist_ok=True)
        for arq in lidos:
            shutil.move(arq, os.path.join(destino, os.path.basename(arq)))
        print(f"{len(lidos)} XML(s) movidos para {destino}")
    if not args.nao_abrir and hasattr(os, "startfile"):
        os.startfile(args.saida)


if __name__ == "__main__":
    try:
        main()
    except SystemExit as exc:
        if exc.code not in (None, 0):
            print(exc.code)
            input("Pressione Enter para sair...")
    except Exception as exc:
        print(f"Erro: {exc}")
        input("Pressione Enter para sair...")
