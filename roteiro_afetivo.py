# -*- coding: utf-8 -*-
"""
ROTEIRO AFETIVO - Uma aventura pixelizada acolhedora de carinho e código.

Versão Python (pygame) convertida do jogo original em HTML5 Canvas.

Como rodar (precisa de Python instalado):
    python roteiro_afetivo.py
    (o pygame é instalado automaticamente na primeira execução se faltar)

Como gerar um executável que roda em qualquer PC SEM Python:
    Windows:  duplo-clique em build_windows.bat
    Mac/Linux: bash build_macos_linux.sh
    (gera o executável na pasta 'dist/')

Controlos:
    - Conduz/anda com as teclas WASD ou as setas.
    - Ou clica e arrasta com o rato dentro do ecrã para guiar.
    - ENTER ou clique avança os diálogos.
    - R reinicia no fim da história.
"""

import math
import random
import sys
import os
import subprocess


def _garantir_pygame():
    """Importa o pygame; se não estiver instalado, tenta instalar via pip.

    Isto torna o ficheiro .py executável em qualquer PC com Python, mesmo
    sem o pygame previamente instalado. Quando empacotado como .exe pelo
    PyInstaller, o pygame já vai embutido e este bloco não faz nada.
    """
    try:
        import pygame  # noqa: F401
        return
    except ImportError:
        pass

    # Não tenta instalar quando já está congelado num executável.
    if getattr(sys, "frozen", False):
        raise SystemExit("pygame não encontrado no executável empacotado.")

    print("pygame não encontrado. A tentar instalar automaticamente...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pygame"])
    except Exception as e:  # noqa: BLE001
        raise SystemExit(
            "Não foi possível instalar o pygame automaticamente.\n"
            "Instala manualmente com:  pip install pygame\n"
            f"Detalhe do erro: {e}"
        )


_garantir_pygame()
import pygame


def caminho_recurso(rel):
    """Resolve caminhos de ficheiros tanto a correr como .py como empacotado.

    Útil caso queiras juntar fontes/imagens no futuro. Não é necessário
    para a versão atual (que não usa ficheiros externos).
    """
    base = getattr(sys, "_MEIPASS", os.path.abspath("."))
    return os.path.join(base, rel)

# ==============================================================================
# CONFIGURAÇÃO DO ECRÃ VIRTUAL DE BAIXA RESOLUÇÃO (MODO PIXEL ART RETRO)
# ==============================================================================
LARGURA = 400
ALTURA = 300
ESCALA = 2  # Janela final = 800 x 600
FPS = 60


def hx(s):
    """Converte uma cor hexadecimal '#rrggbb' num tuplo RGB."""
    s = s.lstrip('#')
    return (int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16))


# Paleta de Cores Cozy & Camponesa
COR_ASFALTO = hx('#343f44')
COR_GRAMA = hx('#4a7551')
COR_CEU_DIA = hx('#8cb8d0')
COR_CEU_NOITE = hx('#0c1020')
COR_CEU_ENTARDECER = hx('#d36c3c')
COR_CAIXA_DIALOGO = hx('#4e311f')
COR_BORDA_DIALOGO = hx('#9e714b')
COR_TEXTO = hx('#fcf5db')

# Constantes das Cenas
CENA_1_ESTRADA = 1
CENA_2_KIKAO = 2
CENA_3_VIAGEM = 3
CENA_4_CHEGADA_CASA = 4
CENA_5_QUARTO = 5
CENA_6_PROGRAMACAO = 6


# ==============================================================================
# ESTADO GLOBAL DO JOGO
# ==============================================================================
class G:
    """Contentor de estado mutável (equivalente às variáveis globais do JS)."""
    cenaAtual = CENA_1_ESTRADA
    transicaoAlfa = 0.0
    transitando = False
    direcaoTransicao = 1
    proximaCena = None

    # Movimento do carro
    carroX = 10.0
    carroY = 185.0
    carroVel = 1.8
    estradaOffset = 0.0
    velocidadeManual = 1.6
    VELOCIDADE_ALVO = 1.6

    # Tráfego
    listaObstaculos = []
    timerGerarObstaculo = 0
    colidirTimer = 0

    # Cena 2 (Kikão)
    homemX = 0.0
    homemY = 0.0
    homemAtivo = False
    homemComLanche = False
    homemVisivel = True
    dinerTimer = 0
    kikaoEstado = "conduzindo_para_parar"

    # Cena 4 (Casa e animais)
    casaX = 220
    casaY = 60
    casalAtivo = False
    casalX = 0.0
    casalY = 0.0
    casalVel = 0.8
    casalChegouPortao = False

    # Quarto e notebook
    camaX = 90
    camaY = 100
    mesaX = 260
    mesaY = 115
    quartoLuzAcesa = False
    mulherQuartoX = 24.0
    mulherQuartoY = 185.0
    homemQuartoX = 14.0
    homemQuartoY = 190.0
    quartoEstado = "entrando"
    quartoTimer = 0
    notebookAceso = False
    cliqueDisponivel = False
    puloCliqueNotebook = 0.0

    # Animação de caminhada
    tempoPasso = 0.0

    # Toque / arrasto
    toqueAtivo = False
    toqueDestinoX = 0.0
    toqueDestinoY = 0.0

    # Texto de status (HUD)
    statusCena = "Cena 1: A Viagem Começa..."


rectNotebookTela = {'x': G.mesaX + 18, 'y': G.mesaY + 6, 'width': 12, 'height': 9}

# Registo de teclas pressionadas (nomes em minúsculas: 'w','a','s','d','arrowup'...)
teclasPressionadas = {}


# ==============================================================================
# INICIALIZAÇÃO DO PYGAME
# ==============================================================================
pygame.init()
janela = pygame.display.set_mode((LARGURA * ESCALA, ALTURA * ESCALA))
pygame.display.set_caption("Roteiro Afetivo - Um Jogo de Amor e Código")
clock = pygame.time.Clock()

# Superfície virtual onde tudo é desenhado em 400x300 antes do scaling
tela = pygame.Surface((LARGURA, ALTURA))

# Fontes (substituem 'Press Start 2P' e 'VT323')
FONT_CACHE = {}


def fonte(tam, bold=False):
    chave = (tam, bold)
    if chave not in FONT_CACHE:
        FONT_CACHE[chave] = pygame.font.SysFont("couriernew,consolas,monospace", tam, bold=bold)
    return FONT_CACHE[chave]


def texto(surf, txt, x, y, tam, cor, align='left', bold=False):
    """Desenha texto. align: 'left' | 'center' | 'right'."""
    img = fonte(tam, bold).render(txt, True, cor)
    r = img.get_rect()
    if align == 'center':
        r.midtop = (int(x), int(y))
    elif align == 'right':
        r.topright = (int(x), int(y))
    else:
        r.topleft = (int(x), int(y))
    surf.blit(img, r)


def linha_tracejada(surf, cor, x1, y, x2, dash=10, gap=10, espessura=1):
    """Desenha uma linha horizontal tracejada."""
    x = x1
    while x < x2:
        pygame.draw.line(surf, cor, (x, y), (min(x + dash, x2), y), espessura)
        x += dash + gap


# ==============================================================================
# CLASSES
# ==============================================================================
class Obstaculo:
    def __init__(self, tipo, x, y, velocidade, cor):
        self.tipo = tipo
        self.x = float(x)
        self.y = float(y)
        self.velocidade = velocidade
        self.cor = cor
        self.largura = 32 if tipo == 'carro' else 18
        self.altura = 14 if tipo == 'carro' else 11

    def atualizar(self, velJogador):
        self.x -= (self.velocidade + velJogador)

    def desenhar(self):
        x, y = self.x, self.y
        # Sombra
        pygame.draw.rect(tela, (15, 25, 15), (x + 1, y + self.altura - 2, self.largura - 2, 2))
        if self.tipo == 'carro':
            pygame.draw.rect(tela, self.cor, (x, y + 4, self.largura, self.altura - 4))
            pygame.draw.rect(tela, hx('#90afc5'), (x + 5, y, self.largura - 10, 5))
            pygame.draw.rect(tela, hx('#141416'), (x + 4, y + self.altura - 2, 5, 2))
            pygame.draw.rect(tela, hx('#141416'), (x + self.largura - 9, y + self.altura - 2, 5, 2))
            cor_farol = hx('#fff4a3') if self.velocidade < 0 else hx('#ff3333')
            pygame.draw.rect(tela, cor_farol, (x, y + 6, 1, 2))
        else:
            pygame.draw.rect(tela, self.cor, (x + 3, y + 2, self.largura - 6, self.altura - 4))
            pygame.draw.rect(tela, hx('#141416'), (x, y + self.altura - 2, 3, 2))
            pygame.draw.rect(tela, hx('#141416'), (x + self.largura - 3, y + self.altura - 2, 3, 2))
            pygame.draw.rect(tela, hx('#222222'), (x + 6, y, 5, 4))
            cor_farol = hx('#fff4a3') if self.velocidade < 0 else hx('#ff3333')
            fx = x if self.velocidade < 0 else x + self.largura - 1
            pygame.draw.rect(tela, cor_farol, (fx, y + 3, 1, 1))


class Pet:
    def __init__(self, nome, tipo, x, y, cor, corOrelhas=None, fala=""):
        self.nome = nome
        self.tipo = tipo
        self.x = x
        self.baseY = y
        self.y = y
        self.cor = cor
        self.corOrelhas = corOrelhas if corOrelhas else cor
        self.fala = fala
        self.anguloBalanco = 0.0
        self.puloOffset = 0.0
        self.feliz = False

    def atualizar(self, casalProximo):
        self.feliz = casalProximo
        if self.feliz:
            self.anguloBalanco += 0.4
            self.puloOffset = abs(math.sin(self.anguloBalanco) * 7)
        else:
            self.anguloBalanco += 0.05
            self.puloOffset = abs(math.sin(self.anguloBalanco) * 1.5)
        self.y = self.baseY - self.puloOffset

    def desenhar(self):
        x, y = self.x, self.y
        # Sombra
        pygame.draw.rect(tela, (15, 25, 15), (x + 1, self.baseY + 11, 10, 2))
        # Corpo
        pygame.draw.rect(tela, self.cor, (x + 1, y + 5, 10, 7))
        # Cabeça
        pygame.draw.rect(tela, self.cor, (x + 2, y + 1, 8, 5))
        # Olhos
        pygame.draw.rect(tela, hx('#0f0f0f'), (x + 3, y + 2, 1, 1))
        pygame.draw.rect(tela, hx('#0f0f0f'), (x + 7, y + 2, 1, 1))
        # Nariz e orelhas
        if self.tipo == 'gato':
            pygame.draw.rect(tela, hx('#e8a3a3'), (x + 5, y + 3, 1, 1))
            pygame.draw.rect(tela, self.corOrelhas, (x + 2, y, 1, 1))
            pygame.draw.rect(tela, self.corOrelhas, (x + 8, y, 1, 1))
        else:
            pygame.draw.rect(tela, hx('#111111'), (x + 5, y + 3, 2, 1))
            pygame.draw.rect(tela, self.corOrelhas, (x + 1, y + 2, 1, 3))
            pygame.draw.rect(tela, self.corOrelhas, (x + 9, y + 2, 1, 3))

        # Balão de fala
        if self.feliz and self.fala:
            f = fonte(7, bold=True)
            img = f.render(self.fala, True, hx('#000000'))
            largTexto = img.get_width()
            bw = largTexto + 6
            bh = 10
            bx = int(x + 6 - bw / 2)
            by = int(y - 14)
            # Sombra
            pygame.draw.rect(tela, (0, 0, 0), (bx + 1, by + 1, bw, bh))
            # Corpo branco
            pygame.draw.rect(tela, hx('#ffffff'), (bx, by, bw, bh))
            pygame.draw.rect(tela, hx('#000000'), (bx, by, bw, bh), 1)
            # Ponta do balão
            pts = [(x + 4, by + bh), (x + 6, by + bh + 3), (x + 8, by + bh)]
            pygame.draw.polygon(tela, hx('#ffffff'), pts)
            pygame.draw.lines(tela, hx('#000000'), False, pts, 1)
            # Texto
            tr = img.get_rect()
            tr.midtop = (int(x + 6), by + 1)
            tela.blit(img, tr)


# Criar os 5 animais de estimação
listaPets = [
    Pet("Shitzu Branca", "cao", 320, 155, hx('#f5f5f5'), hx('#d9c3b0'), "auuu"),
    Pet("Yorkshire", "cao", 350, 165, hx('#534438'), hx('#c68a4c'), "auau"),
    Pet("Shitzu Marrom", "cao", 310, 160, hx('#915f3c'), hx('#4a2f1c'), ""),
    Pet("Gato Tricolor", "gato", 340, 132, hx('#dc8c50'), hx('#222222'), ""),
    Pet("Gato Laranja", "gato", 375, 142, hx('#e66e1e'), hx('#f39c12'), "miau"),
]


class CaixaDialogo:
    def __init__(self):
        self.textoCompleto = ""
        self.textoAtual = ""
        self.ativo = False
        self.indiceLetra = 0.0
        self.velocidadeEscrita = 0.4
        self.tempoCursor = 0

    def iniciar(self, txt):
        self.textoCompleto = txt
        self.textoAtual = ""
        self.indiceLetra = 0.0
        self.ativo = True

    def atualizar(self):
        if not self.ativo:
            return
        if self.indiceLetra < len(self.textoCompleto):
            self.indiceLetra += self.velocidadeEscrita
            self.textoAtual = self.textoCompleto[:int(self.indiceLetra)]
        self.tempoCursor += 1

    def desenhar(self):
        if not self.ativo:
            return
        pygame.draw.rect(tela, COR_CAIXA_DIALOGO, (20, 220, 360, 70))
        pygame.draw.rect(tela, COR_BORDA_DIALOGO, (20, 220, 360, 70), 3)
        pygame.draw.rect(tela, hx('#2b1b11'), (23, 223, 354, 64), 1)

        f = fonte(13)
        # Quebra de linha por largura (limite ~330px)
        palavras = self.textoAtual.split(' ')
        linhas = []
        atual = ""
        for palavra in palavras:
            teste = atual + palavra + " "
            if f.size(teste)[0] < 330:
                atual = teste
            else:
                linhas.append(atual)
                atual = palavra + " "
        linhas.append(atual)

        yOff = 232
        for linha in linhas:
            texto(tela, linha, 35, yOff, 13, COR_TEXTO)
            yOff += 16

        if self.indiceLetra >= len(self.textoCompleto):
            if (self.tempoCursor // 20) % 2 == 0:
                texto(tela, "v", 363, 272, 11, COR_BORDA_DIALOGO)


caixaDialogo = CaixaDialogo()


# ==============================================================================
# LÓGICA DE CONTROLO
# ==============================================================================
def podeConduzir():
    if caixaDialogo.ativo or G.transitando:
        return False
    if G.cenaAtual == CENA_1_ESTRADA:
        return True
    if G.cenaAtual == CENA_2_KIKAO and G.kikaoEstado in ("conduzindo_para_parar", "conduzindo_para_sair"):
        return True
    if G.cenaAtual == CENA_3_VIAGEM:
        return True
    if G.cenaAtual == CENA_4_CHEGADA_CASA and G.kikaoEstado == "conduzindo_para_parar":
        return True
    return False


def podeMoverHomem():
    if caixaDialogo.ativo or G.transitando:
        return False
    return G.cenaAtual == CENA_2_KIKAO and G.kikaoEstado in ("descendo", "voltando")


def obterHitboxCarro():
    return {'x': G.carroX + 4, 'y': G.carroY + 8, 'l': 40, 'a': 11}


def k(*nomes):
    """True se alguma das teclas dadas está pressionada."""
    return any(teclasPressionadas.get(n, False) for n in nomes)


def atualizarMovimentoCarroJogador():
    if not podeConduzir():
        return
    acelerando = k('d', 'arrowright')
    travando = k('a', 'arrowleft')
    subindo = k('w', 'arrowup')
    descendo = k('s', 'arrowdown')

    if G.toqueAtivo:
        dx = G.toqueDestinoX - (G.carroX + 24)
        dy = G.toqueDestinoY - (G.carroY + 10)
        if abs(dx) > 15:
            acelerando = acelerando or dx > 0
            travando = travando or dx <= 0
        if abs(dy) > 10:
            descendo = descendo or dy > 0
            subindo = subindo or dy <= 0

    if acelerando:
        G.carroX += G.velocidadeManual
        if G.cenaAtual in (CENA_1_ESTRADA, CENA_3_VIAGEM):
            G.estradaOffset -= G.velocidadeManual
    elif travando:
        G.carroX -= G.velocidadeManual
        if G.carroX < -60:
            G.carroX = -60
        if G.cenaAtual in (CENA_1_ESTRADA, CENA_3_VIAGEM):
            G.estradaOffset += G.velocidadeManual

    if subindo:
        G.carroY -= 1.3
        if G.carroY < 170:
            G.carroY = 170
    elif descendo:
        G.carroY += 1.3
        if G.carroY > 205:
            G.carroY = 205


def atualizarMovimentoHomem():
    if not podeMoverHomem():
        return
    acelerando = k('d', 'arrowright')
    travando = k('a', 'arrowleft')
    subindo = k('w', 'arrowup')
    descendo = k('s', 'arrowdown')

    if G.toqueAtivo:
        dx = G.toqueDestinoX - (G.homemX + 5)
        dy = G.toqueDestinoY - (G.homemY + 12)
        if abs(dx) > 10:
            acelerando = acelerando or dx > 0
            travando = travando or dx <= 0
        if abs(dy) > 10:
            descendo = descendo or dy > 0
            subindo = subindo or dy <= 0

    velAndar = 1.0
    if acelerando:
        G.homemX += velAndar
    if travando:
        G.homemX -= velAndar
    if subindo:
        G.homemY -= velAndar
    if descendo:
        G.homemY += velAndar

    G.homemX = max(10, min(LARGURA - 20, G.homemX))
    G.homemY = max(120, min(210, G.homemY))


def gerenciarObstaculosEColisoes():
    if not podeConduzir() or G.cenaAtual == CENA_4_CHEGADA_CASA:
        G.listaObstaculos = []
        return

    G.timerGerarObstaculo += 1
    taxaGeracao = 35 if G.cenaAtual == CENA_3_VIAGEM else 55

    if G.timerGerarObstaculo >= taxaGeracao:
        G.timerGerarObstaculo = 0
        tipo = 'carro' if random.random() > 0.4 else 'moto'
        spawnY = 172 if random.random() > 0.5 else 200
        vemDeFrente = random.random() > 0.35
        velObstaculo = -3.8 if vemDeFrente else 0.8
        if tipo == 'carro':
            col = hx('#2980b9') if random.random() > 0.5 else hx('#27ae60')
        else:
            col = hx('#f1c40f') if random.random() > 0.5 else hx('#e67e22')
        G.listaObstaculos.append(Obstaculo(tipo, LARGURA + 30, spawnY, velObstaculo, col))

    velRefJogador = G.velocidadeManual if (k('d', 'arrowright') or
                                           (G.toqueAtivo and G.toqueDestinoX > G.carroX + 24)) else 0
    for obs in G.listaObstaculos:
        obs.atualizar(velRefJogador)

    G.listaObstaculos = [o for o in G.listaObstaculos if -50 < o.x < LARGURA + 100]

    if G.velocidadeManual < G.VELOCIDADE_ALVO:
        G.velocidadeManual += 0.04
        if G.velocidadeManual > G.VELOCIDADE_ALVO:
            G.velocidadeManual = G.VELOCIDADE_ALVO

    if G.colidirTimer > 0:
        G.colidirTimer -= 1

    if G.colidirTimer == 0:
        hb = obterHitboxCarro()
        for obs in G.listaObstaculos:
            if (hb['x'] < obs.x + obs.largura and
                    hb['x'] + hb['l'] > obs.x and
                    hb['y'] < obs.y + obs.altura and
                    hb['y'] + hb['a'] > obs.y):
                G.colidirTimer = 50
                G.velocidadeManual = 0.4
                G.carroX -= 15
                if G.carroX < -60:
                    G.carroX = -60
                G.listaObstaculos.remove(obs)
                break


def resetarVariaveisCenas():
    G.carroX = 10.0
    G.carroY = 185.0
    G.carroVel = 1.8
    G.estradaOffset = 0.0
    G.velocidadeManual = G.VELOCIDADE_ALVO
    G.listaObstaculos = []
    G.timerGerarObstaculo = 0
    G.colidirTimer = 0
    G.homemX = 0.0
    G.homemY = 0.0
    G.homemAtivo = False
    G.homemComLanche = False
    G.homemVisivel = True
    G.dinerTimer = 0
    G.kikaoEstado = "conduzindo_para_parar"
    G.casalAtivo = False
    G.casalX = 0.0
    G.casalY = 0.0
    G.casalChegouPortao = False
    G.quartoLuzAcesa = False
    G.mulherQuartoX = 24.0
    G.mulherQuartoY = 185.0
    G.homemQuartoX = 14.0
    G.homemQuartoY = 190.0
    G.quartoEstado = "entrando"
    G.quartoTimer = 0
    G.notebookAceso = False
    G.cliqueDisponivel = False
    G.tempoPasso = 0.0
    G.toqueAtivo = False
    for key in list(teclasPressionadas.keys()):
        teclasPressionadas[key] = False


def iniciarTransicao(proxima):
    if not G.transitando:
        G.transitando = True
        G.direcaoTransicao = 1
        G.proximaCena = proxima


def gerenciarTransicao():
    if not G.transitando:
        return
    G.transicaoAlfa += G.direcaoTransicao * 0.04
    if G.transicaoAlfa >= 1:
        G.transicaoAlfa = 1.0
        G.cenaAtual = G.proximaCena
        G.listaObstaculos = []
        if G.cenaAtual == CENA_2_KIKAO:
            G.carroX = -50
            G.kikaoEstado = "conduzindo_para_parar"
            G.statusCena = "Cena 2: Estaciona o carro na vaga amarela!"
        elif G.cenaAtual == CENA_3_VIAGEM:
            G.carroX = -60
            G.statusCena = "Cena 3: Desvia-te do tráfego rápido na autoestrada!"
        elif G.cenaAtual == CENA_4_CHEGADA_CASA:
            G.carroX = -60
            G.kikaoEstado = "conduzindo_para_parar"
            G.statusCena = "Cena 4: Conduz com carinho até casa..."
        elif G.cenaAtual == CENA_5_QUARTO:
            G.quartoTimer = 0
            G.quartoEstado = "entrando"
            G.mulherQuartoX = 24.0
            G.mulherQuartoY = 185.0
            G.homemQuartoX = 14.0
            G.homemQuartoY = 190.0
            G.statusCena = "Cena 5: A entrar no quarto de mãos dadas..."
        elif G.cenaAtual == CENA_6_PROGRAMACAO:
            G.statusCena = "Cena 6: Linhas de carinho e código..."
        G.direcaoTransicao = -1
    elif G.transicaoAlfa <= 0:
        G.transicaoAlfa = 0.0
        G.transitando = False


# ==============================================================================
# DESENHOS DE CENÁRIO
# ==============================================================================
def desenharRelvaComDetalhes():
    tela.fill(COR_GRAMA, (0, 0, LARGURA, ALTURA))
    cor = hx('#3f6745')
    tufos = [(20, 30), (50, 70), (110, 20), (80, 110), (150, 50), (280, 40), (350, 80),
             (310, 120), (220, 90), (40, 250), (180, 260), (290, 270), (370, 240), (90, 280)]
    for tx, ty in tufos:
        pygame.draw.rect(tela, cor, (tx, ty, 1, 2))
        pygame.draw.rect(tela, cor, (tx + 1, ty + 1, 1, 1))


def desenharArvoresPixelizadas():
    arvores = [(40, 150), (90, 145), (360, 150), (380, 155)]
    for ax, ay in arvores:
        pygame.draw.rect(tela, hx('#3c2817'), (ax - 2, ay - 8, 4, 8))
        pygame.draw.polygon(tela, hx('#224d30'), [(ax - 10, ay - 8), (ax, ay - 18), (ax + 10, ay - 8)])
        pygame.draw.polygon(tela, hx('#295c3a'), [(ax - 8, ay - 14), (ax, ay - 24), (ax + 8, ay - 14)])
        pygame.draw.polygon(tela, hx('#316b43'), [(ax - 5, ay - 20), (ax, ay - 29), (ax + 5, ay - 20)])


def desenharCarroPixel(x, y):
    flash = G.colidirTimer > 0 and (G.colidirTimer // 4) % 2 == 0
    if flash:
        sup = pygame.Surface((LARGURA, ALTURA), pygame.SRCALPHA)
        alvo = sup
    else:
        alvo = tela

    # Sombra
    pygame.draw.rect(alvo, (15, 25, 15), (x + 2, y + 21, 44, 5))
    # Chassi
    pygame.draw.rect(alvo, hx('#b02a2a'), (x, y + 8, 48, 12))
    pygame.draw.rect(alvo, hx('#6e1111'), (x, y + 19, 48, 1))
    pygame.draw.rect(alvo, hx('#6e1111'), (x, y + 8, 1, 11))
    # Cabine
    pygame.draw.rect(alvo, hx('#99b3ca'), (x + 10, y, 26, 9))
    pygame.draw.rect(alvo, hx('#ffffff'), (x + 13, y + 2, 4, 4))
    pygame.draw.rect(alvo, hx('#ffffff'), (x + 26, y + 2, 5, 4))
    # Rodas
    pygame.draw.rect(alvo, hx('#141416'), (x + 8, y + 17, 8, 6))
    pygame.draw.rect(alvo, hx('#141416'), (x + 32, y + 17, 8, 6))
    pygame.draw.rect(alvo, hx('#7a7a82'), (x + 11, y + 19, 2, 2))
    pygame.draw.rect(alvo, hx('#7a7a82'), (x + 35, y + 19, 2, 2))
    # Faróis
    pygame.draw.rect(alvo, hx('#ff3333'), (x, y + 10, 1, 3))
    pygame.draw.rect(alvo, hx('#fff4a3'), (x + 47, y + 11, 1, 3))

    # Cone de luz dianteiro (cenas 3 e 4)
    if G.cenaAtual in (CENA_3_VIAGEM, CENA_4_CHEGADA_CASA):
        cone = pygame.Surface((LARGURA, ALTURA), pygame.SRCALPHA)
        pygame.draw.polygon(cone, (255, 244, 163, 70),
                            [(x + 48, y + 11), (x + 85, y + 2), (x + 85, y + 22)])
        alvo.blit(cone, (0, 0))

    if flash:
        sup.set_alpha(90)  # ~0.35 de opacidade
        tela.blit(sup, (0, 0))

    # Alerta "OPS!" (sempre opaco)
    if G.colidirTimer > 20:
        texto(tela, "OPS!", x + 24, y - 14, 9, hx('#e74c3c'), align='center', bold=True)


def desenharHomemPixel(x, y, bobbing=False):
    bobY = math.floor(math.sin(G.tempoPasso * 0.8) * 1.5) if bobbing else 0
    pygame.draw.rect(tela, (15, 25, 15), (x + 1, y + 25, 10, 2))
    pygame.draw.rect(tela, hx('#1f2d3d'), (x + 2, y + 18 + bobY, 3, 8 - bobY))
    pygame.draw.rect(tela, hx('#1f2d3d'), (x + 7, y + 18 + bobY, 3, 8 - bobY))
    pygame.draw.rect(tela, hx('#225d87'), (x + 1, y + 10 + bobY, 10, 9))
    pygame.draw.rect(tela, hx('#174363'), (x + 3, y + 9 + bobY, 6, 2))
    pygame.draw.rect(tela, hx('#f9cba0'), (x + 2, y + 3 + bobY, 8, 7))
    pygame.draw.rect(tela, hx('#4f2c15'), (x + 1, y + 1 + bobY, 10, 3))
    pygame.draw.rect(tela, hx('#4f2c15'), (x + 1, y + 3 + bobY, 2, 3))
    pygame.draw.rect(tela, hx('#4f2c15'), (x + 9, y + 3 + bobY, 2, 2))
    pygame.draw.rect(tela, hx('#111111'), (x + 4, y + 5 + bobY, 1, 1))
    pygame.draw.rect(tela, hx('#111111'), (x + 7, y + 5 + bobY, 1, 1))


def desenharMulherPixel(x, y, bobbing=False):
    bobY = math.floor(math.sin(G.tempoPasso * 0.8) * 1.5) if bobbing else 0
    pygame.draw.rect(tela, (15, 25, 15), (x + 1, y + 25, 10, 2))
    pygame.draw.rect(tela, hx('#261b2e'), (x + 2, y + 18 + bobY, 3, 8 - bobY))
    pygame.draw.rect(tela, hx('#261b2e'), (x + 7, y + 18 + bobY, 3, 8 - bobY))
    pygame.draw.rect(tela, hx('#b33c70'), (x + 1, y + 10 + bobY, 10, 9))
    pygame.draw.rect(tela, hx('#f9cba0'), (x + 2, y + 3 + bobY, 8, 7))
    pygame.draw.rect(tela, hx('#e8c851'), (x + 1, y + 1 + bobY, 10, 3))
    pygame.draw.rect(tela, hx('#e8c851'), (x + 1, y + 4 + bobY, 2, 7))
    pygame.draw.rect(tela, hx('#e8c851'), (x + 9, y + 4 + bobY, 2, 7))
    pygame.draw.rect(tela, hx('#111111'), (x + 4, y + 5 + bobY, 1, 1))
    pygame.draw.rect(tela, hx('#111111'), (x + 7, y + 5 + bobY, 1, 1))


def desenharLanchoneteKikaoPixel():
    pygame.draw.rect(tela, hx('#d97d26'), (150, 75, 120, 75))
    pygame.draw.rect(tela, hx('#9e5311'), (150, 149, 120, 1))
    pygame.draw.rect(tela, hx('#a82c2c'), (140, 65, 140, 11))
    pygame.draw.rect(tela, hx('#cc3b3b'), (140, 63, 140, 2))
    pygame.draw.rect(tela, hx('#422712'), (200, 120, 20, 30))
    pygame.draw.rect(tela, hx('#ffd700'), (216, 134, 1, 2))
    pygame.draw.rect(tela, hx('#519bb3'), (160, 95, 25, 20))
    pygame.draw.rect(tela, hx('#519bb3'), (235, 95, 25, 20))
    pygame.draw.rect(tela, hx('#ffffff'), (165, 95, 2, 20))
    pygame.draw.rect(tela, hx('#ffffff'), (240, 95, 2, 20))
    pygame.draw.rect(tela, hx('#422712'), (160, 95, 25, 20), 1)
    pygame.draw.rect(tela, hx('#422712'), (235, 95, 25, 20), 1)
    pygame.draw.rect(tela, hx('#ffd700'), (170, 40, 80, 20))
    pygame.draw.rect(tela, hx('#2b1c11'), (170, 40, 80, 20), 2)
    texto(tela, "KIKAO", 210, 44, 10, hx('#a82c2c'), align='center', bold=True)


def desenharCasaPortaoPixel():
    cx, cy = G.casaX, G.casaY
    pygame.draw.rect(tela, hx('#c9ab81'), (cx, cy, 120, 80))
    pygame.draw.polygon(tela, hx('#8f3333'), [(cx - 10, cy), (cx + 60, cy - 45), (cx + 130, cy)])
    pygame.draw.rect(tela, hx('#a83e3e'), (cx - 10, cy - 1, 140, 2))
    pygame.draw.rect(tela, hx('#3d2514'), (cx + 25, cy + 45, 20, 35))
    pygame.draw.rect(tela, hx('#fce588'), (cx + 41, cy + 62, 1, 2))
    pygame.draw.rect(tela, hx('#fce588'), (cx + 75, cy + 25, 25, 20))
    pygame.draw.rect(tela, hx('#3d2514'), (cx + 75, cy + 25, 25, 20), 1)
    pygame.draw.rect(tela, hx('#3d2514'), (cx + 87, cy + 25, 1, 20))
    pygame.draw.rect(tela, hx('#3d2514'), (cx + 75, cy + 35, 25, 1))
    pygame.draw.rect(tela, hx('#7a7671'), (cx + 120, cy + 40, 60, 40))
    gx = cx + 124
    while gx < LARGURA:
        pygame.draw.line(tela, hx('#3d3f42'), (gx, cy + 30), (gx, cy + 80), 1)
        gx += 8
    pygame.draw.line(tela, hx('#3d3f42'), (cx + 120, cy + 30), (LARGURA, cy + 30), 1)


# ==============================================================================
# DESENHO DO QUARTO
# ==============================================================================
def desenharElipse(cx, cy, rx, ry, cor):
    pygame.draw.ellipse(tela, cor, (cx - rx, cy - ry, rx * 2, ry * 2))


def desenharQuarto():
    tela.fill(hx('#2c2235'), (0, 0, LARGURA, ALTURA))
    pygame.draw.rect(tela, hx('#523625'), (0, 210, LARGURA, 90))
    for yy in range(210, ALTURA, 15):
        pygame.draw.line(tela, hx('#382215'), (0, yy), (LARGURA, yy), 1)

    desenharElipse(G.camaX + 30, G.camaY + 110, 45, 15, hx('#3f566e'))

    # Porta principal esquerda
    pygame.draw.rect(tela, hx('#4c311f'), (10, 140, 14, 70))
    pygame.draw.rect(tela, hx('#25160d'), (10, 140, 14, 70), 2)
    pygame.draw.rect(tela, hx('#9e714b'), (10, 140, 14, 70), 1)
    pygame.draw.rect(tela, hx('#ffd15c'), (20, 175, 2, 3))

    # Janela
    cor_janela = hx('#ffd15c') if G.quartoLuzAcesa else hx('#111528')
    pygame.draw.rect(tela, cor_janela, (40, 40, 60, 50))
    pygame.draw.rect(tela, hx('#1e110a'), (40, 40, 60, 50), 2)
    pygame.draw.line(tela, hx('#1e110a'), (70, 40), (70, 90), 1)
    pygame.draw.line(tela, hx('#1e110a'), (40, 65), (100, 65), 1)

    # Cama
    pygame.draw.rect(tela, hx('#6e4424'), (G.camaX, G.camaY, 60, 120))
    pygame.draw.rect(tela, hx('#e3e3f0'), (G.camaX + 2, G.camaY + 28, 56, 92))
    pygame.draw.rect(tela, hx('#ffffff'), (G.camaX + 6, G.camaY + 6, 20, 15))
    pygame.draw.rect(tela, hx('#ffffff'), (G.camaX + 34, G.camaY + 6, 20, 15))

    # Mesa
    pygame.draw.rect(tela, hx('#5c3d25'), (G.mesaX, G.mesaY, 55, 60))
    pygame.draw.rect(tela, hx('#331f11'), (G.mesaX + 2, G.mesaY + 60, 4, 30))
    pygame.draw.rect(tela, hx('#331f11'), (G.mesaX + 49, G.mesaY + 60, 4, 30))
    pygame.draw.rect(tela, hx('#382215'), (G.mesaX + 8, G.mesaY + 65, 14, 20))
    pygame.draw.rect(tela, hx('#382215'), (G.mesaX + 13, G.mesaY + 85, 3, 10))
    pygame.draw.rect(tela, hx('#68686d'), (G.mesaX + 15, G.mesaY + 20, 20, 4))

    if G.notebookAceso:
        pygame.draw.rect(tela, hx('#a1e4ff'),
                         (rectNotebookTela['x'], rectNotebookTela['y'],
                          rectNotebookTela['width'], rectNotebookTela['height']))
    else:
        pygame.draw.rect(tela, hx('#1e1e24'), (G.mesaX + 18, G.mesaY + 10, 15, 10))


# ==============================================================================
# MÁQUINA DE ESTADOS (ATUALIZAR)
# ==============================================================================
def atualizar():
    gerenciarTransicao()
    caixaDialogo.atualizar()

    if caixaDialogo.ativo:
        return

    G.tempoPasso += 0.2

    if G.cenaAtual == CENA_1_ESTRADA:
        if G.carroX >= LARGURA:
            iniciarTransicao(CENA_2_KIKAO)

    elif G.cenaAtual == CENA_2_KIKAO:
        if G.kikaoEstado == "conduzindo_para_parar":
            ccx = G.carroX + 24
            ccy = G.carroY + 10
            if 85 <= ccx <= 135 and 180 <= ccy <= 202:
                G.kikaoEstado = "descendo"
                G.homemX = G.carroX + 15
                G.homemY = G.carroY - 5
                G.homemAtivo = True
                G.homemVisivel = True
                G.homemComLanche = False
                G.statusCena = "Cena 2: Caminha até à porta da lanchonete!"
        elif G.kikaoEstado == "descendo":
            feetX = G.homemX + 5
            feetY = G.homemY + 25
            if abs(feetX - 210) < 12 and feetY <= 150:
                G.homemVisivel = False
                G.kikaoEstado = "comprando"
                G.dinerTimer = 0
                G.statusCena = "Cena 2: À espera do lanche... Quase pronto!"
        elif G.kikaoEstado == "comprando":
            G.dinerTimer += 1
            if G.dinerTimer >= 100:
                G.homemVisivel = True
                G.homemComLanche = True
                G.homemX = 205
                G.homemY = 125
                G.kikaoEstado = "voltando"
                G.statusCena = "Cena 2: Lanche na mão! Volta para o carro!"
        elif G.kikaoEstado == "voltando":
            mcx = G.homemX + 5
            mcy = G.homemY + 12
            ccx = G.carroX + 24
            ccy = G.carroY + 10
            if math.hypot(mcx - ccx, mcy - ccy) < 22:
                G.homemAtivo = False
                G.kikaoEstado = "conduzindo_para_sair"
                G.statusCena = "Cena 2: Tudo pronto, conduz para a direita!"
        elif G.kikaoEstado == "conduzindo_para_sair":
            if G.carroX > LARGURA:
                iniciarTransicao(CENA_3_VIAGEM)

    elif G.cenaAtual == CENA_3_VIAGEM:
        if G.carroX > LARGURA:
            iniciarTransicao(CENA_4_CHEGADA_CASA)

    elif G.cenaAtual == CENA_4_CHEGADA_CASA:
        if G.kikaoEstado == "conduzindo_para_parar":
            if G.carroX >= 60:
                G.carroX = 60
                G.kikaoEstado = "casal_andando"
                G.casalX = G.carroX + 15
                G.casalY = G.carroY - 15
                G.casalAtivo = True
        elif G.kikaoEstado == "casal_andando":
            alvoX = G.casaX + 115
            alvoY = G.casaY + 90
            dx = alvoX - G.casalX
            dy = alvoY - G.casalY
            dist = math.hypot(dx, dy)
            casalProximo = dist < 110
            for pet in listaPets:
                pet.atualizar(casalProximo)
            if dist > 2:
                G.casalX += (dx / dist) * G.casalVel
                G.casalY += (dy / dist) * G.casalVel
            else:
                G.kikaoEstado = "casal_entrando_casa"
        elif G.kikaoEstado == "casal_entrando_casa":
            alvoX = G.casaX + 35
            alvoY = G.casaY + 68
            dx = alvoX - G.casalX
            dy = alvoY - G.casalY
            dist = math.hypot(dx, dy)
            for pet in listaPets:
                pet.atualizar(True)
            if dist > 2:
                G.casalX += (dx / dist) * G.casalVel
                G.casalY += (dy / dist) * G.casalVel
            else:
                if not G.casalChegouPortao:
                    G.casalChegouPortao = True
                    G.casalAtivo = False
                    iniciarTransicao(CENA_5_QUARTO)

    elif G.cenaAtual == CENA_5_QUARTO:
        if G.quartoEstado == "entrando":
            alvoXM = G.camaX + 10
            alvoYM = G.camaY + 10
            dxM = alvoXM - G.mulherQuartoX
            dyM = alvoYM - G.mulherQuartoY
            distM = math.hypot(dxM, dyM)

            alvoXH = G.camaX + 40
            alvoYH = G.camaY + 10
            dxH = alvoXH - G.homemQuartoX
            dyH = alvoYH - G.homemQuartoY
            distH = math.hypot(dxH, dyH)

            if distM > 1.5:
                G.mulherQuartoX += (dxM / distM) * 0.8
                G.mulherQuartoY += (dyM / distM) * 0.8
            if distH > 1.5:
                G.homemQuartoX += (dxH / distH) * 0.8
                G.homemQuartoY += (dyH / distH) * 0.8

            if distM <= 1.5 and distH <= 1.5:
                G.quartoEstado = "dormindo"
                G.quartoTimer = 0
        else:
            G.quartoTimer += 1
            if G.quartoEstado == "dormindo":
                if G.quartoTimer >= 140:
                    G.quartoLuzAcesa = True
                    G.quartoEstado = "acordando"
                    G.quartoTimer = 0
            elif G.quartoEstado == "acordando":
                if G.quartoTimer >= 40:
                    G.quartoEstado = "andando"
            elif G.quartoEstado == "andando":
                alvoX = G.mesaX + 8
                alvoY = G.mesaY + 25
                dx = alvoX - G.mulherQuartoX
                dy = alvoY - G.mulherQuartoY
                dist = math.hypot(dx, dy)
                if dist > 1.5:
                    G.mulherQuartoX += (dx / dist) * 0.8
                    G.mulherQuartoY += (dy / dist) * 0.8
                else:
                    G.notebookAceso = True
                    G.quartoEstado = "programando"
                    iniciarTransicao(CENA_6_PROGRAMACAO)

    elif G.cenaAtual == CENA_6_PROGRAMACAO:
        G.cliqueDisponivel = True
        G.puloCliqueNotebook += 0.08


# ==============================================================================
# DESENHAR QUADROS
# ==============================================================================
def desenhar():
    shakeX = shakeY = 0
    if G.colidirTimer > 35:
        shakeX = (random.random() - 0.5) * 4.5
        shakeY = (random.random() - 0.5) * 4.5

    tela.fill((0, 0, 0))

    # Cria uma sub-superfície deslocada para o screen shake desenhando tudo
    # diretamente em 'tela' e depois deslocando no blit final é complexo;
    # aqui aplicamos o shake no blit para a janela.

    if G.cenaAtual == CENA_1_ESTRADA:
        desenharRelvaComDetalhes()
        desenharArvoresPixelizadas()
        tela.fill(COR_CEU_DIA, (0, 0, LARGURA, 90))
        pygame.draw.circle(tela, hx('#fff9d4'), (320, 45), 14)
        tela.fill(COR_ASFALTO, (0, 165, LARGURA, 65))
        linha_tracejada(tela, hx('#f39c12'), 0, 197, LARGURA)
        for obs in G.listaObstaculos:
            obs.desenhar()
        desenharCarroPixel(G.carroX, G.carroY)

    elif G.cenaAtual == CENA_2_KIKAO:
        desenharRelvaComDetalhes()
        desenharArvoresPixelizadas()
        tela.fill(COR_ASFALTO, (0, 165, LARGURA, 65))
        pygame.draw.line(tela, hx('#f39c12'), (0, 197), (LARGURA, 197), 1)
        desenharLanchoneteKikaoPixel()
        if G.kikaoEstado == "conduzindo_para_parar":
            pygame.draw.rect(tela, hx('#ffd700'), (85, 180, 50, 22), 1)
            texto(tela, "VAGA", 110, 168, 10, hx('#ffd700'), align='center')
        if G.kikaoEstado == "comprando":
            barX, barY, barW, barH = 190, 105, 40, 5
            pygame.draw.rect(tela, hx('#1e1e24'), (barX, barY, barW, barH))
            prog = min(G.dinerTimer / 100, 1.0)
            pygame.draw.rect(tela, hx('#27ae60'), (barX, barY, int(barW * prog), barH))
            pygame.draw.rect(tela, hx('#9e714b'), (barX, barY, barW, barH), 1)
        for obs in G.listaObstaculos:
            obs.desenhar()
        desenharCarroPixel(G.carroX, G.carroY)
        if G.homemAtivo and G.homemVisivel:
            desenharHomemPixel(G.homemX, G.homemY, True)
            if G.homemComLanche:
                pygame.draw.rect(tela, hx('#ffffff'), (G.homemX + 10, G.homemY - 11, 8, 8))
                pygame.draw.rect(tela, hx('#6e3811'), (G.homemX + 11, G.homemY - 8, 6, 3))
                pygame.draw.rect(tela, hx('#228b22'), (G.homemX + 11, G.homemY - 9, 6, 1))

    elif G.cenaAtual == CENA_3_VIAGEM:
        desenharRelvaComDetalhes()
        desenharArvoresPixelizadas()
        tela.fill(COR_CEU_ENTARDECER, (0, 0, LARGURA, 90))
        pygame.draw.circle(tela, hx('#e8a85e'), (300, 60), 12)
        tela.fill(COR_ASFALTO, (0, 165, LARGURA, 65))
        linha_tracejada(tela, hx('#f39c12'), 0, 197, LARGURA)
        for obs in G.listaObstaculos:
            obs.desenhar()
        desenharCarroPixel(G.carroX, G.carroY)

    elif G.cenaAtual == CENA_4_CHEGADA_CASA:
        desenharRelvaComDetalhes()
        tela.fill(hx('#5c544e'), (200, 140, 200, 50))
        cx = 208
        while cx < LARGURA:
            pygame.draw.rect(tela, hx('#45403c'), (cx, 140, 1, 50))
            cx += 16
        desenharCasaPortaoPixel()
        tela.fill(COR_ASFALTO, (0, 180, LARGURA, 55))
        pygame.draw.line(tela, hx('#f39c12'), (0, 207), (LARGURA, 207), 1)
        desenharCarroPixel(G.carroX, G.carroY)
        for pet in listaPets:
            pet.desenhar()
        if G.casalAtivo:
            desenharMulherPixel(G.casalX, G.casalY, True)
            desenharHomemPixel(G.casalX - 10, G.casalY + 1, True)

    elif G.cenaAtual == CENA_5_QUARTO:
        desenharQuarto()
        if G.quartoEstado == "entrando":
            desenharMulherPixel(G.mulherQuartoX, G.mulherQuartoY, True)
            desenharHomemPixel(G.homemQuartoX, G.homemQuartoY, True)
        elif G.quartoEstado == "dormindo":
            desenharMulherPixel(G.camaX + 10, G.camaY + 10)
            desenharHomemPixel(G.camaX + 40, G.camaY + 10)
            pygame.draw.rect(tela, hx('#cfcfe0'), (G.camaX + 2, G.camaY + 28, 56, 92))
        else:
            desenharHomemPixel(G.camaX + 40, G.camaY + 10)
            pygame.draw.rect(tela, hx('#cfcfe0'), (G.camaX + 2, G.camaY + 28, 56, 92))
            desenharMulherPixel(G.mulherQuartoX, G.mulherQuartoY, True)

        overlay = pygame.Surface((LARGURA, ALTURA), pygame.SRCALPHA)
        if not G.quartoLuzAcesa:
            overlay.fill((12, 10, 24, int(0.72 * 255)))
        else:
            overlay.fill((255, 215, 120, int(0.08 * 255)))
        tela.blit(overlay, (0, 0))

    elif G.cenaAtual == CENA_6_PROGRAMACAO:
        desenharQuarto()
        desenharHomemPixel(G.camaX + 40, G.camaY + 10)
        pygame.draw.rect(tela, hx('#cfcfe0'), (G.camaX + 2, G.camaY + 28, 56, 92))
        desenharMulherPixel(G.mulherQuartoX, G.mulherQuartoY)

        overlay = pygame.Surface((LARGURA, ALTURA), pygame.SRCALPHA)
        overlay.fill((255, 215, 120, int(0.08 * 255)))
        tela.blit(overlay, (0, 0))

        if G.cliqueDisponivel and not caixaDialogo.ativo:
            pulso = abs(math.sin(G.puloCliqueNotebook) * 4)
            pygame.draw.circle(tela, hx('#ffffff'),
                               (rectNotebookTela['x'] + 6, rectNotebookTela['y'] + 4),
                               int(10 + pulso), 1)
            offsetY = math.sin(G.puloCliqueNotebook * 1.5) * 3
            texto(tela, "TOCA AQUI", rectNotebookTela['x'] + 6,
                  rectNotebookTela['y'] - 18 + offsetY, 11, hx('#ffffff'), align='center')

        if not caixaDialogo.ativo and not G.cliqueDisponivel:
            esc = pygame.Surface((LARGURA, ALTURA), pygame.SRCALPHA)
            esc.fill((15, 12, 12, int(0.88 * 255)))
            tela.blit(esc, (0, 0))
            texto(tela, "FIM DA HISTORIA <3", LARGURA // 2, ALTURA // 2 - 22,
                  18, COR_BORDA_DIALOGO, align='center', bold=True)
            texto(tela, "Pressiona 'R' para reiniciar", LARGURA // 2, ALTURA // 2 + 12,
                  14, COR_TEXTO, align='center')

    # HUD de controlo
    if podeConduzir() or podeMoverHomem():
        hud = pygame.Surface((205, 18), pygame.SRCALPHA)
        hud.fill((20, 20, 20, int(0.72 * 255)))
        tela.blit(hud, (8, 8))
        txt = "CONTROLO: CONDUZ O TEU CARRO!" if podeConduzir() else "CONTROLO: MOVIMENTA O RAPAZ A PE!"
        texto(tela, txt, 12, 11, 10, hx('#ffffff'))

    # Caixa de diálogo
    caixaDialogo.desenhar()

    # Camada de transição
    if G.transicaoAlfa > 0:
        fade = pygame.Surface((LARGURA, ALTURA), pygame.SRCALPHA)
        fade.fill((0, 0, 0, int(G.transicaoAlfa * 255)))
        tela.blit(fade, (0, 0))

    # Escala para a janela (com screen shake aplicado no destino)
    escalada = pygame.transform.scale(tela, (LARGURA * ESCALA, ALTURA * ESCALA))
    janela.fill((0, 0, 0))
    janela.blit(escalada, (int(shakeX * ESCALA), int(shakeY * ESCALA)))


# ==============================================================================
# INTERAÇÕES DO JOGADOR
# ==============================================================================
def avancarDialogo():
    if caixaDialogo.indiceLetra >= len(caixaDialogo.textoCompleto):
        caixaDialogo.ativo = False
        G.cliqueDisponivel = False
    else:
        caixaDialogo.indiceLetra = float(len(caixaDialogo.textoCompleto))
        caixaDialogo.textoAtual = caixaDialogo.textoCompleto


def tratarClique(mx_janela, my_janela):
    mouseX = mx_janela / ESCALA
    mouseY = my_janela / ESCALA
    if caixaDialogo.ativo:
        avancarDialogo()
        return
    if G.cenaAtual == CENA_6_PROGRAMACAO and G.cliqueDisponivel:
        rt = rectNotebookTela
        if (rt['x'] - 6 <= mouseX <= rt['x'] + rt['width'] + 6 and
                rt['y'] - 6 <= mouseY <= rt['y'] + rt['height'] + 6):
            caixaDialogo.iniciar("[Mulher]: Pronto, agora posso continuar a programar o nosso jogo...")


# Mapeamento de teclas físicas pygame -> nomes usados internamente
TECLA_NOME = {
    pygame.K_w: 'w', pygame.K_a: 'a', pygame.K_s: 's', pygame.K_d: 'd',
    pygame.K_UP: 'arrowup', pygame.K_DOWN: 'arrowdown',
    pygame.K_LEFT: 'arrowleft', pygame.K_RIGHT: 'arrowright',
}


# ==============================================================================
# LOOP PRINCIPAL
# ==============================================================================
def main():
    rodando = True
    while rodando:
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                rodando = False

            elif evento.type == pygame.KEYDOWN:
                nome = TECLA_NOME.get(evento.key)
                if nome:
                    teclasPressionadas[nome] = True
                if evento.key == pygame.K_RETURN:
                    if caixaDialogo.ativo:
                        avancarDialogo()
                elif evento.key == pygame.K_r:
                    if (G.cenaAtual == CENA_6_PROGRAMACAO and
                            not G.cliqueDisponivel and not caixaDialogo.ativo):
                        resetarVariaveisCenas()
                        iniciarTransicao(CENA_1_ESTRADA)

            elif evento.type == pygame.KEYUP:
                nome = TECLA_NOME.get(evento.key)
                if nome:
                    teclasPressionadas[nome] = False

            elif evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
                if podeConduzir() or podeMoverHomem():
                    G.toqueDestinoX = evento.pos[0] / ESCALA
                    G.toqueDestinoY = evento.pos[1] / ESCALA
                    G.toqueAtivo = True
                else:
                    tratarClique(evento.pos[0], evento.pos[1])

            elif evento.type == pygame.MOUSEMOTION:
                if G.toqueAtivo and (podeConduzir() or podeMoverHomem()):
                    G.toqueDestinoX = evento.pos[0] / ESCALA
                    G.toqueDestinoY = evento.pos[1] / ESCALA

            elif evento.type == pygame.MOUSEBUTTONUP and evento.button == 1:
                G.toqueAtivo = False

        # Update
        atualizarMovimentoCarroJogador()
        atualizarMovimentoHomem()
        gerenciarObstaculosEColisoes()
        atualizar()

        # Render
        desenhar()
        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()


if __name__ == "__main__":
    main()
