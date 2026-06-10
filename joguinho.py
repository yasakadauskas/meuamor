# -*- coding: utf-8 -*-
"""
ROTEIRO AFETIVO - Uma aventura pixelizada acolhedora de carinho e código.

Versão Python (pygame).

Como rodar (precisa de Python instalado):
    python roteiro_afetivo.py
    (o pygame é instalado automaticamente na primeira execução se faltar)

Como gerar um executável para qualquer PC SEM Python:
    Windows:  duplo-clique em build_windows.bat  (ou via GitHub Actions)
    -> gera dist/RoteiroAfetivo.exe

>>> SOBRE O VÍDEO E MÚSICA <<<
Coloca o teu vídeo na MESMA PASTA do jogo (ao lado do .exe), de preferência
chamado:  meu_video.mp4   (também aceita .mov .avi .mkv .webm .m4v, ou qualquer
vídeo que estiver na pasta).
Coloca o arquivo  videoplayback.mp3  também na MESMA PASTA do jogo.

Controlos:
    - WASD ou setas: move o carro / o casal / a Mimi (em TODAS as cenas).
    - Clica e arrasta com o rato dentro do ecrã para guiar também.
    - ENTER ou clique avança os diálogos.
    - R reinicia.
    - P pausa.  M muta o som.  + / - ajusta o volume.  F11 tela cheia.
"""

import math
import random
import sys
import os
import subprocess
import array


def _garantir_pygame():
    try:
        import pygame  # noqa: F401
        return
    except ImportError:
        pass
    if getattr(sys, "frozen", False):
        raise SystemExit("pygame não encontrado no executável empacotado.")
    print("pygame não encontrado. A tentar instalar automaticamente...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pygame"])
    except Exception as e:
        raise SystemExit(
            "Não foi possível instalar o pygame automaticamente.\n"
            "Instala manualmente com:  pip install pygame\n"
            f"Detalhe do erro: {e}"
        )


_garantir_pygame()
import pygame


# ==============================================================================
# CONFIGURAÇÃO
# ==============================================================================
LARGURA = 400
ALTURA = 300
ESCALA = 2
FPS = 60

VIDEO_EXTS = ('.mp4', '.mov', '.avi', '.mkv', '.webm', '.m4v', '.wmv')
VIDEO_PREFERIDOS = ('meu_video', 'video', 'nosso_video', 'mimi')


def hx(s):
    s = s.lstrip('#')
    return (int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16))


def lerp(a, b, t):
    return a + (b - a) * t


def lerp_cor(c1, c2, t):
    return (int(lerp(c1[0], c2[0], t)), int(lerp(c1[1], c2[1], t)), int(lerp(c1[2], c2[2], t)))


def clamp(v, lo, hi):
    return lo if v < lo else hi if v > hi else v


def pasta_base():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def encontrar_video():
    base = pasta_base()
    try:
        arquivos = os.listdir(base)
    except OSError:
        arquivos = []
    for nome in VIDEO_PREFERIDOS:
        for ext in VIDEO_EXTS:
            p = os.path.join(base, nome + ext)
            if os.path.exists(p):
                return p
    for f in sorted(arquivos):
        if f.lower().endswith(VIDEO_EXTS):
            return os.path.join(base, f)
    return None


def encontrar_cartinha():
    """Procura um arquivo carta.txt ou similar na pasta do jogo."""
    base = pasta_base()
    nomes = ('carta', 'cartinha', 'mensagem', 'letter', 'minha_carta')
    for nome in nomes:
        for ext in ('.txt', '.md'):
            p = os.path.join(base, nome + ext)
            if os.path.exists(p):
                return p
    return None


def reproduzir_video():
    cam = encontrar_video()
    if not cam:
        G.videoMsg = "Coloca um video (.mp4) na pasta do jogo!"
        G.videoExiste = False
        return
    G.videoExiste = True
    try:
        if sys.platform.startswith('win'):
            os.startfile(cam)
        elif sys.platform == 'darwin':
            subprocess.Popen(['open', cam])
        else:
            subprocess.Popen(['xdg-open', cam])
        G.videoMsg = "A reproduzir no teu leitor de video..."
    except Exception:
        G.videoMsg = "Nao consegui abrir o video."


def abrir_cartinha():
    cam = encontrar_cartinha()
    if cam:
        try:
            if sys.platform.startswith('win'):
                os.startfile(cam)
            elif sys.platform == 'darwin':
                subprocess.Popen(['open', cam])
            else:
                subprocess.Popen(['xdg-open', cam])
            G.cartaMsg = "Abrindo a cartinha..."
            return
        except Exception:
            pass
    # Se não encontrou arquivo, mostra mensagem embutida
    G.mostrarCartinha = True
    G.cartaMsg = ""


# Paleta
COR_ASFALTO = hx('#3a4248')
COR_GRAMA = hx('#4a7551')
COR_CAIXA_DIALOGO = hx('#4e311f')
COR_BORDA_DIALOGO = hx('#caa074')
COR_TEXTO = hx('#fcf5db')

# Cenas
CENA_INTRO = 0
CENA_1_ESTRADA = 1
CENA_2_KIKAO = 2
CENA_3_VIAGEM = 3
CENA_4_CHEGADA_CASA = 4
CENA_5_QUARTO = 5
CENA_6_PROGRAMACAO = 6
CENA_DENTRO_CARRO = 7  # cena de abertura: visão de dentro do carro


# ==============================================================================
# SOM PROCEDURAL
# ==============================================================================
pygame.mixer.pre_init(44100, -16, 2, 512)
pygame.init()
pygame.mixer.init(44100, -16, 2, 512)

SAMPLE_RATE = 44100
SONS_OK = False


def _buf(n):
    return array.array('h', [0] * n)


def _gerar_som_motor():
    ms = 800
    n = int(SAMPLE_RATE * ms / 1000)
    buf = _buf(n)
    for i in range(n):
        t = i / SAMPLE_RATE
        v = (math.sin(2 * math.pi * 80 * t) * 0.4 +
             math.sin(2 * math.pi * 160 * t) * 0.3 +
             (random.random() - 0.5) * 0.15)
        buf[i] = int(clamp(v, -1, 1) * 0.25 * 32767)
    return pygame.sndarray.make_sound(buf)


def _gerar_som_passos():
    n = int(SAMPLE_RATE * 0.12)
    buf = _buf(n)
    for i in range(n):
        env = 1.0 - (i / n) ** 0.5
        buf[i] = int((random.random() - 0.5) * 2 * env * 0.35 * 32767)
    return pygame.sndarray.make_sound(buf)


def _gerar_som_colisao():
    n = int(SAMPLE_RATE * 0.25)
    buf = _buf(n)
    for i in range(n):
        t = i / SAMPLE_RATE
        env = (1.0 - i / n) ** 0.3
        freq = max(30, 200 - t * 400)
        v = math.sin(2 * math.pi * freq * t) * env + (random.random() - 0.5) * 0.4 * env
        buf[i] = int(clamp(v, -1, 1) * 0.5 * 32767)
    return pygame.sndarray.make_sound(buf)


def _gerar_bip(freq, ms, vol=0.2):
    n = int(SAMPLE_RATE * ms / 1000)
    buf = _buf(n)
    for i in range(n):
        env = math.sin(math.pi * i / n)
        buf[i] = int(math.sin(2 * math.pi * freq * i / SAMPLE_RATE) * env * vol * 32767)
    return pygame.sndarray.make_sound(buf)


def _gerar_transicao():
    n = int(SAMPLE_RATE * 0.55)
    buf = _buf(n)
    for i in range(n):
        t = i / SAMPLE_RATE
        freq = 220 + (i / n) * 440
        env = math.sin(math.pi * i / n)
        buf[i] = int(math.sin(2 * math.pi * freq * t) * env * 0.28 * 32767)
    return pygame.sndarray.make_sound(buf)


def _gerar_fanfarra():
    notas = [(523, 0.14), (659, 0.14), (784, 0.24)]
    total = sum(d for _, d in notas)
    n = int(SAMPLE_RATE * total)
    buf = _buf(n)
    pos = 0
    for freq, dur in notas:
        sn = int(SAMPLE_RATE * dur)
        for i in range(sn):
            if pos + i < n:
                env = math.sin(math.pi * i / sn)
                buf[pos + i] = int(math.sin(2 * math.pi * freq * i / SAMPLE_RATE) * env * 0.4 * 32767)
        pos += sn
    return pygame.sndarray.make_sound(buf)


def _gerar_ding():
    n = int(SAMPLE_RATE * 0.5)
    buf = _buf(n)
    for i in range(n):
        env = (1.0 - i / n) ** 1.5
        v = (math.sin(2 * math.pi * 880 * i / SAMPLE_RATE) * 0.6 +
             math.sin(2 * math.pi * 1320 * i / SAMPLE_RATE) * 0.3) * env
        buf[i] = int(v * 0.35 * 32767)
    return pygame.sndarray.make_sound(buf)


def _gerar_musica_intro():
    notas = [(330, 0.18), (392, 0.18), (440, 0.18), (392, 0.18),
             (330, 0.25), (0, 0.12),
             (294, 0.18), (330, 0.18), (392, 0.35), (0, 0.15)]
    total = sum(d for _, d in notas)
    n = int(SAMPLE_RATE * total)
    buf = _buf(n)
    pos = 0
    for freq, dur in notas:
        sn = int(SAMPLE_RATE * dur)
        for i in range(sn):
            if pos + i < n:
                if freq == 0:
                    buf[pos + i] = 0
                else:
                    env = math.sin(math.pi * i / sn) ** 0.5
                    sq = 1.0 if math.sin(2 * math.pi * freq * i / SAMPLE_RATE) > 0 else -1.0
                    buf[pos + i] = int(sq * env * 0.18 * 32767)
        pos += sn
    return pygame.sndarray.make_sound(buf)


def _gerar_grilos():
    """Leito noturno suave: grilos discretos + brisa, para tocar em loop dentro de casa."""
    dur = 2.4
    n = int(SAMPLE_RATE * dur)
    buf = _buf(n)
    for i in range(n):
        t = i / SAMPLE_RATE
        # brisa baixinha
        v = (random.random() - 0.5) * 0.05
        # chirp ritmado a cada ~0.5s
        fase = t % 0.5
        if fase < 0.07:
            env = math.sin(math.pi * fase / 0.07)
            v += math.sin(2 * math.pi * 4300 * t) * env * 0.06
            v += math.sin(2 * math.pi * 5200 * t) * env * 0.03
        buf[i] = int(clamp(v, -1, 1) * 32767)
    return pygame.sndarray.make_sound(buf)


# Sons declarados aqui; gerados depois (ver gerar_sons), para a tela de "carregando".
SOM_MOTOR = SOM_PASSOS = SOM_COLISAO = SOM_BIP = None
SOM_TRANSICAO = SOM_CHEGADA = SOM_DING = SOM_INTRO = SOM_GRILOS = None


def gerar_sons():
    """Gera todos os sons procedurais (parte lenta no primeiro boot)."""
    global SOM_MOTOR, SOM_PASSOS, SOM_COLISAO, SOM_BIP, SOM_TRANSICAO
    global SOM_CHEGADA, SOM_DING, SOM_INTRO, SOM_GRILOS, SONS_OK
    try:
        SOM_MOTOR = _gerar_som_motor()
        SOM_PASSOS = _gerar_som_passos()
        SOM_COLISAO = _gerar_som_colisao()
        SOM_BIP = _gerar_bip(440, 80)
        SOM_TRANSICAO = _gerar_transicao()
        SOM_CHEGADA = _gerar_fanfarra()
        SOM_DING = _gerar_ding()
        SOM_INTRO = _gerar_musica_intro()
        SOM_GRILOS = _gerar_grilos()
        SONS_OK = True
    except Exception as e:
        print(f"[Aviso] Sons desativados: {e}")


# Música de fundo MP3
MUSICA_FUNDO_OK = False
_musica_fundo_tocando = False


def _carregar_musica_fundo():
    global MUSICA_FUNDO_OK
    base = pasta_base()
    script_dir = os.path.dirname(os.path.abspath(__file__)) if not getattr(sys, 'frozen', False) else base
    cwd = os.getcwd()
    caminhos = []
    for nome in ('videoplayback.mp3', 'musica.mp3', 'music.mp3', 'fundo.mp3',
                 'videoplayback.ogg', 'musica.ogg', 'music.ogg', 'fundo.ogg'):
        for d in (base, script_dir, cwd):
            p = os.path.join(d, nome)
            if p not in caminhos:
                caminhos.append(p)
    # Qualquer MP3/OGG na pasta base e no script_dir
    for search_dir in set([base, script_dir, cwd]):
        try:
            for f in sorted(os.listdir(search_dir)):
                if f.lower().endswith(('.mp3', '.ogg', '.wav')):
                    p = os.path.join(search_dir, f)
                    if p not in caminhos:
                        caminhos.append(p)
        except OSError:
            pass
    vistos = set()
    for p in caminhos:
        if p in vistos:
            continue
        vistos.add(p)
        if not os.path.exists(p):
            continue
        try:
            pygame.mixer.music.load(p)
            pygame.mixer.music.set_volume(0.22)
            MUSICA_FUNDO_OK = True
            print(f"[Musica] Carregada com sucesso: {p}")
            return
        except Exception as e:
            print(f"[Musica] Nao carregou {os.path.basename(p)}: {e}")
    # Nenhum arquivo funcionou — tenta converter MP3 -> OGG com pydub
    print("[Musica] Tentando converter MP3 para OGG via pydub...")
    for search_dir in set([base, script_dir, cwd]):
        try:
            for f in sorted(os.listdir(search_dir)):
                if f.lower().endswith('.mp3'):
                    mp3_path = os.path.join(search_dir, f)
                    ogg_path = mp3_path[:-4] + '_converted.ogg'
                    try:
                        from pydub import AudioSegment
                        seg = AudioSegment.from_mp3(mp3_path)
                        seg.export(ogg_path, format='ogg')
                        pygame.mixer.music.load(ogg_path)
                        pygame.mixer.music.set_volume(0.22)
                        MUSICA_FUNDO_OK = True
                        print(f"[Musica] Convertido e carregado: {ogg_path}")
                        return
                    except ImportError:
                        print("[Musica] pydub nao instalado. Para converter: pip install pydub")
                    except Exception as e2:
                        print(f"[Musica] Falha na conversao: {e2}")
        except OSError:
            pass
    print("[Musica] FALHA: nao foi possivel carregar nenhum audio.")
    print("[Musica] SOLUCAO: converte o videoplayback.mp3 para .ogg (ex: via Audacity ou online)")
    print("[Musica] e coloca o videoplayback.ogg na mesma pasta do .py")


# NÃO carregamos a música aqui — aguardamos até após pygame.display.set_mode()
# para garantir que o mixer está totalmente inicializado.

_t_motor = 0
_t_passos = 0
_intro_musica_on = False


def tocar_motor():
    global _t_motor
    if not SONS_OK:
        return
    agora = pygame.time.get_ticks()
    if agora - _t_motor > 820:
        _t_motor = agora
        SOM_MOTOR.play()


def tocar_passos():
    global _t_passos
    if not SONS_OK:
        return
    agora = pygame.time.get_ticks()
    if agora - _t_passos > 290:
        _t_passos = agora
        SOM_PASSOS.play()


def iniciar_musica_fundo():
    global _musica_fundo_tocando
    if not MUSICA_FUNDO_OK:
        return
    if not _musica_fundo_tocando:
        try:
            pygame.mixer.music.play(-1)  # -1 = loop infinito
            pygame.mixer.music.set_volume(0.0 if _musica_mutada else _volume_musica)
            _musica_fundo_tocando = True
            print("[Musica] Tocando em loop.")
        except Exception as e:
            print(f"[Música] Erro ao tocar: {e}")


def parar_musica_fundo():
    global _musica_fundo_tocando
    if _musica_fundo_tocando:
        try:
            pygame.mixer.music.stop()
            _musica_fundo_tocando = False
        except Exception:
            pass


# Som ambiente (grilos) das cenas dentro de casa
_ambiente_tocando = False
_AMB_VOL = 0.5


def iniciar_ambiente():
    global _ambiente_tocando
    if not (SONS_OK and SOM_GRILOS):
        return
    if not _ambiente_tocando:
        try:
            SOM_GRILOS.set_volume(0.0 if _musica_mutada else _AMB_VOL)
            SOM_GRILOS.play(-1)
            _ambiente_tocando = True
        except Exception:
            pass


def parar_ambiente():
    global _ambiente_tocando
    if _ambiente_tocando and SOM_GRILOS:
        try:
            SOM_GRILOS.stop()
        except Exception:
            pass
        _ambiente_tocando = False


# ==============================================================================
# ESTADO GLOBAL
# ==============================================================================
class G:
    cenaAtual = CENA_INTRO
    transicaoAlfa = 0.0
    transitando = False
    direcaoTransicao = 1
    proximaCena = None

    # Tela Intro
    introTimer = 0
    introEstrelas = [(random.randint(0, 399), random.randint(0, 185), random.random())
                     for _ in range(42)]

    carroX = 10.0
    carroY = 185.0
    estradaOffset = 0.0
    velocidadeManual = 1.6
    VELOCIDADE_ALVO = 1.6

    listaObstaculos = []
    timerGerarObstaculo = 0
    colidirTimer = 0

    homemX = 0.0
    homemY = 0.0
    homemAtivo = False
    homemComLanche = False
    homemVisivel = True
    dinerTimer = 0
    kikaoEstado = "conduzindo_para_parar"

    casaX = 220
    casaY = 60
    casalAtivo = False
    casalX = 0.0
    casalY = 0.0

    camaX = 90
    camaY = 100
    mesaX = 260
    mesaY = 115
    quartoLuzAcesa = False
    mulherQuartoX = 30.0
    mulherQuartoY = 190.0
    homemQuartoX = 16.0
    homemQuartoY = 194.0
    quartoEstado = "entrando"
    quartoTimer = 0
    notebookAceso = False

    notebookZoom = 0.0
    introMostrada = False
    cliqueDisponivel = False
    puloCliqueNotebook = 0.0
    videoExiste = False
    videoMsg = ""
    cartaMsg = ""
    mostrarCartinha = False
    playRect = None
    cartaRect = None

    tempoPasso = 0.0
    tempoCeu = 0.0

    toqueAtivo = False
    toqueDestinoX = 0.0
    toqueDestinoY = 0.0

    statusCena = "Cena 1: A Viagem Começa..."
    somChegadaTocado = False
    somDingTocado = False

    # Controle do diálogo do Lusca na cena 4
    luscaDialogoMostrado = False

    # Melhorias novas
    pausado = False
    telaCheia = False
    volumeMsg = ""
    volumeMsgTimer = 0
    coracoes = []
    coracaoTimer = 0

    # Plaquinhas na estrada
    placas = []
    placaTimer = 0

    # Coletáveis de coração
    coracoesColetaveis = []
    coracoesPegos = 0

    # Cena de dentro do carro (abertura)
    falaCarroIdx = 0


teclasPressionadas = {}

janela = pygame.display.set_mode((LARGURA * ESCALA, ALTURA * ESCALA))
pygame.display.set_caption("Joguinho pro Meu Amor <3")
clock = pygame.time.Clock()
tela = pygame.Surface((LARGURA, ALTURA))


def _tela_carregando(msg="preparando o carinho..."):
    janela.fill((20, 12, 30))
    cx = LARGURA * ESCALA // 2
    cy = ALTURA * ESCALA // 2
    f1 = pygame.font.SysFont("segoeui,verdana,arial,dejavusans,freesans", 26, bold=True)
    img1 = f1.render("carregando  \u2665", True, (255, 136, 187))
    janela.blit(img1, img1.get_rect(center=(cx, cy - 16)))
    f2 = pygame.font.SysFont("segoeui,verdana,arial,dejavusans,freesans", 14)
    img2 = f2.render(msg, True, (200, 200, 214))
    janela.blit(img2, img2.get_rect(center=(cx, cy + 18)))
    pygame.display.flip()
    pygame.event.pump()  # mantém a janela responsiva


# Mostra a tela de carregando ANTES de gerar os sons (parte lenta no 1º boot)
_tela_carregando()
gerar_sons()

# Carregar música APÓS set_mode() para garantir que o mixer está pronto
_carregar_musica_fundo()

FONT_CACHE = {}
_fila_texto = []


def fonte(tam, bold=False):
    chave = (tam, bold)
    if chave not in FONT_CACHE:
        FONT_CACHE[chave] = pygame.font.SysFont(
            "segoeui,verdana,arial,dejavusans,freesans", tam, bold=bold)
    return FONT_CACHE[chave]


def texto(_surf, txt, x, y, tam, cor, align='left', bold=False):
    _fila_texto.append((str(txt), float(x), float(y), int(tam), cor, align, bold))


def medir_texto(txt, tam, bold=False):
    return fonte(int(tam * ESCALA), bold).size(str(txt))[0] / ESCALA


def _render_fila_texto():
    for (t, x, y, tam, cor, align, bold) in _fila_texto:
        f = fonte(int(tam * ESCALA), bold)
        img = f.render(t, True, cor)
        r = img.get_rect()
        wx, wy = x * ESCALA, y * ESCALA
        if align == 'center':
            r.midtop = (int(wx), int(wy))
        elif align == 'right':
            r.topright = (int(wx), int(wy))
        else:
            r.topleft = (int(wx), int(wy))
        janela.blit(img, r)


def linha_tracejada(surf, cor, x1, y, x2, dash=10, gap=10, esp=1):
    x = x1
    while x < x2:
        pygame.draw.line(surf, cor, (x, y), (min(x + dash, x2), y), esp)
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
        pygame.draw.rect(tela, (15, 25, 15), (x + 1, y + self.altura - 2, self.largura - 2, 2))
        if self.tipo == 'carro':
            pygame.draw.rect(tela, self.cor, (x, y + 4, self.largura, self.altura - 4))
            pygame.draw.rect(tela, hx('#90afc5'), (x + 5, y, self.largura - 10, 5))
            pygame.draw.rect(tela, hx('#141416'), (x + 4, y + self.altura - 2, 5, 2))
            pygame.draw.rect(tela, hx('#141416'), (x + self.largura - 9, y + self.altura - 2, 5, 2))
            cf = hx('#fff4a3') if self.velocidade < 0 else hx('#ff3333')
            pygame.draw.rect(tela, cf, (x, y + 6, 1, 2))
        else:
            pygame.draw.rect(tela, self.cor, (x + 3, y + 2, self.largura - 6, self.altura - 4))
            pygame.draw.rect(tela, hx('#141416'), (x, y + self.altura - 2, 3, 2))
            pygame.draw.rect(tela, hx('#141416'), (x + self.largura - 3, y + self.altura - 2, 3, 2))
            pygame.draw.rect(tela, hx('#222222'), (x + 6, y, 5, 4))
            cf = hx('#fff4a3') if self.velocidade < 0 else hx('#ff3333')
            fx = x if self.velocidade < 0 else x + self.largura - 1
            pygame.draw.rect(tela, cf, (fx, y + 3, 1, 1))


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
        self.feliz = False

    def atualizar(self, perto):
        self.feliz = perto
        if self.feliz:
            self.anguloBalanco += 0.4
            off = abs(math.sin(self.anguloBalanco) * 7)
        else:
            self.anguloBalanco += 0.05
            off = abs(math.sin(self.anguloBalanco) * 1.5)
        self.y = self.baseY - off

    def desenhar(self):
        x, y = self.x, self.y
        pygame.draw.rect(tela, (15, 25, 15), (x + 1, self.baseY + 11, 10, 2))
        pygame.draw.rect(tela, self.cor, (x + 1, y + 5, 10, 7))
        pygame.draw.rect(tela, self.cor, (x + 2, y + 1, 8, 5))
        pygame.draw.rect(tela, hx('#0f0f0f'), (x + 3, y + 2, 1, 1))
        pygame.draw.rect(tela, hx('#0f0f0f'), (x + 7, y + 2, 1, 1))
        if self.tipo == 'gato':
            pygame.draw.rect(tela, hx('#e8a3a3'), (x + 5, y + 3, 1, 1))
            pygame.draw.rect(tela, self.corOrelhas, (x + 2, y, 1, 1))
            pygame.draw.rect(tela, self.corOrelhas, (x + 8, y, 1, 1))
        else:
            pygame.draw.rect(tela, hx('#111111'), (x + 5, y + 3, 2, 1))
            pygame.draw.rect(tela, self.corOrelhas, (x + 1, y + 2, 1, 3))
            pygame.draw.rect(tela, self.corOrelhas, (x + 9, y + 2, 1, 3))

        if self.feliz and self.fala:
            largTexto = medir_texto(self.fala, 6, True)
            bw = largTexto + 6
            bh = 11
            bx = x + 6 - bw / 2
            by = y - 15
            pygame.draw.rect(tela, (0, 0, 0), (bx + 1, by + 1, bw, bh))
            pygame.draw.rect(tela, hx('#ffffff'), (bx, by, bw, bh))
            pygame.draw.rect(tela, hx('#000000'), (bx, by, bw, bh), 1)
            pts = [(x + 4, by + bh), (x + 6, by + bh + 3), (x + 8, by + bh)]
            pygame.draw.polygon(tela, hx('#ffffff'), pts)
            pygame.draw.lines(tela, hx('#000000'), False, pts, 1)
            texto(tela, self.fala, x + 6, by + 1, 6, (0, 0, 0), align='center', bold=True)


class CoracaoFlutuante:
    """Coraçãozinho pixelado que sobe e some, para momentos fofos."""
    CORES = [hx('#ec607a'), hx('#ff88bb'), hx('#ffd0e8'), hx('#e8607f')]

    def __init__(self, x, y):
        self.x = float(x)
        self.y = float(y)
        self.vy = -random.uniform(0.35, 0.85)
        self.vx = random.uniform(-0.3, 0.3)
        self.vida = 1.0
        self.s = random.choice([2, 2, 3])
        self.fase = random.uniform(0, math.pi * 2)
        self.cor = random.choice(CoracaoFlutuante.CORES)

    def atualizar(self):
        self.y += self.vy
        self.x += self.vx + math.sin(self.fase + self.y * 0.05) * 0.3
        self.vida -= 0.009

    def viva(self):
        return self.vida > 0

    def desenhar(self):
        a = int(clamp(self.vida, 0, 1) * 255)
        s = self.s
        surf = pygame.Surface((s * 3, s * 4), pygame.SRCALPHA)
        cor = (self.cor[0], self.cor[1], self.cor[2], a)
        # dois "lóbulos" no topo
        pygame.draw.rect(surf, cor, (0, 0, s, s))
        pygame.draw.rect(surf, cor, (s * 2, 0, s, s))
        # corpo
        pygame.draw.rect(surf, cor, (0, s, s * 3, s))
        pygame.draw.rect(surf, cor, (s // 2, s * 2, s * 2, s))
        # ponta
        pygame.draw.rect(surf, cor, (s, s * 3, s, s))
        tela.blit(surf, (int(self.x), int(self.y)))


def soltar_coracoes(x, y, n=1):
    for _ in range(n):
        G.coracoes.append(CoracaoFlutuante(x + random.uniform(-6, 6), y + random.uniform(-4, 4)))


def desenharCoracoes():
    for c in G.coracoes:
        c.desenhar()


# ----- Plaquinhas escondidas na estrada (cenas 1 e 3) -----
PLACAS_MENSAGENS = [
    "Te amo \u2665", "faltam 2 km pra casa", "quase lá, mo \u2665",
    "dirige com carinho", "sdds tuas \u2665", "buzina se me ama",
]

# Falas da cena de abertura (dentro do carro)
FALAS_CARRO = [
    "mimi: quer pedir um ifood??",
    "lusca: claro mo, quer comer o que?",
    "mimi: pode escolher",
    "lusca: não sei, eu sempre escolho errado",
    "mimi: lanchinho??",
    "lusca: uhuuuuul",
]


def atualizar_placas():
    """Move e gera as plaquinhas; chamado nas cenas de estrada."""
    G.placaTimer += 1
    if G.placaTimer >= 200:
        G.placaTimer = 0
        msg = random.choice(PLACAS_MENSAGENS)
        G.placas.append({'x': float(LARGURA + 20), 'y': 126.0, 'txt': msg})
    indo = k('d', 'arrowright') or (G.toqueAtivo and G.toqueDestinoX > G.carroX + 24)
    velF = G.velocidadeManual if indo else 0
    for p in G.placas:
        p['x'] -= (0.6 + velF)
    G.placas = [p for p in G.placas if p['x'] > -90]


def desenharPlacas():
    for p in G.placas:
        x = int(p['x'])
        y = int(p['y'])
        txt = p['txt']
        w = int(medir_texto(txt, 8, True)) + 12
        # poste
        pygame.draw.rect(tela, hx('#5b3a1c'), (x + w // 2 - 1, y + 15, 2, 20))
        # tábua
        pygame.draw.rect(tela, hx('#caa46f'), (x, y, w, 15))
        pygame.draw.rect(tela, hx('#e7cfa0'), (x, y, w, 3))
        pygame.draw.rect(tela, hx('#8a6a3c'), (x, y, w, 15), 1)
        texto(tela, txt, x + w // 2, y + 2, 8, hx('#3a2510'), align='center', bold=True)


# ----- Coletáveis de coração (3 por cena de carro: cenas 1 e 3) -----
COLECT_TOTAL = 6
COLECT_POS = {
    CENA_1_ESTRADA: [(120, 178), (215, 200), (320, 176)],
    CENA_3_VIAGEM: [(110, 198), (225, 176), (330, 200)],
}


def criar_coletaveis(cena):
    G.coracoesColetaveis = [
        {'x': float(px), 'y': float(py), 'pego': False, 'fase': random.uniform(0, 6.28)}
        for (px, py) in COLECT_POS.get(cena, [])
    ]


def coletar_coracoes_estrada():
    carCx, carCy = G.carroX + 24, G.carroY + 12
    for h in G.coracoesColetaveis:
        if not h['pego'] and dist(carCx, carCy, h['x'], h['y']) < 16:
            h['pego'] = True
            G.coracoesPegos = min(COLECT_TOTAL, G.coracoesPegos + 1)
            if SONS_OK and SOM_DING:
                SOM_DING.play()
            soltar_coracoes(h['x'], h['y'], 5)


def desenharColetaveis():
    for h in G.coracoesColetaveis:
        if h['pego']:
            continue
        h['fase'] += 0.1
        x = int(h['x'])
        y = int(h['y'] + math.sin(h['fase']) * 2)
        glow = pygame.Surface((LARGURA, ALTURA), pygame.SRCALPHA)
        pygame.draw.circle(glow, (236, 96, 122, 80), (x, y), 9)
        tela.blit(glow, (0, 0))
        cor = hx('#ec607a')
        pygame.draw.rect(tela, cor, (x - 4, y - 3, 3, 3))
        pygame.draw.rect(tela, cor, (x + 1, y - 3, 3, 3))
        pygame.draw.rect(tela, cor, (x - 4, y, 8, 3))
        pygame.draw.rect(tela, cor, (x - 2, y + 3, 4, 2))
        pygame.draw.rect(tela, hx('#ffd0e8'), (x - 3, y - 2, 2, 2))


listaPets = [
    Pet("Shitzu Branca", "cao", 320, 155, hx('#f5f5f5'), hx('#d9c3b0'), "auuu"),
    Pet("Cão Bege", "cao", 350, 165, hx('#e3cda6'), hx('#c0a373'), "auau"),
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
        self.velocidadeEscrita = 0.5
        self.tempoCursor = 0
        self._ultimaLetra = 0

    def iniciar(self, txt):
        self.textoCompleto = txt
        self.textoAtual = ""
        self.indiceLetra = 0.0
        self.ativo = True
        self._ultimaLetra = 0

    def atualizar(self):
        if not self.ativo:
            return
        if self.indiceLetra < len(self.textoCompleto):
            self.indiceLetra += self.velocidadeEscrita
            novo = int(self.indiceLetra)
            if SONS_OK and novo > self._ultimaLetra and novo % 3 == 0:
                SOM_BIP.play()
            self._ultimaLetra = novo
            self.textoAtual = self.textoCompleto[:novo]
        self.tempoCursor += 1

    def desenhar(self):
        if not self.ativo:
            return
        pygame.draw.rect(tela, COR_CAIXA_DIALOGO, (20, 220, 360, 70))
        pygame.draw.rect(tela, COR_BORDA_DIALOGO, (20, 220, 360, 70), 3)
        pygame.draw.rect(tela, hx('#2b1b11'), (23, 223, 354, 64), 1)
        palavras = self.textoAtual.split(' ')
        linhas, atual = [], ""
        for palavra in palavras:
            teste = atual + palavra + " "
            if medir_texto(teste, 13) < 330:
                atual = teste
            else:
                linhas.append(atual)
                atual = palavra + " "
        linhas.append(atual)
        yOff = 230
        for linha in linhas:
            texto(tela, linha, 35, yOff, 13, COR_TEXTO)
            yOff += 17
        if self.indiceLetra >= len(self.textoCompleto):
            if (self.tempoCursor // 20) % 2 == 0:
                texto(tela, "▼", 360, 270, 12, COR_BORDA_DIALOGO)


caixaDialogo = CaixaDialogo()


# ==============================================================================
# CONTROLO
# ==============================================================================
def k(*nomes):
    return any(teclasPressionadas.get(n, False) for n in nomes)


def inputs_para(cx, cy, mx=12, my=10):
    direita = k('d', 'arrowright')
    esquerda = k('a', 'arrowleft')
    cima = k('w', 'arrowup')
    baixo = k('s', 'arrowdown')
    if G.toqueAtivo:
        dx = G.toqueDestinoX - cx
        dy = G.toqueDestinoY - cy
        if abs(dx) > mx:
            direita = dx > 0
            esquerda = dx < 0
        if abs(dy) > my:
            baixo = dy > 0
            cima = dy < 0
    return direita, esquerda, cima, baixo


def _livre():
    return not caixaDialogo.ativo and not G.transitando and not G.pausado


def podeConduzir():
    if not _livre():
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
    return _livre() and G.cenaAtual == CENA_2_KIKAO and G.kikaoEstado in ("descendo", "voltando")


def podeMoverCasalCena4():
    return _livre() and G.cenaAtual == CENA_4_CHEGADA_CASA and G.kikaoEstado == "casal_controlado"


def podeMoverQuartoEntrando():
    return _livre() and G.cenaAtual == CENA_5_QUARTO and G.quartoEstado == "entrando"


def podeMoverMimiQuarto():
    return _livre() and G.cenaAtual == CENA_5_QUARTO and G.quartoEstado == "andando"


def controlandoPersonagem():
    return (podeConduzir() or podeMoverHomem() or podeMoverCasalCena4() or
            podeMoverQuartoEntrando() or podeMoverMimiQuarto())


def obterHitboxCarro():
    return {'x': G.carroX + 4, 'y': G.carroY + 8, 'l': 40, 'a': 11}


def atualizarMovimentoCarroJogador():
    if not podeConduzir():
        return
    d, e, c, b = inputs_para(G.carroX + 24, G.carroY + 10, 15, 10)
    if (d or e or c or b) and SONS_OK:
        tocar_motor()
    if d:
        G.carroX += G.velocidadeManual
        if G.cenaAtual in (CENA_1_ESTRADA, CENA_3_VIAGEM):
            G.estradaOffset -= G.velocidadeManual
    elif e:
        G.carroX -= G.velocidadeManual
        if G.carroX < -60:
            G.carroX = -60
        if G.cenaAtual in (CENA_1_ESTRADA, CENA_3_VIAGEM):
            G.estradaOffset += G.velocidadeManual
    if c:
        G.carroY = max(170, G.carroY - 1.3)
    elif b:
        G.carroY = min(205, G.carroY + 1.3)


def atualizarMovimentoHomem():
    if not podeMoverHomem():
        return
    d, e, c, b = inputs_para(G.homemX + 5, G.homemY + 12)
    if (d or e or c or b) and SONS_OK:
        tocar_passos()
    v = 1.0
    if d: G.homemX += v
    if e: G.homemX -= v
    if c: G.homemY -= v
    if b: G.homemY += v
    G.homemX = clamp(G.homemX, 10, LARGURA - 20)
    G.homemY = clamp(G.homemY, 120, 210)


def atualizarMovimentoCasalCena4():
    if not podeMoverCasalCena4():
        return
    d, e, c, b = inputs_para(G.casalX + 5, G.casalY + 12)
    if (d or e or c or b) and SONS_OK:
        tocar_passos()
    v = 1.2
    if d: G.casalX += v
    if e: G.casalX -= v
    if c: G.casalY -= v
    if b: G.casalY += v
    G.casalX = clamp(G.casalX, 5, LARGURA - 15)
    G.casalY = clamp(G.casalY, 95, 200)


def atualizarMovimentoQuartoEntrando():
    if not podeMoverQuartoEntrando():
        return
    d, e, c, b = inputs_para(G.mulherQuartoX + 5, G.mulherQuartoY + 12)
    if (d or e or c or b) and SONS_OK:
        tocar_passos()
    v = 1.0
    if d: G.mulherQuartoX += v
    if e: G.mulherQuartoX -= v
    if c: G.mulherQuartoY -= v
    if b: G.mulherQuartoY += v
    G.mulherQuartoX = clamp(G.mulherQuartoX, 12, LARGURA - 20)
    G.mulherQuartoY = clamp(G.mulherQuartoY, 130, 205)
    G.homemQuartoX = clamp(G.mulherQuartoX - 13, 6, LARGURA - 20)
    G.homemQuartoY = clamp(G.mulherQuartoY + 4, 130, 205)


def atualizarMovimentoMimiQuarto():
    if not podeMoverMimiQuarto():
        return
    d, e, c, b = inputs_para(G.mulherQuartoX + 5, G.mulherQuartoY + 12)
    if (d or e or c or b) and SONS_OK:
        tocar_passos()
    v = 1.0
    if d: G.mulherQuartoX += v
    if e: G.mulherQuartoX -= v
    if c: G.mulherQuartoY -= v
    if b: G.mulherQuartoY += v
    G.mulherQuartoX = clamp(G.mulherQuartoX, 12, LARGURA - 20)
    G.mulherQuartoY = clamp(G.mulherQuartoY, 130, 205)


def gerenciarObstaculosEColisoes():
    if not podeConduzir() or G.cenaAtual == CENA_4_CHEGADA_CASA:
        G.listaObstaculos = []
        return
    G.timerGerarObstaculo += 1
    taxa = 35 if G.cenaAtual == CENA_3_VIAGEM else 55
    if G.timerGerarObstaculo >= taxa:
        G.timerGerarObstaculo = 0
        tipo = 'carro' if random.random() > 0.4 else 'moto'
        spawnY = 172 if random.random() > 0.5 else 200
        vemDeFrente = random.random() > 0.35
        vel = -3.8 if vemDeFrente else 0.8
        col = hx('#2980b9') if random.random() > 0.5 else hx('#27ae60') if tipo == 'carro' else hx('#f1c40f')
        G.listaObstaculos.append(Obstaculo(tipo, LARGURA + 30, spawnY, vel, col))

    velRef = G.velocidadeManual if (k('d', 'arrowright') or
                                    (G.toqueAtivo and G.toqueDestinoX > G.carroX + 24)) else 0
    for obs in G.listaObstaculos:
        obs.atualizar(velRef)
    G.listaObstaculos = [o for o in G.listaObstaculos if -50 < o.x < LARGURA + 100]

    if G.velocidadeManual < G.VELOCIDADE_ALVO:
        G.velocidadeManual = min(G.VELOCIDADE_ALVO, G.velocidadeManual + 0.04)
    if G.colidirTimer > 0:
        G.colidirTimer -= 1

    if G.colidirTimer == 0:
        hb = obterHitboxCarro()
        for obs in G.listaObstaculos:
            if (hb['x'] < obs.x + obs.largura and hb['x'] + hb['l'] > obs.x and
                    hb['y'] < obs.y + obs.altura and hb['y'] + hb['a'] > obs.y):
                G.colidirTimer = 50
                G.velocidadeManual = 0.4
                G.carroX = max(-60, G.carroX - 15)
                G.listaObstaculos.remove(obs)
                if SONS_OK:
                    SOM_COLISAO.play()
                break


def resetarVariaveisCenas():
    G.carroX = 10.0
    G.carroY = 185.0
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
    G.quartoLuzAcesa = False
    G.mulherQuartoX = 30.0
    G.mulherQuartoY = 190.0
    G.homemQuartoX = 16.0
    G.homemQuartoY = 194.0
    G.quartoEstado = "entrando"
    G.quartoTimer = 0
    G.notebookAceso = False
    G.notebookZoom = 0.0
    G.introMostrada = False
    G.cliqueDisponivel = False
    G.puloCliqueNotebook = 0.0
    G.videoMsg = ""
    G.cartaMsg = ""
    G.mostrarCartinha = False
    G.playRect = None
    G.cartaRect = None
    G.somChegadaTocado = False
    G.somDingTocado = False
    G.luscaDialogoMostrado = False
    G.pausado = False
    G.coracoes = []
    G.coracaoTimer = 0
    G.placas = []
    G.placaTimer = 0
    G.coracoesColetaveis = []
    G.coracoesPegos = 0
    G.falaCarroIdx = 0
    parar_ambiente()
    caixaDialogo.ativo = False
    for key in list(teclasPressionadas.keys()):
        teclasPressionadas[key] = False


def iniciarTransicao(proxima):
    if not G.transitando:
        G.transitando = True
        G.direcaoTransicao = 1
        G.proximaCena = proxima
        if SONS_OK and proxima != CENA_INTRO:
            SOM_TRANSICAO.play()


def atualizarStatus(t):
    G.statusCena = t


def gerenciarTransicao():
    if not G.transitando:
        return
    G.transicaoAlfa += G.direcaoTransicao * 0.04
    # Fade suave da música acompanhando o escurecer/clarear da tela
    if MUSICA_FUNDO_OK and not _musica_mutada and _musica_fundo_tocando:
        try:
            pygame.mixer.music.set_volume(_volume_musica * (1.0 - G.transicaoAlfa * 0.85))
        except Exception:
            pass
    if G.transicaoAlfa >= 1:
        G.transicaoAlfa = 1.0
        G.cenaAtual = G.proximaCena
        G.listaObstaculos = []
        G.placas = []
        G.placaTimer = 0
        G.coracoesColetaveis = []
        if G.cenaAtual == CENA_DENTRO_CARRO:
            G.falaCarroIdx = 0
            atualizarStatus("No carro: combinem o pedido <3")
        elif G.cenaAtual == CENA_1_ESTRADA:
            criar_coletaveis(CENA_1_ESTRADA)
            atualizarStatus("Cena 1: A Viagem Começa...  (pega os corações \u2665)")
        elif G.cenaAtual == CENA_2_KIKAO:
            G.carroX = -50
            G.kikaoEstado = "conduzindo_para_parar"
            atualizarStatus("Cena 2: Estaciona o carro na vaga amarela!")
        elif G.cenaAtual == CENA_3_VIAGEM:
            G.carroX = -60
            criar_coletaveis(CENA_3_VIAGEM)
            atualizarStatus("Cena 3: Desvia-te do tráfego rápido!  (pega os corações \u2665)")
        elif G.cenaAtual == CENA_4_CHEGADA_CASA:
            G.carroX = -60
            G.kikaoEstado = "conduzindo_para_parar"
            G.luscaDialogoMostrado = False
            atualizarStatus("Cena 4: Conduz com carinho até casa...")
        elif G.cenaAtual == CENA_5_QUARTO:
            G.quartoTimer = 0
            G.quartoEstado = "entrando"
            G.mulherQuartoX = 30.0
            G.mulherQuartoY = 190.0
            G.homemQuartoX = 16.0
            G.homemQuartoY = 194.0
            atualizarStatus("Cena 5: Leva o casal até a cama...")
        elif G.cenaAtual == CENA_6_PROGRAMACAO:
            G.notebookZoom = 0.0
            G.introMostrada = False
            G.cliqueDisponivel = False
            G.videoExiste = encontrar_video() is not None
            atualizarStatus("Cena 6: O nosso vídeo <3")
        G.direcaoTransicao = -1
    elif G.transicaoAlfa <= 0:
        G.transicaoAlfa = 0.0
        G.transitando = False
        # Restaura o volume cheio ao terminar a transição
        if MUSICA_FUNDO_OK and not _musica_mutada and _musica_fundo_tocando:
            try:
                pygame.mixer.music.set_volume(_volume_musica)
            except Exception:
                pass


# ==============================================================================
# CENÁRIO
# ==============================================================================
def desenharCeu(c1, c2, y0, y1, bandas=18):
    h = (y1 - y0) / bandas
    for i in range(bandas):
        t = i / (bandas - 1)
        pygame.draw.rect(tela, lerp_cor(c1, c2, t), (0, int(y0 + i * h), LARGURA, int(h) + 1))


def desenharNuvem(x, y, s=1.0, cor=(248, 250, 255)):
    for bx, by, bw, bh in [(0, 4, 18, 6), (6, 0, 12, 6), (12, 3, 12, 6), (3, 8, 22, 4)]:
        pygame.draw.rect(tela, cor, (x + bx * s, y + by * s, bw * s, bh * s))


def desenharNuvensDeriva(bases, cor=(248, 250, 255)):
    for bx, by, s in bases:
        x = (bx + G.tempoCeu * 0.12) % (LARGURA + 60) - 30
        desenharNuvem(x, by + 2, s, (220, 228, 240))
        desenharNuvem(x, by, s, cor)


def desenharFlores(spots):
    for fx, fy, cor in spots:
        pygame.draw.rect(tela, cor, (fx, fy, 2, 2))
        pygame.draw.rect(tela, hx('#ffd54a'), (fx, fy, 1, 1))
        pygame.draw.rect(tela, hx('#2f5a36'), (fx, fy + 2, 1, 1))


FLORES_CAMPO = [
    (30, 110, hx('#e57ea0')), (70, 130, hx('#f0e36a')), (110, 100, hx('#e57ea0')),
    (150, 138, hx('#c98be0')), (185, 105, hx('#f0e36a')), (250, 120, hx('#e57ea0')),
    (300, 140, hx('#c98be0')), (40, 250, hx('#f0e36a')), (120, 270, hx('#e57ea0')),
    (210, 258, hx('#c98be0')), (300, 272, hx('#f0e36a')), (360, 245, hx('#e57ea0')),
]


def desenharArvore(ax, ay):
    pygame.draw.rect(tela, hx('#3c2817'), (ax - 2, ay - 8, 4, 8))
    pygame.draw.polygon(tela, hx('#224d30'), [(ax - 10, ay - 8), (ax, ay - 18), (ax + 10, ay - 8)])
    pygame.draw.polygon(tela, hx('#295c3a'), [(ax - 8, ay - 14), (ax, ay - 24), (ax + 8, ay - 14)])
    pygame.draw.polygon(tela, hx('#316b43'), [(ax - 5, ay - 20), (ax, ay - 29), (ax + 5, ay - 20)])


def desenharArvores():
    for ax, ay in [(40, 150), (90, 145), (360, 150), (380, 155)]:
        desenharArvore(ax, ay)


def desenharEstrada(topo, altura, tracejada=True):
    pygame.draw.rect(tela, COR_ASFALTO, (0, topo, LARGURA, altura))
    pygame.draw.rect(tela, hx('#5b6066'), (0, topo, LARGURA, 2))
    pygame.draw.rect(tela, hx('#5b6066'), (0, topo + altura - 2, LARGURA, 2))
    meio = topo + altura // 2
    if tracejada:
        linha_tracejada(tela, hx('#f5c542'), 0, meio, LARGURA)
    else:
        pygame.draw.line(tela, hx('#f5c542'), (0, meio), (LARGURA, meio), 1)


# ==============================================================================
# PERSONAGENS / OBJETOS
# ==============================================================================
def desenharCarroPixel(x, y):
    flash = G.colidirTimer > 0 and (G.colidirTimer // 4) % 2 == 0
    alvo = pygame.Surface((LARGURA, ALTURA), pygame.SRCALPHA) if flash else tela
    pygame.draw.rect(alvo, (15, 25, 15), (x + 2, y + 21, 44, 5))
    pygame.draw.rect(alvo, hx('#1b2240'), (x, y + 8, 48, 12))
    pygame.draw.rect(alvo, hx('#0c1024'), (x, y + 19, 48, 1))
    pygame.draw.rect(alvo, hx('#0c1024'), (x, y + 8, 1, 11))
    pygame.draw.rect(alvo, hx('#2c3a66'), (x + 1, y + 9, 47, 1))
    pygame.draw.rect(alvo, hx('#9fb8d4'), (x + 10, y, 26, 9))
    pygame.draw.rect(alvo, hx('#ffffff'), (x + 13, y + 2, 4, 4))
    pygame.draw.rect(alvo, hx('#ffffff'), (x + 26, y + 2, 5, 4))
    pygame.draw.rect(alvo, hx('#141416'), (x + 8, y + 17, 8, 6))
    pygame.draw.rect(alvo, hx('#141416'), (x + 32, y + 17, 8, 6))
    pygame.draw.rect(alvo, hx('#7a7a82'), (x + 11, y + 19, 2, 2))
    pygame.draw.rect(alvo, hx('#7a7a82'), (x + 35, y + 19, 2, 2))
    pygame.draw.rect(alvo, hx('#ff3333'), (x, y + 10, 1, 3))
    pygame.draw.rect(alvo, hx('#fff4a3'), (x + 47, y + 11, 1, 3))
    if G.cenaAtual in (CENA_3_VIAGEM, CENA_4_CHEGADA_CASA):
        cone = pygame.Surface((LARGURA, ALTURA), pygame.SRCALPHA)
        pygame.draw.polygon(cone, (255, 244, 163, 70),
                            [(x + 48, y + 11), (x + 85, y + 2), (x + 85, y + 22)])
        tela.blit(cone, (0, 0))  # sempre blita na tela base (que aceita SRCALPHA)
    if flash:
        alvo.set_alpha(90)
        tela.blit(alvo, (0, 0))
    if G.colidirTimer > 20:
        texto(tela, "OPS!", x + 24, y - 16, 10, hx('#e74c3c'), align='center', bold=True)


def desenharHomemPixel(x, y, bobbing=False):
    b = math.floor(math.sin(G.tempoPasso * 0.8) * 1.5) if bobbing else 0
    pygame.draw.rect(tela, (15, 25, 15), (x + 1, y + 25, 10, 2))
    pygame.draw.rect(tela, hx('#1f2d3d'), (x + 2, y + 18 + b, 3, 8 - b))
    pygame.draw.rect(tela, hx('#1f2d3d'), (x + 7, y + 18 + b, 3, 8 - b))
    pygame.draw.rect(tela, hx('#225d87'), (x + 1, y + 10 + b, 10, 9))
    pygame.draw.rect(tela, hx('#174363'), (x + 3, y + 9 + b, 6, 2))
    pygame.draw.rect(tela, hx('#f9cba0'), (x + 2, y + 3 + b, 8, 7))
    pygame.draw.rect(tela, hx('#4f2c15'), (x + 1, y + 1 + b, 10, 3))
    pygame.draw.rect(tela, hx('#4f2c15'), (x + 1, y + 3 + b, 2, 3))
    pygame.draw.rect(tela, hx('#4f2c15'), (x + 9, y + 3 + b, 2, 2))
    pygame.draw.rect(tela, hx('#111111'), (x + 4, y + 5 + b, 1, 1))
    pygame.draw.rect(tela, hx('#111111'), (x + 7, y + 5 + b, 1, 1))


def desenharMulherPixel(x, y, bobbing=False):
    """Mulher com cabelo castanho e blusa verde."""
    b = math.floor(math.sin(G.tempoPasso * 0.8) * 1.5) if bobbing else 0
    pygame.draw.rect(tela, (15, 25, 15), (x + 1, y + 25, 10, 2))
    # Pernas
    pygame.draw.rect(tela, hx('#261b2e'), (x + 2, y + 18 + b, 3, 8 - b))
    pygame.draw.rect(tela, hx('#261b2e'), (x + 7, y + 18 + b, 3, 8 - b))
    # Blusa verde
    pygame.draw.rect(tela, hx('#2d7a3a'), (x + 1, y + 10 + b, 10, 9))
    # Rosto
    pygame.draw.rect(tela, hx('#f9cba0'), (x + 2, y + 3 + b, 8, 7))
    # Cabelo castanho
    pygame.draw.rect(tela, hx('#6b3a1f'), (x + 1, y + 1 + b, 10, 3))
    pygame.draw.rect(tela, hx('#6b3a1f'), (x + 1, y + 4 + b, 2, 7))
    pygame.draw.rect(tela, hx('#6b3a1f'), (x + 9, y + 4 + b, 2, 7))
    # Olhos
    pygame.draw.rect(tela, hx('#111111'), (x + 4, y + 5 + b, 1, 1))
    pygame.draw.rect(tela, hx('#111111'), (x + 7, y + 5 + b, 1, 1))


def desenharLanchonete():
    pygame.draw.rect(tela, hx('#d97d26'), (150, 75, 120, 75))
    pygame.draw.rect(tela, hx('#9e5311'), (150, 149, 120, 1))
    pygame.draw.rect(tela, hx('#a82c2c'), (140, 65, 140, 11))
    pygame.draw.rect(tela, hx('#cc3b3b'), (140, 63, 140, 2))
    for i in range(0, 140, 16):
        pygame.draw.rect(tela, hx('#f2efe6'), (140 + i, 65, 8, 11))
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
    texto(tela, "KIKÃO", 210, 43, 11, hx('#a82c2c'), align='center', bold=True)


def desenharCasa():
    cx, cy = G.casaX, G.casaY
    pygame.draw.rect(tela, hx('#d8bd92'), (cx, cy, 120, 80))
    pygame.draw.rect(tela, hx('#c9ab81'), (cx, cy + 60, 120, 20))
    pygame.draw.polygon(tela, hx('#8f3333'), [(cx - 10, cy), (cx + 60, cy - 45), (cx + 130, cy)])
    pygame.draw.polygon(tela, hx('#a14040'), [(cx - 10, cy), (cx + 60, cy - 45), (cx + 30, cy)])
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
    for bx in (cx - 6, cx + 108):
        pygame.draw.rect(tela, hx('#2f5d39'), (bx, cy + 66, 14, 14))
        pygame.draw.rect(tela, hx('#3a7146'), (bx + 2, cy + 64, 10, 6))


def desenharCerca(y):
    for px in range(6, LARGURA, 26):
        pygame.draw.rect(tela, hx('#caa46f'), (px, y, 3, 16))
    pygame.draw.rect(tela, hx('#b8945f'), (0, y + 4, LARGURA, 2))
    pygame.draw.rect(tela, hx('#b8945f'), (0, y + 10, LARGURA, 2))


def desenharQuarto():
    desenharCeu(hx('#352a40'), hx('#26203a'), 0, 210)
    pygame.draw.rect(tela, hx('#5a3c28'), (0, 210, LARGURA, 90))
    for yy in range(210, ALTURA, 15):
        pygame.draw.line(tela, hx('#3a2517'), (0, yy), (LARGURA, yy), 1)
    pygame.draw.ellipse(tela, hx('#3f566e'), (G.camaX - 15, G.camaY + 95, 90, 30))
    pygame.draw.ellipse(tela, hx('#4d678a'), (G.camaX - 5, G.camaY + 102, 70, 16))
    pygame.draw.rect(tela, hx('#caa074'), (150, 18, 34, 26))
    pygame.draw.rect(tela, hx('#2a2238'), (153, 21, 28, 20))
    pygame.draw.rect(tela, hx('#e8607f'), (160, 27, 4, 4))
    pygame.draw.rect(tela, hx('#e8607f'), (168, 27, 4, 4))
    pygame.draw.rect(tela, hx('#e8607f'), (162, 30, 8, 4))
    pygame.draw.rect(tela, hx('#e8607f'), (164, 33, 4, 3))

    janela_x, janela_y = 10, 40
    janela_w, janela_h = 80, 65
    janela_surf = pygame.Surface((janela_w, janela_h))
    if not G.quartoLuzAcesa:
        janela_surf.fill(hx('#0e1430'))
        for sx, sy in [(8, 8), (22, 18), (38, 10), (55, 22), (18, 40), (50, 48)]:
            pygame.draw.rect(janela_surf, hx('#fdf6c8'), (sx, sy, 1, 1))
        pygame.draw.circle(janela_surf, hx('#f2efbf'), (62, 14), 5)
    else:
        bandas = 8
        h_banda = janela_h / bandas
        c1, c2 = hx('#9fc6dc'), hx('#dfeef2')
        for i in range(bandas):
            t = i / max(bandas - 1, 1)
            cor = lerp_cor(c1, c2, t)
            pygame.draw.rect(janela_surf, cor, (0, int(i * h_banda), janela_w, int(h_banda) + 1))
        pygame.draw.rect(janela_surf, hx('#ffffff'), (20, 20, 20, 8))
        pygame.draw.rect(janela_surf, hx('#ffffff'), (24, 16, 12, 8))
    tela.blit(janela_surf, (janela_x, janela_y))
    pygame.draw.rect(tela, hx('#1e110a'), (janela_x, janela_y, janela_w, janela_h), 2)
    pygame.draw.line(tela, hx('#1e110a'), (janela_x + janela_w // 2, janela_y),
                     (janela_x + janela_w // 2, janela_y + janela_h), 1)
    pygame.draw.line(tela, hx('#1e110a'), (janela_x, janela_y + janela_h // 2),
                     (janela_x + janela_w, janela_y + janela_h // 2), 1)

    pygame.draw.rect(tela, hx('#4c311f'), (10, 140, 14, 70))
    pygame.draw.rect(tela, hx('#25160d'), (10, 140, 14, 70), 2)
    pygame.draw.rect(tela, hx('#9e714b'), (10, 140, 14, 70), 1)
    pygame.draw.rect(tela, hx('#ffd15c'), (20, 175, 2, 3))
    pygame.draw.rect(tela, hx('#5c3d25'), (G.mesaX, G.mesaY, 55, 60))
    pygame.draw.rect(tela, hx('#331f11'), (G.mesaX + 2, G.mesaY + 60, 4, 30))
    pygame.draw.rect(tela, hx('#331f11'), (G.mesaX + 49, G.mesaY + 60, 4, 30))
    pygame.draw.rect(tela, hx('#382215'), (G.mesaX + 8, G.mesaY + 65, 14, 20))
    if G.quartoLuzAcesa:
        glow = pygame.Surface((40, 40), pygame.SRCALPHA)
        pygame.draw.circle(glow, (255, 220, 130, 60), (20, 20), 18)
        tela.blit(glow, (G.mesaX + 24, G.mesaY - 14))
    pygame.draw.rect(tela, hx('#caa05a'), (G.mesaX + 40, G.mesaY - 6, 6, 12))
    pygame.draw.rect(tela, hx('#ffe7a0'), (G.mesaX + 37, G.mesaY - 12, 12, 7))
    pygame.draw.rect(tela, hx('#68686d'), (G.mesaX + 15, G.mesaY + 20, 20, 4))
    if G.notebookAceso:
        pygame.draw.rect(tela, hx('#a1e4ff'), (G.mesaX + 18, G.mesaY + 6, 12, 9))
    else:
        pygame.draw.rect(tela, hx('#1e1e24'), (G.mesaX + 18, G.mesaY + 10, 15, 10))

    pygame.draw.rect(tela, hx('#6e4424'), (G.camaX, G.camaY, 60, 120))
    pygame.draw.rect(tela, hx('#e3e3f0'), (G.camaX + 2, G.camaY + 28, 56, 92))
    pygame.draw.rect(tela, hx('#cdb4e0'), (G.camaX + 2, G.camaY + 28, 56, 6))
    pygame.draw.rect(tela, hx('#ffffff'), (G.camaX + 6, G.camaY + 6, 20, 15))
    pygame.draw.rect(tela, hx('#ffffff'), (G.camaX + 34, G.camaY + 6, 20, 15))


def desenharTelaNotebook(t):
    sx, sy, sw, sh = G.mesaX + 18, G.mesaY + 6, 12, 9
    px, py, pw, ph = 64, 36, 272, 142
    x = lerp(sx, px, t)
    y = lerp(sy, py, t)
    w = lerp(sw, pw, t)
    h = lerp(sh, ph, t)
    pygame.draw.rect(tela, (18, 20, 28), (x - 4, y - 4, w + 8, h + 8))
    pygame.draw.rect(tela, (40, 44, 56), (x - 4, y - 4, w + 8, h + 8), 1)
    pygame.draw.rect(tela, (10, 12, 20), (x, y, w, h))
    pygame.draw.rect(tela, (22, 26, 40), (int(x + 3), int(y + 3), int(w - 6), int(h - 6)))
    return x, y, w, h


# ==============================================================================
# DENTRO DO CARRO (cena de abertura)
# ==============================================================================
def desenharDentroCarro():
    # Para-brisa: céu + estrada à frente
    desenharCeu(hx('#7fc1e8'), hx('#cfeaf6'), 0, 150)
    pygame.draw.circle(tela, hx('#fff4c2'), (320, 38), 14)
    pygame.draw.circle(tela, hx('#fff9d8'), (320, 38), 9)
    desenharNuvensDeriva([(60, 26, 0.8), (240, 18, 1.0)])
    # estrada em perspectiva
    pygame.draw.rect(tela, COR_GRAMA, (0, 138, LARGURA, 32))
    pygame.draw.polygon(tela, COR_ASFALTO,
                        [(155, 138), (245, 138), (360, 170), (40, 170)])
    for i, yy in enumerate(range(140, 170, 7)):
        w = 1 + i // 2
        pygame.draw.rect(tela, hx('#f5c542'), (LARGURA // 2 - w // 2, yy, w, 4))
    # painel (dashboard)
    pygame.draw.rect(tela, hx('#241a16'), (0, 168, LARGURA, ALTURA - 168))
    pygame.draw.rect(tela, hx('#3a2a22'), (0, 168, LARGURA, 5))
    # retrovisor com coraçãozinho
    pygame.draw.rect(tela, hx('#1a1410'), (168, 8, 64, 18))
    pygame.draw.rect(tela, hx('#9fc6dc'), (171, 11, 58, 12))
    pygame.draw.rect(tela, hx('#e8607f'), (196, 4, 8, 7))
    pygame.draw.polygon(tela, hx('#e8607f'), [(196, 11), (200, 15), (204, 11)])

    # ocupantes (de costas): lusca no volante (esq.), mimi passageira (dir.)
    def ocupante(cx, cor_cabelo, cor_roupa, longo=False):
        pygame.draw.rect(tela, cor_roupa, (cx - 22, 196, 44, ALTURA - 196))
        pygame.draw.rect(tela, lerp_cor(cor_roupa, (0, 0, 0), 0.25), (cx - 22, 196, 44, 5))
        pygame.draw.rect(tela, cor_cabelo, (cx - 14, 150, 28, 48))
        if longo:
            pygame.draw.rect(tela, cor_cabelo, (cx - 18, 158, 6, 54))
            pygame.draw.rect(tela, cor_cabelo, (cx + 12, 158, 6, 54))

    ocupante(118, hx('#4f2c15'), hx('#225d87'))        # lusca
    ocupante(286, hx('#6b3a1f'), hx('#2d7a3a'), True)  # mimi

    # volante na frente do lusca
    pygame.draw.circle(tela, hx('#15100d'), (118, 250), 30)
    pygame.draw.circle(tela, hx('#2a201a'), (118, 250), 30, 4)
    pygame.draw.circle(tela, hx('#15100d'), (118, 250), 9)
    pygame.draw.line(tela, hx('#2a201a'), (90, 250), (146, 250), 3)


# ==============================================================================
# TELA DE INTRO
# ==============================================================================
def desenharTelaIntro():
    t = G.introTimer

    pulso = (math.sin(t * 0.018) + 1) / 2
    c1 = lerp_cor(hx('#140820'), hx('#200c36'), pulso)
    c2 = lerp_cor(hx('#0a1238'), hx('#162048'), pulso)
    desenharCeu(c1, c2, 0, ALTURA)

    for sx, sy, fase in G.introEstrelas:
        brilho = (math.sin(t * 0.04 + fase * 9) + 1) / 2
        a = int(brilho * 190 + 65)
        tam = 1 if brilho < 0.55 else 2
        pygame.draw.rect(tela, (a, a, min(255, a + 50)), (sx, sy, tam, tam))

    for i in range(6):
        ang = t * 0.013 + i * (math.pi * 2 / 6)
        hcx = LARGURA // 2 + int(math.cos(ang) * (55 + i * 12))
        hcy = 145 + int(math.sin(ang * 0.65) * 18)
        a_c = int((math.sin(t * 0.025 + i * 1.2) + 1) / 2 * 110 + 50)
        sz = 2 + i % 3
        hs = pygame.Surface((sz * 4, sz * 4), pygame.SRCALPHA)
        pontos = [(sz, 0), (sz*2, 0), (sz*3, sz), (sz*3, sz*2),
                  (sz*2, sz*3), (sz, sz*3), (0, sz*2), (0, sz)]
        pygame.draw.polygon(hs, (240, 80, 130, a_c), pontos)
        tela.blit(hs, (hcx - sz*2, hcy - sz*2))

    for ox, oy, cor_t in [(2, 2, hx('#500030')), (1, 1, hx('#800050')), (0, 0, hx('#ffd0e8'))]:
        texto(tela, "joguinho pro", LARGURA // 2 + ox, 55 + oy, 23, cor_t, align='center', bold=True)
    for ox, oy, cor_t in [(2, 2, hx('#500030')), (1, 1, hx('#800050')), (0, 0, hx('#ff88bb'))]:
        texto(tela, "meu amor  <3", LARGURA // 2 + ox, 82 + oy, 23, cor_t, align='center', bold=True)

    desenharMulherPixel(LARGURA // 2 - 24, 148)
    desenharHomemPixel(LARGURA // 2 + 10, 148)

    alfa_btn = int((math.sin(t * 0.07) + 1) / 2 * 160 + 95)
    cor_btn = (min(255, alfa_btn + 60), alfa_btn, min(255, alfa_btn + 90))
    texto(tela, "ENTER ou clique para começar", LARGURA // 2, 196, 11, cor_btn,
          align='center', bold=True)
    texto(tela, "feito com amor  ♥", LARGURA // 2, 215, 9, hx('#886699'), align='center')


# ==============================================================================
# CARTINHA (overlay)
# ==============================================================================
TEXTO_CARTA = [
    ("Para o meu amor <3", True, True),
    ("", False, False),
    ("Obrigada por passar esses", False, False),
    ("8 meses ao meu lado,", False, False),
    ("você é meu tudo  ♥", False, False),
    ("", False, False),
    ("Quero estar pra sempre", False, False),
    ("com você meu gatinho  ♥", False, False),
    ("", False, False),
    ("Com muito amor:", False, False),
    ("mimisf  ♥", True, True),
]


def desenharOverlayCarta():
    ov = pygame.Surface((LARGURA, ALTURA), pygame.SRCALPHA)
    ov.fill((0, 0, 0, 200))
    tela.blit(ov, (0, 0))

    cx, cy, cw, ch = 30, 20, 340, 245
    pygame.draw.rect(tela, hx('#fffdf0'), (cx, cy, cw, ch))
    pygame.draw.rect(tela, hx('#e8c88a'), (cx, cy, cw, ch), 2)
    texto(tela, "♥", LARGURA // 2, cy + 6, 14, hx('#c0305a'), align='center', bold=True)
    y_off = cy + 24
    for (linha, destaque, bold_linha) in TEXTO_CARTA:
        if linha == "":
            y_off += 8
            continue
        cor_linha = hx('#c0305a') if destaque else hx('#3a2520')
        texto(tela, linha, LARGURA // 2, y_off, 11, cor_linha, align='center', bold=bold_linha)
        y_off += 16
    # Linha dinâmica de acordo com os corações coletados
    if G.coracoesPegos >= COLECT_TOTAL:
        texto(tela, "você pegou todos os corações \u2665", LARGURA // 2, y_off + 4, 10,
              hx('#c0305a'), align='center', bold=True)
    elif G.coracoesPegos > 0:
        texto(tela, f"você pegou {G.coracoesPegos} de {COLECT_TOTAL} corações \u2665",
              LARGURA // 2, y_off + 4, 10, hx('#a85070'), align='center')
    else:
        texto(tela, "(da próxima, pega os corações na estrada \u2665)", LARGURA // 2,
              y_off + 4, 9, hx('#a85070'), align='center')
    bx, by, bw, bh = LARGURA // 2 - 40, cy + ch - 22, 80, 16
    pygame.draw.rect(tela, hx('#c0305a'), (bx, by, bw, bh))
    pygame.draw.rect(tela, hx('#e8a0b8'), (bx, by, bw, bh), 1)
    texto(tela, "fechar  ♥", LARGURA // 2, by + 2, 10, hx('#ffffff'), align='center', bold=True)
    G._cartaFechaBtnRect = (bx, by, bw, bh)


# ==============================================================================
# OVERLAY DE PAUSA
# ==============================================================================
def desenharOverlayPausa():
    ov = pygame.Surface((LARGURA, ALTURA), pygame.SRCALPHA)
    ov.fill((10, 8, 22, 180))
    tela.blit(ov, (0, 0))
    pw, ph = 200, 96
    px, py = (LARGURA - pw) // 2, (ALTURA - ph) // 2
    pygame.draw.rect(tela, hx('#2a1c3a'), (px, py, pw, ph))
    pygame.draw.rect(tela, hx('#caa074'), (px, py, pw, ph), 2)
    texto(tela, "PAUSA  ♥", LARGURA // 2, py + 14, 18, hx('#ff88bb'), align='center', bold=True)
    texto(tela, "P para continuar", LARGURA // 2, py + 44, 11, hx('#fcf5db'), align='center')
    texto(tela, "M muta  |  + / - volume", LARGURA // 2, py + 62, 9, hx('#c9c9d6'), align='center')
    texto(tela, "F11 tela cheia  |  R recomeça", LARGURA // 2, py + 76, 9, hx('#c9c9d6'), align='center')


# ==============================================================================
# ATUALIZAR
# ==============================================================================
def dist(ax, ay, bx, by):
    return math.hypot(ax - bx, ay - by)


def atualizar():
    global _intro_musica_on
    gerenciarTransicao()
    caixaDialogo.atualizar()
    G.tempoCeu += 1.0

    # Corações flutuantes (sempre, mesmo durante diálogo)
    for c in G.coracoes:
        c.atualizar()
    G.coracoes = [c for c in G.coracoes if c.viva()]

    if G.volumeMsgTimer > 0:
        G.volumeMsgTimer -= 1

    if caixaDialogo.ativo:
        return
    G.tempoPasso += 0.2

    # --- Tela intro ---
    if G.cenaAtual == CENA_INTRO:
        G.introTimer += 1
        if SONS_OK and not _intro_musica_on:
            SOM_INTRO.play(-1)
            _intro_musica_on = True
        return

    # Parar música intro, iniciar música de fundo (independente de SONS_OK)
    if _intro_musica_on:
        if SONS_OK:
            SOM_INTRO.stop()
        _intro_musica_on = False
    # A trilha toca só nas cenas de viagem; ao entrar em casa (cena 5) em diante, silêncio + grilos.
    if G.cenaAtual in (CENA_DENTRO_CARRO, CENA_1_ESTRADA, CENA_2_KIKAO,
                       CENA_3_VIAGEM, CENA_4_CHEGADA_CASA):
        iniciar_musica_fundo()  # a função já evita tocar duas vezes
        parar_ambiente()
    else:
        parar_musica_fundo()
        iniciar_ambiente()  # grilos / clima de noite dentro de casa

    if G.cenaAtual == CENA_DENTRO_CARRO:
        # Sequência de falas de abertura; ao terminar, vai para a estrada
        if G.falaCarroIdx < len(FALAS_CARRO):
            caixaDialogo.iniciar(FALAS_CARRO[G.falaCarroIdx])
            G.falaCarroIdx += 1
        else:
            iniciarTransicao(CENA_1_ESTRADA)

    elif G.cenaAtual == CENA_1_ESTRADA:
        atualizar_placas()
        coletar_coracoes_estrada()
        if G.carroX >= LARGURA:
            iniciarTransicao(CENA_2_KIKAO)

    elif G.cenaAtual == CENA_2_KIKAO:
        if G.kikaoEstado == "conduzindo_para_parar":
            ccx, ccy = G.carroX + 24, G.carroY + 10
            if 85 <= ccx <= 135 and 180 <= ccy <= 202:
                G.kikaoEstado = "descendo"
                G.homemX = G.carroX + 15
                G.homemY = G.carroY - 5
                G.homemAtivo = True
                G.homemVisivel = True
                G.homemComLanche = False
                if SONS_OK:
                    SOM_DING.play()
                atualizarStatus("Cena 2: Caminha até à porta da lanchonete!")
        elif G.kikaoEstado == "descendo":
            if abs((G.homemX + 5) - 210) < 12 and (G.homemY + 25) <= 150:
                G.homemVisivel = False
                G.kikaoEstado = "comprando"
                G.dinerTimer = 0
                atualizarStatus("Cena 2: À espera do lanche...")
        elif G.kikaoEstado == "comprando":
            G.dinerTimer += 1
            if G.dinerTimer >= 100:
                G.homemVisivel = True
                G.homemComLanche = True
                G.homemX = 205
                G.homemY = 125
                G.kikaoEstado = "voltando"
                atualizarStatus("Cena 2: Lanche na mão! Volta para o carro!")
        elif G.kikaoEstado == "voltando":
            if dist(G.homemX + 5, G.homemY + 12, G.carroX + 24, G.carroY + 10) < 22:
                G.homemAtivo = False
                G.kikaoEstado = "conduzindo_para_sair"
                atualizarStatus("Cena 2: Conduz para a direita!")
        elif G.kikaoEstado == "conduzindo_para_sair":
            if G.carroX > LARGURA:
                iniciarTransicao(CENA_3_VIAGEM)

    elif G.cenaAtual == CENA_3_VIAGEM:
        atualizar_placas()
        coletar_coracoes_estrada()
        # Diálogo do Lusca: exibir quando o carro entra na tela
        if not G.luscaDialogoMostrado and G.carroX >= 20:
            G.luscaDialogoMostrado = True
            caixaDialogo.iniciar("Lusca: *estrala o dedo* hmmm que catupiry bom vei!")
        if G.carroX > LARGURA:
            iniciarTransicao(CENA_4_CHEGADA_CASA)

    elif G.cenaAtual == CENA_4_CHEGADA_CASA:
        if G.kikaoEstado == "conduzindo_para_parar":
            if G.carroX >= 60:
                G.carroX = 60
                G.kikaoEstado = "casal_controlado"
                G.casalX = G.carroX + 15
                G.casalY = G.carroY - 15
                G.casalAtivo = True
                atualizarStatus("Cena 4: Leva o casal até a porta de casa!")
                if SONS_OK and not G.somChegadaTocado:
                    SOM_CHEGADA.play()
                    G.somChegadaTocado = True
        elif G.kikaoEstado == "casal_controlado":
            perto = (dist(G.casalX + 5, G.casalY + 12, G.casaX + 90, G.casaY + 80) < 130)
            for pet in listaPets:
                pet.atualizar(perto)
            if perto:
                G.coracaoTimer += 1
                if G.coracaoTimer >= 16:
                    G.coracaoTimer = 0
                    soltar_coracoes(G.casalX + 6, G.casalY - 6, 1)
            if dist(G.casalX + 5, G.casalY + 25, G.casaX + 35, G.casaY + 68) < 16:
                G.casalAtivo = False
                iniciarTransicao(CENA_5_QUARTO)

    elif G.cenaAtual == CENA_5_QUARTO:
        if G.quartoEstado == "entrando":
            if dist(G.mulherQuartoX, G.mulherQuartoY, G.camaX + 20, G.camaY + 55) < 12:
                G.quartoEstado = "dormindo"
                G.quartoTimer = 0
                atualizarStatus("Cena 5: Boa noite...")
                if SONS_OK and not G.somDingTocado:
                    SOM_DING.play()
                    G.somDingTocado = True
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
                    G.mulherQuartoX = G.camaX + 20
                    G.mulherQuartoY = G.camaY + 55
                    atualizarStatus("Cena 5: Leva a Mimi até o notebook!")
            elif G.quartoEstado == "andando":
                if dist(G.mulherQuartoX, G.mulherQuartoY, G.mesaX + 8, G.mesaY + 28) < 10:
                    G.notebookAceso = True
                    G.quartoEstado = "programando"
                    iniciarTransicao(CENA_6_PROGRAMACAO)

    elif G.cenaAtual == CENA_6_PROGRAMACAO:
        if G.notebookZoom < 1.0:
            G.notebookZoom = min(1.0, G.notebookZoom + 0.045)
        elif not G.introMostrada:
            caixaDialogo.iniciar("mimi: oi moo, fiz um vídeo pra vc <3")
            G.introMostrada = True
        G.cliqueDisponivel = (G.notebookZoom >= 1.0 and G.introMostrada and not caixaDialogo.ativo)
        G.puloCliqueNotebook += 0.12
        if G.cliqueDisponivel:
            G.coracaoTimer += 1
            if G.coracaoTimer >= 28:
                G.coracaoTimer = 0
                soltar_coracoes(random.randint(80, 320), 168, 1)


# ==============================================================================
# DESENHAR
# ==============================================================================
def desenhar():
    _fila_texto.clear()
    shakeX = shakeY = 0
    if G.colidirTimer > 35:
        shakeX = (random.random() - 0.5) * 4.5
        shakeY = (random.random() - 0.5) * 4.5

    tela.fill((0, 0, 0))

    if G.cenaAtual == CENA_INTRO:
        desenharTelaIntro()

    elif G.cenaAtual == CENA_DENTRO_CARRO:
        desenharDentroCarro()

    elif G.cenaAtual == CENA_1_ESTRADA:
        tela.fill(COR_GRAMA)
        desenharCeu(hx('#7fc1e8'), hx('#cfeaf6'), 0, 92)
        pygame.draw.circle(tela, hx('#fff4c2'), (322, 44), 16)
        pygame.draw.circle(tela, hx('#fff9d8'), (322, 44), 11)
        desenharNuvensDeriva([(60, 18, 1.0), (220, 30, 0.8), (320, 14, 1.2)])
        desenharArvores()
        desenharPlacas()
        desenharFlores(FLORES_CAMPO)
        desenharEstrada(165, 65, True)
        desenharColetaveis()
        for obs in G.listaObstaculos:
            obs.desenhar()
        desenharCarroPixel(G.carroX, G.carroY)
        desenharCoracoes()

    elif G.cenaAtual == CENA_2_KIKAO:
        tela.fill(COR_GRAMA)
        desenharCeu(hx('#7fc1e8'), hx('#cfeaf6'), 0, 70)
        desenharNuvensDeriva([(40, 12, 0.9), (300, 20, 1.0)])
        desenharArvores()
        desenharEstrada(165, 65, False)
        desenharLanchonete()
        if G.kikaoEstado == "conduzindo_para_parar":
            pygame.draw.rect(tela, hx('#ffd700'), (85, 180, 50, 22), 1)
            texto(tela, "VAGA", 110, 167, 10, hx('#ffd700'), align='center', bold=True)
        if G.kikaoEstado == "comprando":
            pygame.draw.rect(tela, hx('#1e1e24'), (190, 105, 40, 5))
            pygame.draw.rect(tela, hx('#27ae60'), (190, 105, int(40 * min(G.dinerTimer / 100, 1.0)), 5))
            pygame.draw.rect(tela, hx('#9e714b'), (190, 105, 40, 5), 1)
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
        tela.fill(hx('#6b4a52'))
        desenharCeu(hx('#e8763a'), hx('#f4c06a'), 0, 60)
        desenharCeu(hx('#f4c06a'), hx('#8a6b7a'), 60, 95)
        pygame.draw.circle(tela, hx('#ffe0a0'), (300, 62), 16)
        pygame.draw.circle(tela, hx('#ffb96b'), (300, 62), 12)
        desenharNuvensDeriva([(80, 20, 1.0), (260, 30, 0.8)], cor=(255, 210, 170))
        for bx, by in [(120, 40), (135, 36), (200, 28)]:
            pygame.draw.line(tela, hx('#3a2a30'), (bx, by), (bx + 3, by - 2), 1)
            pygame.draw.line(tela, hx('#3a2a30'), (bx + 3, by - 2), (bx + 6, by), 1)
        desenharArvores()
        desenharPlacas()
        desenharEstrada(165, 65, True)
        desenharColetaveis()
        for obs in G.listaObstaculos:
            obs.desenhar()
        desenharCarroPixel(G.carroX, G.carroY)
        desenharCoracoes()

    elif G.cenaAtual == CENA_4_CHEGADA_CASA:
        tela.fill(COR_GRAMA)
        desenharCeu(hx('#f0a25a'), hx('#f6d59a'), 0, 34)
        pygame.draw.rect(tela, hx('#6a615a'), (200, 138, 200, 54))
        for cx in range(208, LARGURA, 16):
            pygame.draw.rect(tela, hx('#534b45'), (cx, 138, 1, 54))
        desenharCerca(120)
        desenharFlores([(30, 250, hx('#e57ea0')), (90, 265, hx('#f0e36a')),
                        (150, 255, hx('#c98be0')), (60, 240, hx('#f0e36a'))])
        desenharCasa()
        desenharEstrada(180, 55, False)
        desenharCarroPixel(G.carroX, G.carroY)
        for pet in listaPets:
            pet.desenhar()
        if G.casalAtivo:
            desenharMulherPixel(G.casalX, G.casalY, True)
            desenharHomemPixel(G.casalX - 12, G.casalY + 2, True)
        desenharCoracoes()

    elif G.cenaAtual == CENA_5_QUARTO:
        desenharQuarto()
        if G.quartoEstado == "entrando":
            desenharHomemPixel(G.homemQuartoX, G.homemQuartoY, True)
            desenharMulherPixel(G.mulherQuartoX, G.mulherQuartoY, True)
        elif G.quartoEstado == "dormindo":
            desenharMulherPixel(G.camaX + 10, G.camaY + 10)
            desenharHomemPixel(G.camaX + 40, G.camaY + 10)
            pygame.draw.rect(tela, hx('#cfcfe0'), (G.camaX + 2, G.camaY + 28, 56, 92))
            pygame.draw.rect(tela, hx('#b9b9d4'), (G.camaX + 2, G.camaY + 28, 56, 4))
        else:
            desenharHomemPixel(G.camaX + 40, G.camaY + 10)
            pygame.draw.rect(tela, hx('#cfcfe0'), (G.camaX + 2, G.camaY + 28, 56, 92))
            pygame.draw.rect(tela, hx('#b9b9d4'), (G.camaX + 2, G.camaY + 28, 56, 4))
            desenharMulherPixel(G.mulherQuartoX, G.mulherQuartoY, True)
        ov = pygame.Surface((LARGURA, ALTURA), pygame.SRCALPHA)
        if not G.quartoLuzAcesa:
            ov.fill((12, 10, 24, 180))
        else:
            ov.fill((255, 215, 120, 18))
        tela.blit(ov, (0, 0))

    elif G.cenaAtual == CENA_6_PROGRAMACAO:
        desenharQuarto()
        desenharHomemPixel(G.camaX + 40, G.camaY + 10)
        pygame.draw.rect(tela, hx('#cfcfe0'), (G.camaX + 2, G.camaY + 28, 56, 92))
        desenharMulherPixel(G.mesaX + 4, G.mesaY + 28)
        ov = pygame.Surface((LARGURA, ALTURA), pygame.SRCALPHA)
        ov.fill((10, 8, 20, 120))
        tela.blit(ov, (0, 0))
        x, y, w, h = desenharTelaNotebook(G.notebookZoom)
        G.playRect = None
        G.cartaRect = None
        if G.cliqueDisponivel:
            cx = int(x + w / 2)
            cy = int(y + h / 2)

            pulso = abs(math.sin(G.puloCliqueNotebook)) * 3
            r_vid = int(16 + pulso)
            vid_cx = int(x + w * 0.30)
            vid_cy = cy

            halo = pygame.Surface((LARGURA, ALTURA), pygame.SRCALPHA)
            pygame.draw.circle(halo, (236, 96, 122, 70), (vid_cx, vid_cy), r_vid + 8)
            tela.blit(halo, (0, 0))
            pygame.draw.circle(tela, hx('#ec607a'), (vid_cx, vid_cy), r_vid)
            pygame.draw.circle(tela, hx('#ffffff'), (vid_cx, vid_cy), r_vid, 2)
            pygame.draw.polygon(tela, hx('#ffffff'),
                                [(vid_cx - 5, vid_cy - 7), (vid_cx - 5, vid_cy + 7), (vid_cx + 7, vid_cy)])
            G.playRect = (vid_cx, vid_cy, r_vid + 6)

            r_carta = int(16 + pulso)
            carta_cx = int(x + w * 0.70)
            carta_cy = cy

            halo2 = pygame.Surface((LARGURA, ALTURA), pygame.SRCALPHA)
            pygame.draw.circle(halo2, (100, 180, 255, 60), (carta_cx, carta_cy), r_carta + 8)
            tela.blit(halo2, (0, 0))
            pygame.draw.circle(tela, hx('#4a90d9'), (carta_cx, carta_cy), r_carta)
            pygame.draw.circle(tela, hx('#ffffff'), (carta_cx, carta_cy), r_carta, 2)
            ex, ey = carta_cx - 7, carta_cy - 5
            pygame.draw.rect(tela, hx('#ffffff'), (ex, ey, 14, 10), 1)
            pygame.draw.line(tela, hx('#ffffff'), (ex, ey), (carta_cx, carta_cy + 1), 1)
            pygame.draw.line(tela, hx('#ffffff'), (ex + 14, ey), (carta_cx, carta_cy + 1), 1)
            G.cartaRect = (carta_cx, carta_cy, r_carta + 6)

            cap_vid = "nosso vídeo <3" if G.videoExiste else "video (.mp4)"
            texto(tela, cap_vid, vid_cx, int(y + h) + 4, 10, hx('#ffe9c2'), align='center', bold=True)
            texto(tela, "cartinha ♥", carta_cx, int(y + h) + 4, 10, hx('#c2d8ff'), align='center', bold=True)

            if G.videoMsg:
                texto(tela, G.videoMsg, LARGURA / 2, int(y + h) + 18, 9, hx('#bfe8c2'), align='center')
            if G.cartaMsg:
                texto(tela, G.cartaMsg, LARGURA / 2, int(y + h) + 28, 9, hx('#bfe8c2'), align='center')
            texto(tela, "Pressiona R para recomeçar", LARGURA / 2, ALTURA - 14, 9,
                  hx('#c9c9d6'), align='center')

        desenharCoracoes()

        if G.mostrarCartinha:
            desenharOverlayCarta()

    # HUD
    if G.cenaAtual != CENA_INTRO and controlandoPersonagem():
        hud = pygame.Surface((212, 18), pygame.SRCALPHA)
        hud.fill((20, 20, 20, 184))
        tela.blit(hud, (8, 8))
        t_hud = "WASD/SETAS: conduz o teu carro" if podeConduzir() else "WASD/SETAS: move os personagens"
        texto(tela, t_hud, 12, 10, 10, hx('#ffffff'))

    # Contador de corações nas cenas de estrada
    if G.cenaAtual in (CENA_1_ESTRADA, CENA_3_VIAGEM):
        hc = pygame.Surface((70, 18), pygame.SRCALPHA)
        hc.fill((20, 20, 20, 184))
        tela.blit(hc, (8, 30))
        texto(tela, f"\u2665 {G.coracoesPegos}/{COLECT_TOTAL}", 14, 32, 11, hx('#ff9ec2'), bold=True)

    # Mensagem de volume/mute
    if G.volumeMsgTimer > 0 and G.volumeMsg:
        vm = pygame.Surface((118, 16), pygame.SRCALPHA)
        vm.fill((20, 20, 20, 184))
        tela.blit(vm, (LARGURA - 126, 8))
        texto(tela, G.volumeMsg, LARGURA - 120, 10, 10, hx('#ffe9c2'), bold=True)

    caixaDialogo.desenhar()

    if G.pausado:
        desenharOverlayPausa()

    if G.transicaoAlfa > 0:
        fade = pygame.Surface((LARGURA, ALTURA), pygame.SRCALPHA)
        fade.fill((0, 0, 0, int(G.transicaoAlfa * 255)))
        tela.blit(fade, (0, 0))

    escalada = pygame.transform.scale(tela, (LARGURA * ESCALA, ALTURA * ESCALA))
    janela.fill((0, 0, 0))
    janela.blit(escalada, (int(shakeX * ESCALA), int(shakeY * ESCALA)))
    _render_fila_texto()


# ==============================================================================
# CONTROLES DE SOM / TELA
# ==============================================================================
def ajustar_volume(delta):
    global _volume_musica
    _volume_musica = clamp(_volume_musica + delta, 0.0, 1.0)
    if MUSICA_FUNDO_OK and not _musica_mutada:
        try:
            pygame.mixer.music.set_volume(_volume_musica)
        except Exception:
            pass
    G.volumeMsg = f"Volume: {int(_volume_musica * 100)}%"
    G.volumeMsgTimer = 90


def alternar_mute():
    global _musica_mutada
    _musica_mutada = not _musica_mutada
    if MUSICA_FUNDO_OK:
        try:
            pygame.mixer.music.set_volume(0.0 if _musica_mutada else _volume_musica)
        except Exception:
            pass
    if SOM_GRILOS:
        try:
            SOM_GRILOS.set_volume(0.0 if _musica_mutada else _AMB_VOL)
        except Exception:
            pass
    G.volumeMsg = "Som: OFF" if _musica_mutada else "Som: ON"
    G.volumeMsgTimer = 90


def alternar_pausa():
    if G.cenaAtual == CENA_INTRO:
        return
    G.pausado = not G.pausado
    if MUSICA_FUNDO_OK and _musica_fundo_tocando:
        try:
            if G.pausado:
                pygame.mixer.music.pause()
            else:
                pygame.mixer.music.unpause()
        except Exception:
            pass


def alternar_tela_cheia():
    global janela
    G.telaCheia = not G.telaCheia
    try:
        if G.telaCheia:
            janela = pygame.display.set_mode(
                (LARGURA * ESCALA, ALTURA * ESCALA), pygame.FULLSCREEN | pygame.SCALED)
        else:
            janela = pygame.display.set_mode((LARGURA * ESCALA, ALTURA * ESCALA))
    except Exception as e:
        print(f"[Tela] Nao consegui alternar tela cheia: {e}")


# ==============================================================================
# EVENTOS
# ==============================================================================
def avancarDialogo():
    if caixaDialogo.indiceLetra >= len(caixaDialogo.textoCompleto):
        caixaDialogo.ativo = False
    else:
        caixaDialogo.indiceLetra = float(len(caixaDialogo.textoCompleto))
        caixaDialogo.textoAtual = caixaDialogo.textoCompleto


def comecarJogo():
    if SONS_OK:
        SOM_DING.play()
    iniciarTransicao(CENA_DENTRO_CARRO)


def tratarClique(mx_janela, my_janela):
    mouseX = mx_janela / ESCALA
    mouseY = my_janela / ESCALA

    if G.mostrarCartinha:
        btn = getattr(G, '_cartaFechaBtnRect', None)
        if btn:
            bx, by, bw, bh = btn
            if bx <= mouseX <= bx + bw and by <= mouseY <= by + bh:
                G.mostrarCartinha = False
        return

    if G.cenaAtual == CENA_INTRO:
        comecarJogo()
        return
    if caixaDialogo.ativo:
        avancarDialogo()
        return
    if G.cenaAtual == CENA_6_PROGRAMACAO and G.cliqueDisponivel:
        if G.playRect:
            cx, cy, r = G.playRect
            if dist(mouseX, mouseY, cx, cy) <= r:
                reproduzir_video()
                return
        if G.cartaRect:
            cx, cy, r = G.cartaRect
            if dist(mouseX, mouseY, cx, cy) <= r:
                abrir_cartinha()
                return


TECLA_NOME = {
    pygame.K_w: 'w', pygame.K_a: 'a', pygame.K_s: 's', pygame.K_d: 'd',
    pygame.K_UP: 'arrowup', pygame.K_DOWN: 'arrowdown',
    pygame.K_LEFT: 'arrowleft', pygame.K_RIGHT: 'arrowright',
}


def main():
    rodando = True
    while rodando:
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                rodando = False
            elif ev.type == pygame.KEYDOWN:
                nome = TECLA_NOME.get(ev.key)
                if nome:
                    teclasPressionadas[nome] = True
                if ev.key == pygame.K_ESCAPE and G.mostrarCartinha:
                    G.mostrarCartinha = False
                # Controles globais de som/tela
                if ev.key == pygame.K_m:
                    alternar_mute()
                elif ev.key in (pygame.K_PLUS, pygame.K_EQUALS, pygame.K_KP_PLUS):
                    ajustar_volume(+0.1)
                elif ev.key in (pygame.K_MINUS, pygame.K_KP_MINUS):
                    ajustar_volume(-0.1)
                elif ev.key == pygame.K_F11:
                    alternar_tela_cheia()
                elif ev.key == pygame.K_p:
                    alternar_pausa()
                if ev.key == pygame.K_RETURN:
                    if G.mostrarCartinha:
                        G.mostrarCartinha = False
                    elif G.cenaAtual == CENA_INTRO:
                        comecarJogo()
                    elif caixaDialogo.ativo:
                        avancarDialogo()
                elif ev.key == pygame.K_r:
                    if G.cenaAtual == CENA_6_PROGRAMACAO and not caixaDialogo.ativo:
                        resetarVariaveisCenas()
                        parar_musica_fundo()
                        G.cenaAtual = CENA_INTRO
                        G.introTimer = 0
            elif ev.type == pygame.KEYUP:
                nome = TECLA_NOME.get(ev.key)
                if nome:
                    teclasPressionadas[nome] = False
            elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                if G.pausado:
                    pass
                elif G.cenaAtual == CENA_INTRO:
                    tratarClique(ev.pos[0], ev.pos[1])
                elif G.mostrarCartinha:
                    tratarClique(ev.pos[0], ev.pos[1])
                elif controlandoPersonagem():
                    G.toqueDestinoX = ev.pos[0] / ESCALA
                    G.toqueDestinoY = ev.pos[1] / ESCALA
                    G.toqueAtivo = True
                else:
                    tratarClique(ev.pos[0], ev.pos[1])
            elif ev.type == pygame.MOUSEMOTION:
                if G.toqueAtivo and controlandoPersonagem():
                    G.toqueDestinoX = ev.pos[0] / ESCALA
                    G.toqueDestinoY = ev.pos[1] / ESCALA
            elif ev.type == pygame.MOUSEBUTTONUP and ev.button == 1:
                G.toqueAtivo = False

        if not G.pausado:
            atualizarMovimentoCarroJogador()
            atualizarMovimentoHomem()
            atualizarMovimentoCasalCena4()
            atualizarMovimentoQuartoEntrando()
            atualizarMovimentoMimiQuarto()
            gerenciarObstaculosEColisoes()
            atualizar()
        desenhar()
        pygame.display.flip()
        clock.tick(FPS)

    parar_musica_fundo()
    pygame.quit()


# Volume / mute globais (definidos antes do uso em runtime)
_volume_musica = 0.22
_musica_mutada = False


if __name__ == "__main__":
    main()ESCALA = 2
FPS = 60

VIDEO_EXTS = ('.mp4', '.mov', '.avi', '.mkv', '.webm', '.m4v', '.wmv')
VIDEO_PREFERIDOS = ('meu_video', 'video', 'nosso_video', 'mimi')


def hx(s):
    s = s.lstrip('#')
    return (int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16))


def lerp(a, b, t):
    return a + (b - a) * t


def lerp_cor(c1, c2, t):
    return (int(lerp(c1[0], c2[0], t)), int(lerp(c1[1], c2[1], t)), int(lerp(c1[2], c2[2], t)))


def clamp(v, lo, hi):
    return lo if v < lo else hi if v > hi else v


def pasta_base():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def encontrar_video():
    base = pasta_base()
    try:
        arquivos = os.listdir(base)
    except OSError:
        arquivos = []
    for nome in VIDEO_PREFERIDOS:
        for ext in VIDEO_EXTS:
            p = os.path.join(base, nome + ext)
            if os.path.exists(p):
                return p
    for f in sorted(arquivos):
        if f.lower().endswith(VIDEO_EXTS):
            return os.path.join(base, f)
    return None


def encontrar_cartinha():
    """Procura um arquivo carta.txt ou similar na pasta do jogo."""
    base = pasta_base()
    nomes = ('carta', 'cartinha', 'mensagem', 'letter', 'minha_carta')
    for nome in nomes:
        for ext in ('.txt', '.md'):
            p = os.path.join(base, nome + ext)
            if os.path.exists(p):
                return p
    return None


def reproduzir_video():
    cam = encontrar_video()
    if not cam:
        G.videoMsg = "Coloca um video (.mp4) na pasta do jogo!"
        G.videoExiste = False
        return
    G.videoExiste = True
    try:
        if sys.platform.startswith('win'):
            os.startfile(cam)
        elif sys.platform == 'darwin':
            subprocess.Popen(['open', cam])
        else:
            subprocess.Popen(['xdg-open', cam])
        G.videoMsg = "A reproduzir no teu leitor de video..."
    except Exception:
        G.videoMsg = "Nao consegui abrir o video."


def abrir_cartinha():
    cam = encontrar_cartinha()
    if cam:
        try:
            if sys.platform.startswith('win'):
                os.startfile(cam)
            elif sys.platform == 'darwin':
                subprocess.Popen(['open', cam])
            else:
                subprocess.Popen(['xdg-open', cam])
            G.cartaMsg = "Abrindo a cartinha..."
            return
        except Exception:
            pass
    # Se não encontrou arquivo, mostra mensagem embutida
    G.mostrarCartinha = True
    G.cartaMsg = ""


# Paleta
COR_ASFALTO = hx('#3a4248')
COR_GRAMA = hx('#4a7551')
COR_CAIXA_DIALOGO = hx('#4e311f')
COR_BORDA_DIALOGO = hx('#caa074')
COR_TEXTO = hx('#fcf5db')

# Cenas
CENA_INTRO = 0
CENA_1_ESTRADA = 1
CENA_2_KIKAO = 2
CENA_3_VIAGEM = 3
CENA_4_CHEGADA_CASA = 4
CENA_5_QUARTO = 5
CENA_6_PROGRAMACAO = 6


# ==============================================================================
# SOM PROCEDURAL
# ==============================================================================
pygame.mixer.pre_init(44100, -16, 2, 512)
pygame.init()
pygame.mixer.init(44100, -16, 2, 512)

SAMPLE_RATE = 44100
SONS_OK = False


def _buf(n):
    return array.array('h', [0] * n)


def _gerar_som_motor():
    ms = 800
    n = int(SAMPLE_RATE * ms / 1000)
    buf = _buf(n)
    for i in range(n):
        t = i / SAMPLE_RATE
        v = (math.sin(2 * math.pi * 80 * t) * 0.4 +
             math.sin(2 * math.pi * 160 * t) * 0.3 +
             (random.random() - 0.5) * 0.15)
        buf[i] = int(clamp(v, -1, 1) * 0.25 * 32767)
    return pygame.sndarray.make_sound(buf)


def _gerar_som_passos():
    n = int(SAMPLE_RATE * 0.12)
    buf = _buf(n)
    for i in range(n):
        env = 1.0 - (i / n) ** 0.5
        buf[i] = int((random.random() - 0.5) * 2 * env * 0.35 * 32767)
    return pygame.sndarray.make_sound(buf)


def _gerar_som_colisao():
    n = int(SAMPLE_RATE * 0.25)
    buf = _buf(n)
    for i in range(n):
        t = i / SAMPLE_RATE
        env = (1.0 - i / n) ** 0.3
        freq = max(30, 200 - t * 400)
        v = math.sin(2 * math.pi * freq * t) * env + (random.random() - 0.5) * 0.4 * env
        buf[i] = int(clamp(v, -1, 1) * 0.5 * 32767)
    return pygame.sndarray.make_sound(buf)


def _gerar_bip(freq, ms, vol=0.2):
    n = int(SAMPLE_RATE * ms / 1000)
    buf = _buf(n)
    for i in range(n):
        env = math.sin(math.pi * i / n)
        buf[i] = int(math.sin(2 * math.pi * freq * i / SAMPLE_RATE) * env * vol * 32767)
    return pygame.sndarray.make_sound(buf)


def _gerar_transicao():
    n = int(SAMPLE_RATE * 0.55)
    buf = _buf(n)
    for i in range(n):
        t = i / SAMPLE_RATE
        freq = 220 + (i / n) * 440
        env = math.sin(math.pi * i / n)
        buf[i] = int(math.sin(2 * math.pi * freq * t) * env * 0.28 * 32767)
    return pygame.sndarray.make_sound(buf)


def _gerar_fanfarra():
    notas = [(523, 0.14), (659, 0.14), (784, 0.24)]
    total = sum(d for _, d in notas)
    n = int(SAMPLE_RATE * total)
    buf = _buf(n)
    pos = 0
    for freq, dur in notas:
        sn = int(SAMPLE_RATE * dur)
        for i in range(sn):
            if pos + i < n:
                env = math.sin(math.pi * i / sn)
                buf[pos + i] = int(math.sin(2 * math.pi * freq * i / SAMPLE_RATE) * env * 0.4 * 32767)
        pos += sn
    return pygame.sndarray.make_sound(buf)


def _gerar_ding():
    n = int(SAMPLE_RATE * 0.5)
    buf = _buf(n)
    for i in range(n):
        env = (1.0 - i / n) ** 1.5
        v = (math.sin(2 * math.pi * 880 * i / SAMPLE_RATE) * 0.6 +
             math.sin(2 * math.pi * 1320 * i / SAMPLE_RATE) * 0.3) * env
        buf[i] = int(v * 0.35 * 32767)
    return pygame.sndarray.make_sound(buf)


def _gerar_musica_intro():
    notas = [(330, 0.18), (392, 0.18), (440, 0.18), (392, 0.18),
             (330, 0.25), (0, 0.12),
             (294, 0.18), (330, 0.18), (392, 0.35), (0, 0.15)]
    total = sum(d for _, d in notas)
    n = int(SAMPLE_RATE * total)
    buf = _buf(n)
    pos = 0
    for freq, dur in notas:
        sn = int(SAMPLE_RATE * dur)
        for i in range(sn):
            if pos + i < n:
                if freq == 0:
                    buf[pos + i] = 0
                else:
                    env = math.sin(math.pi * i / sn) ** 0.5
                    sq = 1.0 if math.sin(2 * math.pi * freq * i / SAMPLE_RATE) > 0 else -1.0
                    buf[pos + i] = int(sq * env * 0.18 * 32767)
        pos += sn
    return pygame.sndarray.make_sound(buf)


try:
    SOM_MOTOR = _gerar_som_motor()
    SOM_PASSOS = _gerar_som_passos()
    SOM_COLISAO = _gerar_som_colisao()
    SOM_BIP = _gerar_bip(440, 80)
    SOM_TRANSICAO = _gerar_transicao()
    SOM_CHEGADA = _gerar_fanfarra()
    SOM_DING = _gerar_ding()
    SOM_INTRO = _gerar_musica_intro()
    SONS_OK = True
except Exception as e:
    print(f"[Aviso] Sons desativados: {e}")

# Música de fundo MP3
MUSICA_FUNDO_OK = False
_musica_fundo_tocando = False


def _carregar_musica_fundo():
    global MUSICA_FUNDO_OK
    base = pasta_base()
    script_dir = os.path.dirname(os.path.abspath(__file__)) if not getattr(sys, 'frozen', False) else base
    cwd = os.getcwd()
    caminhos = []
    for nome in ('videoplayback.mp3', 'musica.mp3', 'music.mp3', 'fundo.mp3',
                 'videoplayback.ogg', 'musica.ogg', 'music.ogg', 'fundo.ogg'):
        for d in (base, script_dir, cwd):
            p = os.path.join(d, nome)
            if p not in caminhos:
                caminhos.append(p)
    # Qualquer MP3/OGG na pasta base e no script_dir
    for search_dir in set([base, script_dir, cwd]):
        try:
            for f in sorted(os.listdir(search_dir)):
                if f.lower().endswith(('.mp3', '.ogg', '.wav')):
                    p = os.path.join(search_dir, f)
                    if p not in caminhos:
                        caminhos.append(p)
        except OSError:
            pass
    vistos = set()
    for p in caminhos:
        if p in vistos:
            continue
        vistos.add(p)
        if not os.path.exists(p):
            continue
        try:
            pygame.mixer.music.load(p)
            pygame.mixer.music.set_volume(0.40)
            MUSICA_FUNDO_OK = True
            print(f"[Musica] Carregada com sucesso: {p}")
            return
        except Exception as e:
            print(f"[Musica] Nao carregou {os.path.basename(p)}: {e}")
    # Nenhum arquivo funcionou — tenta converter MP3 -> OGG com pydub
    print("[Musica] Tentando converter MP3 para OGG via pydub...")
    for search_dir in set([base, script_dir, cwd]):
        try:
            for f in sorted(os.listdir(search_dir)):
                if f.lower().endswith('.mp3'):
                    mp3_path = os.path.join(search_dir, f)
                    ogg_path = mp3_path[:-4] + '_converted.ogg'
                    try:
                        from pydub import AudioSegment
                        seg = AudioSegment.from_mp3(mp3_path)
                        seg.export(ogg_path, format='ogg')
                        pygame.mixer.music.load(ogg_path)
                        pygame.mixer.music.set_volume(0.40)
                        MUSICA_FUNDO_OK = True
                        print(f"[Musica] Convertido e carregado: {ogg_path}")
                        return
                    except ImportError:
                        print("[Musica] pydub nao instalado. Para converter: pip install pydub")
                    except Exception as e2:
                        print(f"[Musica] Falha na conversao: {e2}")
        except OSError:
            pass
    print("[Musica] FALHA: nao foi possivel carregar nenhum audio.")
    print("[Musica] SOLUCAO: converte o videoplayback.mp3 para .ogg (ex: via Audacity ou online)")
    print("[Musica] e coloca o videoplayback.ogg na mesma pasta do .py")


# NÃO carregamos a música aqui — aguardamos até após pygame.display.set_mode()
# para garantir que o mixer está totalmente inicializado.

_t_motor = 0
_t_passos = 0
_intro_musica_on = False


def tocar_motor():
    global _t_motor
    if not SONS_OK:
        return
    agora = pygame.time.get_ticks()
    if agora - _t_motor > 820:
        _t_motor = agora
        SOM_MOTOR.play()


def tocar_passos():
    global _t_passos
    if not SONS_OK:
        return
    agora = pygame.time.get_ticks()
    if agora - _t_passos > 290:
        _t_passos = agora
        SOM_PASSOS.play()


def iniciar_musica_fundo():
    global _musica_fundo_tocando
    if not MUSICA_FUNDO_OK:
        return
    if not _musica_fundo_tocando:
        try:
            pygame.mixer.music.play(-1)  # -1 = loop infinito
            pygame.mixer.music.set_volume(0.0 if _musica_mutada else _volume_musica)
            _musica_fundo_tocando = True
            print("[Musica] Tocando em loop.")
        except Exception as e:
            print(f"[Música] Erro ao tocar: {e}")


def parar_musica_fundo():
    global _musica_fundo_tocando
    if _musica_fundo_tocando:
        try:
            pygame.mixer.music.stop()
            _musica_fundo_tocando = False
        except Exception:
            pass


# ==============================================================================
# ESTADO GLOBAL
# ==============================================================================
class G:
    cenaAtual = CENA_INTRO
    transicaoAlfa = 0.0
    transitando = False
    direcaoTransicao = 1
    proximaCena = None

    # Tela Intro
    introTimer = 0
    introEstrelas = [(random.randint(0, 399), random.randint(0, 185), random.random())
                     for _ in range(42)]

    carroX = 10.0
    carroY = 185.0
    estradaOffset = 0.0
    velocidadeManual = 1.6
    VELOCIDADE_ALVO = 1.6

    listaObstaculos = []
    timerGerarObstaculo = 0
    colidirTimer = 0

    homemX = 0.0
    homemY = 0.0
    homemAtivo = False
    homemComLanche = False
    homemVisivel = True
    dinerTimer = 0
    kikaoEstado = "conduzindo_para_parar"

    casaX = 220
    casaY = 60
    casalAtivo = False
    casalX = 0.0
    casalY = 0.0

    camaX = 90
    camaY = 100
    mesaX = 260
    mesaY = 115
    quartoLuzAcesa = False
    mulherQuartoX = 30.0
    mulherQuartoY = 190.0
    homemQuartoX = 16.0
    homemQuartoY = 194.0
    quartoEstado = "entrando"
    quartoTimer = 0
    notebookAceso = False

    notebookZoom = 0.0
    introMostrada = False
    cliqueDisponivel = False
    puloCliqueNotebook = 0.0
    videoExiste = False
    videoMsg = ""
    cartaMsg = ""
    mostrarCartinha = False
    playRect = None
    cartaRect = None

    tempoPasso = 0.0
    tempoCeu = 0.0

    toqueAtivo = False
    toqueDestinoX = 0.0
    toqueDestinoY = 0.0

    statusCena = "Cena 1: A Viagem Começa..."
    somChegadaTocado = False
    somDingTocado = False

    # Controle do diálogo do Lusca na cena 4
    luscaDialogoMostrado = False

    # Melhorias novas
    pausado = False
    telaCheia = False
    volumeMsg = ""
    volumeMsgTimer = 0
    coracoes = []
    coracaoTimer = 0


teclasPressionadas = {}

janela = pygame.display.set_mode((LARGURA * ESCALA, ALTURA * ESCALA))
pygame.display.set_caption("Joguinho pro Meu Amor <3")
clock = pygame.time.Clock()
tela = pygame.Surface((LARGURA, ALTURA))

# Carregar música APÓS set_mode() para garantir que o mixer está pronto
_carregar_musica_fundo()

FONT_CACHE = {}
_fila_texto = []


def fonte(tam, bold=False):
    chave = (tam, bold)
    if chave not in FONT_CACHE:
        FONT_CACHE[chave] = pygame.font.SysFont(
            "segoeui,verdana,arial,dejavusans,freesans", tam, bold=bold)
    return FONT_CACHE[chave]


def texto(_surf, txt, x, y, tam, cor, align='left', bold=False):
    _fila_texto.append((str(txt), float(x), float(y), int(tam), cor, align, bold))


def medir_texto(txt, tam, bold=False):
    return fonte(int(tam * ESCALA), bold).size(str(txt))[0] / ESCALA


def _render_fila_texto():
    for (t, x, y, tam, cor, align, bold) in _fila_texto:
        f = fonte(int(tam * ESCALA), bold)
        img = f.render(t, True, cor)
        r = img.get_rect()
        wx, wy = x * ESCALA, y * ESCALA
        if align == 'center':
            r.midtop = (int(wx), int(wy))
        elif align == 'right':
            r.topright = (int(wx), int(wy))
        else:
            r.topleft = (int(wx), int(wy))
        janela.blit(img, r)


def linha_tracejada(surf, cor, x1, y, x2, dash=10, gap=10, esp=1):
    x = x1
    while x < x2:
        pygame.draw.line(surf, cor, (x, y), (min(x + dash, x2), y), esp)
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
        pygame.draw.rect(tela, (15, 25, 15), (x + 1, y + self.altura - 2, self.largura - 2, 2))
        if self.tipo == 'carro':
            pygame.draw.rect(tela, self.cor, (x, y + 4, self.largura, self.altura - 4))
            pygame.draw.rect(tela, hx('#90afc5'), (x + 5, y, self.largura - 10, 5))
            pygame.draw.rect(tela, hx('#141416'), (x + 4, y + self.altura - 2, 5, 2))
            pygame.draw.rect(tela, hx('#141416'), (x + self.largura - 9, y + self.altura - 2, 5, 2))
            cf = hx('#fff4a3') if self.velocidade < 0 else hx('#ff3333')
            pygame.draw.rect(tela, cf, (x, y + 6, 1, 2))
        else:
            pygame.draw.rect(tela, self.cor, (x + 3, y + 2, self.largura - 6, self.altura - 4))
            pygame.draw.rect(tela, hx('#141416'), (x, y + self.altura - 2, 3, 2))
            pygame.draw.rect(tela, hx('#141416'), (x + self.largura - 3, y + self.altura - 2, 3, 2))
            pygame.draw.rect(tela, hx('#222222'), (x + 6, y, 5, 4))
            cf = hx('#fff4a3') if self.velocidade < 0 else hx('#ff3333')
            fx = x if self.velocidade < 0 else x + self.largura - 1
            pygame.draw.rect(tela, cf, (fx, y + 3, 1, 1))


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
        self.feliz = False

    def atualizar(self, perto):
        self.feliz = perto
        if self.feliz:
            self.anguloBalanco += 0.4
            off = abs(math.sin(self.anguloBalanco) * 7)
        else:
            self.anguloBalanco += 0.05
            off = abs(math.sin(self.anguloBalanco) * 1.5)
        self.y = self.baseY - off

    def desenhar(self):
        x, y = self.x, self.y
        pygame.draw.rect(tela, (15, 25, 15), (x + 1, self.baseY + 11, 10, 2))
        pygame.draw.rect(tela, self.cor, (x + 1, y + 5, 10, 7))
        pygame.draw.rect(tela, self.cor, (x + 2, y + 1, 8, 5))
        pygame.draw.rect(tela, hx('#0f0f0f'), (x + 3, y + 2, 1, 1))
        pygame.draw.rect(tela, hx('#0f0f0f'), (x + 7, y + 2, 1, 1))
        if self.tipo == 'gato':
            pygame.draw.rect(tela, hx('#e8a3a3'), (x + 5, y + 3, 1, 1))
            pygame.draw.rect(tela, self.corOrelhas, (x + 2, y, 1, 1))
            pygame.draw.rect(tela, self.corOrelhas, (x + 8, y, 1, 1))
        else:
            pygame.draw.rect(tela, hx('#111111'), (x + 5, y + 3, 2, 1))
            pygame.draw.rect(tela, self.corOrelhas, (x + 1, y + 2, 1, 3))
            pygame.draw.rect(tela, self.corOrelhas, (x + 9, y + 2, 1, 3))

        if self.feliz and self.fala:
            largTexto = medir_texto(self.fala, 6, True)
            bw = largTexto + 6
            bh = 11
            bx = x + 6 - bw / 2
            by = y - 15
            pygame.draw.rect(tela, (0, 0, 0), (bx + 1, by + 1, bw, bh))
            pygame.draw.rect(tela, hx('#ffffff'), (bx, by, bw, bh))
            pygame.draw.rect(tela, hx('#000000'), (bx, by, bw, bh), 1)
            pts = [(x + 4, by + bh), (x + 6, by + bh + 3), (x + 8, by + bh)]
            pygame.draw.polygon(tela, hx('#ffffff'), pts)
            pygame.draw.lines(tela, hx('#000000'), False, pts, 1)
            texto(tela, self.fala, x + 6, by + 1, 6, (0, 0, 0), align='center', bold=True)


class CoracaoFlutuante:
    """Coraçãozinho pixelado que sobe e some, para momentos fofos."""
    CORES = [hx('#ec607a'), hx('#ff88bb'), hx('#ffd0e8'), hx('#e8607f')]

    def __init__(self, x, y):
        self.x = float(x)
        self.y = float(y)
        self.vy = -random.uniform(0.35, 0.85)
        self.vx = random.uniform(-0.3, 0.3)
        self.vida = 1.0
        self.s = random.choice([2, 2, 3])
        self.fase = random.uniform(0, math.pi * 2)
        self.cor = random.choice(CoracaoFlutuante.CORES)

    def atualizar(self):
        self.y += self.vy
        self.x += self.vx + math.sin(self.fase + self.y * 0.05) * 0.3
        self.vida -= 0.009

    def viva(self):
        return self.vida > 0

    def desenhar(self):
        a = int(clamp(self.vida, 0, 1) * 255)
        s = self.s
        surf = pygame.Surface((s * 3, s * 4), pygame.SRCALPHA)
        cor = (self.cor[0], self.cor[1], self.cor[2], a)
        # dois "lóbulos" no topo
        pygame.draw.rect(surf, cor, (0, 0, s, s))
        pygame.draw.rect(surf, cor, (s * 2, 0, s, s))
        # corpo
        pygame.draw.rect(surf, cor, (0, s, s * 3, s))
        pygame.draw.rect(surf, cor, (s // 2, s * 2, s * 2, s))
        # ponta
        pygame.draw.rect(surf, cor, (s, s * 3, s, s))
        tela.blit(surf, (int(self.x), int(self.y)))


def soltar_coracoes(x, y, n=1):
    for _ in range(n):
        G.coracoes.append(CoracaoFlutuante(x + random.uniform(-6, 6), y + random.uniform(-4, 4)))


def desenharCoracoes():
    for c in G.coracoes:
        c.desenhar()


listaPets = [
    Pet("Shitzu Branca", "cao", 320, 155, hx('#f5f5f5'), hx('#d9c3b0'), "auuu"),
    Pet("Cão Bege", "cao", 350, 165, hx('#e3cda6'), hx('#c0a373'), "auau"),
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
        self.velocidadeEscrita = 0.5
        self.tempoCursor = 0
        self._ultimaLetra = 0

    def iniciar(self, txt):
        self.textoCompleto = txt
        self.textoAtual = ""
        self.indiceLetra = 0.0
        self.ativo = True
        self._ultimaLetra = 0

    def atualizar(self):
        if not self.ativo:
            return
        if self.indiceLetra < len(self.textoCompleto):
            self.indiceLetra += self.velocidadeEscrita
            novo = int(self.indiceLetra)
            if SONS_OK and novo > self._ultimaLetra and novo % 3 == 0:
                SOM_BIP.play()
            self._ultimaLetra = novo
            self.textoAtual = self.textoCompleto[:novo]
        self.tempoCursor += 1

    def desenhar(self):
        if not self.ativo:
            return
        pygame.draw.rect(tela, COR_CAIXA_DIALOGO, (20, 220, 360, 70))
        pygame.draw.rect(tela, COR_BORDA_DIALOGO, (20, 220, 360, 70), 3)
        pygame.draw.rect(tela, hx('#2b1b11'), (23, 223, 354, 64), 1)
        palavras = self.textoAtual.split(' ')
        linhas, atual = [], ""
        for palavra in palavras:
            teste = atual + palavra + " "
            if medir_texto(teste, 13) < 330:
                atual = teste
            else:
                linhas.append(atual)
                atual = palavra + " "
        linhas.append(atual)
        yOff = 230
        for linha in linhas:
            texto(tela, linha, 35, yOff, 13, COR_TEXTO)
            yOff += 17
        if self.indiceLetra >= len(self.textoCompleto):
            if (self.tempoCursor // 20) % 2 == 0:
                texto(tela, "▼", 360, 270, 12, COR_BORDA_DIALOGO)


caixaDialogo = CaixaDialogo()


# ==============================================================================
# CONTROLO
# ==============================================================================
def k(*nomes):
    return any(teclasPressionadas.get(n, False) for n in nomes)


def inputs_para(cx, cy, mx=12, my=10):
    direita = k('d', 'arrowright')
    esquerda = k('a', 'arrowleft')
    cima = k('w', 'arrowup')
    baixo = k('s', 'arrowdown')
    if G.toqueAtivo:
        dx = G.toqueDestinoX - cx
        dy = G.toqueDestinoY - cy
        if abs(dx) > mx:
            direita = dx > 0
            esquerda = dx < 0
        if abs(dy) > my:
            baixo = dy > 0
            cima = dy < 0
    return direita, esquerda, cima, baixo


def _livre():
    return not caixaDialogo.ativo and not G.transitando and not G.pausado


def podeConduzir():
    if not _livre():
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
    return _livre() and G.cenaAtual == CENA_2_KIKAO and G.kikaoEstado in ("descendo", "voltando")


def podeMoverCasalCena4():
    return _livre() and G.cenaAtual == CENA_4_CHEGADA_CASA and G.kikaoEstado == "casal_controlado"


def podeMoverQuartoEntrando():
    return _livre() and G.cenaAtual == CENA_5_QUARTO and G.quartoEstado == "entrando"


def podeMoverMimiQuarto():
    return _livre() and G.cenaAtual == CENA_5_QUARTO and G.quartoEstado == "andando"


def controlandoPersonagem():
    return (podeConduzir() or podeMoverHomem() or podeMoverCasalCena4() or
            podeMoverQuartoEntrando() or podeMoverMimiQuarto())


def obterHitboxCarro():
    return {'x': G.carroX + 4, 'y': G.carroY + 8, 'l': 40, 'a': 11}


def atualizarMovimentoCarroJogador():
    if not podeConduzir():
        return
    d, e, c, b = inputs_para(G.carroX + 24, G.carroY + 10, 15, 10)
    if (d or e or c or b) and SONS_OK:
        tocar_motor()
    if d:
        G.carroX += G.velocidadeManual
        if G.cenaAtual in (CENA_1_ESTRADA, CENA_3_VIAGEM):
            G.estradaOffset -= G.velocidadeManual
    elif e:
        G.carroX -= G.velocidadeManual
        if G.carroX < -60:
            G.carroX = -60
        if G.cenaAtual in (CENA_1_ESTRADA, CENA_3_VIAGEM):
            G.estradaOffset += G.velocidadeManual
    if c:
        G.carroY = max(170, G.carroY - 1.3)
    elif b:
        G.carroY = min(205, G.carroY + 1.3)


def atualizarMovimentoHomem():
    if not podeMoverHomem():
        return
    d, e, c, b = inputs_para(G.homemX + 5, G.homemY + 12)
    if (d or e or c or b) and SONS_OK:
        tocar_passos()
    v = 1.0
    if d: G.homemX += v
    if e: G.homemX -= v
    if c: G.homemY -= v
    if b: G.homemY += v
    G.homemX = clamp(G.homemX, 10, LARGURA - 20)
    G.homemY = clamp(G.homemY, 120, 210)


def atualizarMovimentoCasalCena4():
    if not podeMoverCasalCena4():
        return
    d, e, c, b = inputs_para(G.casalX + 5, G.casalY + 12)
    if (d or e or c or b) and SONS_OK:
        tocar_passos()
    v = 1.2
    if d: G.casalX += v
    if e: G.casalX -= v
    if c: G.casalY -= v
    if b: G.casalY += v
    G.casalX = clamp(G.casalX, 5, LARGURA - 15)
    G.casalY = clamp(G.casalY, 95, 200)


def atualizarMovimentoQuartoEntrando():
    if not podeMoverQuartoEntrando():
        return
    d, e, c, b = inputs_para(G.mulherQuartoX + 5, G.mulherQuartoY + 12)
    if (d or e or c or b) and SONS_OK:
        tocar_passos()
    v = 1.0
    if d: G.mulherQuartoX += v
    if e: G.mulherQuartoX -= v
    if c: G.mulherQuartoY -= v
    if b: G.mulherQuartoY += v
    G.mulherQuartoX = clamp(G.mulherQuartoX, 12, LARGURA - 20)
    G.mulherQuartoY = clamp(G.mulherQuartoY, 130, 205)
    G.homemQuartoX = clamp(G.mulherQuartoX - 13, 6, LARGURA - 20)
    G.homemQuartoY = clamp(G.mulherQuartoY + 4, 130, 205)


def atualizarMovimentoMimiQuarto():
    if not podeMoverMimiQuarto():
        return
    d, e, c, b = inputs_para(G.mulherQuartoX + 5, G.mulherQuartoY + 12)
    if (d or e or c or b) and SONS_OK:
        tocar_passos()
    v = 1.0
    if d: G.mulherQuartoX += v
    if e: G.mulherQuartoX -= v
    if c: G.mulherQuartoY -= v
    if b: G.mulherQuartoY += v
    G.mulherQuartoX = clamp(G.mulherQuartoX, 12, LARGURA - 20)
    G.mulherQuartoY = clamp(G.mulherQuartoY, 130, 205)


def gerenciarObstaculosEColisoes():
    if not podeConduzir() or G.cenaAtual == CENA_4_CHEGADA_CASA:
        G.listaObstaculos = []
        return
    G.timerGerarObstaculo += 1
    taxa = 35 if G.cenaAtual == CENA_3_VIAGEM else 55
    if G.timerGerarObstaculo >= taxa:
        G.timerGerarObstaculo = 0
        tipo = 'carro' if random.random() > 0.4 else 'moto'
        spawnY = 172 if random.random() > 0.5 else 200
        vemDeFrente = random.random() > 0.35
        vel = -3.8 if vemDeFrente else 0.8
        col = hx('#2980b9') if random.random() > 0.5 else hx('#27ae60') if tipo == 'carro' else hx('#f1c40f')
        G.listaObstaculos.append(Obstaculo(tipo, LARGURA + 30, spawnY, vel, col))

    velRef = G.velocidadeManual if (k('d', 'arrowright') or
                                    (G.toqueAtivo and G.toqueDestinoX > G.carroX + 24)) else 0
    for obs in G.listaObstaculos:
        obs.atualizar(velRef)
    G.listaObstaculos = [o for o in G.listaObstaculos if -50 < o.x < LARGURA + 100]

    if G.velocidadeManual < G.VELOCIDADE_ALVO:
        G.velocidadeManual = min(G.VELOCIDADE_ALVO, G.velocidadeManual + 0.04)
    if G.colidirTimer > 0:
        G.colidirTimer -= 1

    if G.colidirTimer == 0:
        hb = obterHitboxCarro()
        for obs in G.listaObstaculos:
            if (hb['x'] < obs.x + obs.largura and hb['x'] + hb['l'] > obs.x and
                    hb['y'] < obs.y + obs.altura and hb['y'] + hb['a'] > obs.y):
                G.colidirTimer = 50
                G.velocidadeManual = 0.4
                G.carroX = max(-60, G.carroX - 15)
                G.listaObstaculos.remove(obs)
                if SONS_OK:
                    SOM_COLISAO.play()
                break


def resetarVariaveisCenas():
    G.carroX = 10.0
    G.carroY = 185.0
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
    G.quartoLuzAcesa = False
    G.mulherQuartoX = 30.0
    G.mulherQuartoY = 190.0
    G.homemQuartoX = 16.0
    G.homemQuartoY = 194.0
    G.quartoEstado = "entrando"
    G.quartoTimer = 0
    G.notebookAceso = False
    G.notebookZoom = 0.0
    G.introMostrada = False
    G.cliqueDisponivel = False
    G.puloCliqueNotebook = 0.0
    G.videoMsg = ""
    G.cartaMsg = ""
    G.mostrarCartinha = False
    G.playRect = None
    G.cartaRect = None
    G.somChegadaTocado = False
    G.somDingTocado = False
    G.luscaDialogoMostrado = False
    G.pausado = False
    G.coracoes = []
    G.coracaoTimer = 0
    caixaDialogo.ativo = False
    for key in list(teclasPressionadas.keys()):
        teclasPressionadas[key] = False


def iniciarTransicao(proxima):
    if not G.transitando:
        G.transitando = True
        G.direcaoTransicao = 1
        G.proximaCena = proxima
        if SONS_OK and proxima != CENA_INTRO:
            SOM_TRANSICAO.play()


def atualizarStatus(t):
    G.statusCena = t


def gerenciarTransicao():
    if not G.transitando:
        return
    G.transicaoAlfa += G.direcaoTransicao * 0.04
    # Fade suave da música acompanhando o escurecer/clarear da tela
    if MUSICA_FUNDO_OK and not _musica_mutada and _musica_fundo_tocando:
        try:
            pygame.mixer.music.set_volume(_volume_musica * (1.0 - G.transicaoAlfa * 0.85))
        except Exception:
            pass
    if G.transicaoAlfa >= 1:
        G.transicaoAlfa = 1.0
        G.cenaAtual = G.proximaCena
        G.listaObstaculos = []
        if G.cenaAtual == CENA_1_ESTRADA:
            atualizarStatus("Cena 1: A Viagem Começa...")
        elif G.cenaAtual == CENA_2_KIKAO:
            G.carroX = -50
            G.kikaoEstado = "conduzindo_para_parar"
            atualizarStatus("Cena 2: Estaciona o carro na vaga amarela!")
        elif G.cenaAtual == CENA_3_VIAGEM:
            G.carroX = -60
            atualizarStatus("Cena 3: Desvia-te do tráfego rápido!")
        elif G.cenaAtual == CENA_4_CHEGADA_CASA:
            G.carroX = -60
            G.kikaoEstado = "conduzindo_para_parar"
            G.luscaDialogoMostrado = False
            atualizarStatus("Cena 4: Conduz com carinho até casa...")
        elif G.cenaAtual == CENA_5_QUARTO:
            G.quartoTimer = 0
            G.quartoEstado = "entrando"
            G.mulherQuartoX = 30.0
            G.mulherQuartoY = 190.0
            G.homemQuartoX = 16.0
            G.homemQuartoY = 194.0
            atualizarStatus("Cena 5: Leva o casal até a cama...")
        elif G.cenaAtual == CENA_6_PROGRAMACAO:
            G.notebookZoom = 0.0
            G.introMostrada = False
            G.cliqueDisponivel = False
            G.videoExiste = encontrar_video() is not None
            atualizarStatus("Cena 6: O nosso vídeo <3")
        G.direcaoTransicao = -1
    elif G.transicaoAlfa <= 0:
        G.transicaoAlfa = 0.0
        G.transitando = False
        # Restaura o volume cheio ao terminar a transição
        if MUSICA_FUNDO_OK and not _musica_mutada and _musica_fundo_tocando:
            try:
                pygame.mixer.music.set_volume(_volume_musica)
            except Exception:
                pass


# ==============================================================================
# CENÁRIO
# ==============================================================================
def desenharCeu(c1, c2, y0, y1, bandas=18):
    h = (y1 - y0) / bandas
    for i in range(bandas):
        t = i / (bandas - 1)
        pygame.draw.rect(tela, lerp_cor(c1, c2, t), (0, int(y0 + i * h), LARGURA, int(h) + 1))


def desenharNuvem(x, y, s=1.0, cor=(248, 250, 255)):
    for bx, by, bw, bh in [(0, 4, 18, 6), (6, 0, 12, 6), (12, 3, 12, 6), (3, 8, 22, 4)]:
        pygame.draw.rect(tela, cor, (x + bx * s, y + by * s, bw * s, bh * s))


def desenharNuvensDeriva(bases, cor=(248, 250, 255)):
    for bx, by, s in bases:
        x = (bx + G.tempoCeu * 0.12) % (LARGURA + 60) - 30
        desenharNuvem(x, by + 2, s, (220, 228, 240))
        desenharNuvem(x, by, s, cor)


def desenharFlores(spots):
    for fx, fy, cor in spots:
        pygame.draw.rect(tela, cor, (fx, fy, 2, 2))
        pygame.draw.rect(tela, hx('#ffd54a'), (fx, fy, 1, 1))
        pygame.draw.rect(tela, hx('#2f5a36'), (fx, fy + 2, 1, 1))


FLORES_CAMPO = [
    (30, 110, hx('#e57ea0')), (70, 130, hx('#f0e36a')), (110, 100, hx('#e57ea0')),
    (150, 138, hx('#c98be0')), (185, 105, hx('#f0e36a')), (250, 120, hx('#e57ea0')),
    (300, 140, hx('#c98be0')), (40, 250, hx('#f0e36a')), (120, 270, hx('#e57ea0')),
    (210, 258, hx('#c98be0')), (300, 272, hx('#f0e36a')), (360, 245, hx('#e57ea0')),
]


def desenharArvore(ax, ay):
    pygame.draw.rect(tela, hx('#3c2817'), (ax - 2, ay - 8, 4, 8))
    pygame.draw.polygon(tela, hx('#224d30'), [(ax - 10, ay - 8), (ax, ay - 18), (ax + 10, ay - 8)])
    pygame.draw.polygon(tela, hx('#295c3a'), [(ax - 8, ay - 14), (ax, ay - 24), (ax + 8, ay - 14)])
    pygame.draw.polygon(tela, hx('#316b43'), [(ax - 5, ay - 20), (ax, ay - 29), (ax + 5, ay - 20)])


def desenharArvores():
    for ax, ay in [(40, 150), (90, 145), (360, 150), (380, 155)]:
        desenharArvore(ax, ay)


def desenharEstrada(topo, altura, tracejada=True):
    pygame.draw.rect(tela, COR_ASFALTO, (0, topo, LARGURA, altura))
    pygame.draw.rect(tela, hx('#5b6066'), (0, topo, LARGURA, 2))
    pygame.draw.rect(tela, hx('#5b6066'), (0, topo + altura - 2, LARGURA, 2))
    meio = topo + altura // 2
    if tracejada:
        linha_tracejada(tela, hx('#f5c542'), 0, meio, LARGURA)
    else:
        pygame.draw.line(tela, hx('#f5c542'), (0, meio), (LARGURA, meio), 1)


# ==============================================================================
# PERSONAGENS / OBJETOS
# ==============================================================================
def desenharCarroPixel(x, y):
    flash = G.colidirTimer > 0 and (G.colidirTimer // 4) % 2 == 0
    alvo = pygame.Surface((LARGURA, ALTURA), pygame.SRCALPHA) if flash else tela
    pygame.draw.rect(alvo, (15, 25, 15), (x + 2, y + 21, 44, 5))
    pygame.draw.rect(alvo, hx('#1b2240'), (x, y + 8, 48, 12))
    pygame.draw.rect(alvo, hx('#0c1024'), (x, y + 19, 48, 1))
    pygame.draw.rect(alvo, hx('#0c1024'), (x, y + 8, 1, 11))
    pygame.draw.rect(alvo, hx('#2c3a66'), (x + 1, y + 9, 47, 1))
    pygame.draw.rect(alvo, hx('#9fb8d4'), (x + 10, y, 26, 9))
    pygame.draw.rect(alvo, hx('#ffffff'), (x + 13, y + 2, 4, 4))
    pygame.draw.rect(alvo, hx('#ffffff'), (x + 26, y + 2, 5, 4))
    pygame.draw.rect(alvo, hx('#141416'), (x + 8, y + 17, 8, 6))
    pygame.draw.rect(alvo, hx('#141416'), (x + 32, y + 17, 8, 6))
    pygame.draw.rect(alvo, hx('#7a7a82'), (x + 11, y + 19, 2, 2))
    pygame.draw.rect(alvo, hx('#7a7a82'), (x + 35, y + 19, 2, 2))
    pygame.draw.rect(alvo, hx('#ff3333'), (x, y + 10, 1, 3))
    pygame.draw.rect(alvo, hx('#fff4a3'), (x + 47, y + 11, 1, 3))
    if G.cenaAtual in (CENA_3_VIAGEM, CENA_4_CHEGADA_CASA):
        cone = pygame.Surface((LARGURA, ALTURA), pygame.SRCALPHA)
        pygame.draw.polygon(cone, (255, 244, 163, 70),
                            [(x + 48, y + 11), (x + 85, y + 2), (x + 85, y + 22)])
        tela.blit(cone, (0, 0))  # sempre blita na tela base (que aceita SRCALPHA)
    if flash:
        alvo.set_alpha(90)
        tela.blit(alvo, (0, 0))
    if G.colidirTimer > 20:
        texto(tela, "OPS!", x + 24, y - 16, 10, hx('#e74c3c'), align='center', bold=True)


def desenharHomemPixel(x, y, bobbing=False):
    b = math.floor(math.sin(G.tempoPasso * 0.8) * 1.5) if bobbing else 0
    pygame.draw.rect(tela, (15, 25, 15), (x + 1, y + 25, 10, 2))
    pygame.draw.rect(tela, hx('#1f2d3d'), (x + 2, y + 18 + b, 3, 8 - b))
    pygame.draw.rect(tela, hx('#1f2d3d'), (x + 7, y + 18 + b, 3, 8 - b))
    pygame.draw.rect(tela, hx('#225d87'), (x + 1, y + 10 + b, 10, 9))
    pygame.draw.rect(tela, hx('#174363'), (x + 3, y + 9 + b, 6, 2))
    pygame.draw.rect(tela, hx('#f9cba0'), (x + 2, y + 3 + b, 8, 7))
    pygame.draw.rect(tela, hx('#4f2c15'), (x + 1, y + 1 + b, 10, 3))
    pygame.draw.rect(tela, hx('#4f2c15'), (x + 1, y + 3 + b, 2, 3))
    pygame.draw.rect(tela, hx('#4f2c15'), (x + 9, y + 3 + b, 2, 2))
    pygame.draw.rect(tela, hx('#111111'), (x + 4, y + 5 + b, 1, 1))
    pygame.draw.rect(tela, hx('#111111'), (x + 7, y + 5 + b, 1, 1))


def desenharMulherPixel(x, y, bobbing=False):
    """Mulher com cabelo castanho e blusa verde."""
    b = math.floor(math.sin(G.tempoPasso * 0.8) * 1.5) if bobbing else 0
    pygame.draw.rect(tela, (15, 25, 15), (x + 1, y + 25, 10, 2))
    # Pernas
    pygame.draw.rect(tela, hx('#261b2e'), (x + 2, y + 18 + b, 3, 8 - b))
    pygame.draw.rect(tela, hx('#261b2e'), (x + 7, y + 18 + b, 3, 8 - b))
    # Blusa verde
    pygame.draw.rect(tela, hx('#2d7a3a'), (x + 1, y + 10 + b, 10, 9))
    # Rosto
    pygame.draw.rect(tela, hx('#f9cba0'), (x + 2, y + 3 + b, 8, 7))
    # Cabelo castanho
    pygame.draw.rect(tela, hx('#6b3a1f'), (x + 1, y + 1 + b, 10, 3))
    pygame.draw.rect(tela, hx('#6b3a1f'), (x + 1, y + 4 + b, 2, 7))
    pygame.draw.rect(tela, hx('#6b3a1f'), (x + 9, y + 4 + b, 2, 7))
    # Olhos
    pygame.draw.rect(tela, hx('#111111'), (x + 4, y + 5 + b, 1, 1))
    pygame.draw.rect(tela, hx('#111111'), (x + 7, y + 5 + b, 1, 1))


def desenharLanchonete():
    pygame.draw.rect(tela, hx('#d97d26'), (150, 75, 120, 75))
    pygame.draw.rect(tela, hx('#9e5311'), (150, 149, 120, 1))
    pygame.draw.rect(tela, hx('#a82c2c'), (140, 65, 140, 11))
    pygame.draw.rect(tela, hx('#cc3b3b'), (140, 63, 140, 2))
    for i in range(0, 140, 16):
        pygame.draw.rect(tela, hx('#f2efe6'), (140 + i, 65, 8, 11))
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
    texto(tela, "KIKÃO", 210, 43, 11, hx('#a82c2c'), align='center', bold=True)


def desenharCasa():
    cx, cy = G.casaX, G.casaY
    pygame.draw.rect(tela, hx('#d8bd92'), (cx, cy, 120, 80))
    pygame.draw.rect(tela, hx('#c9ab81'), (cx, cy + 60, 120, 20))
    pygame.draw.polygon(tela, hx('#8f3333'), [(cx - 10, cy), (cx + 60, cy - 45), (cx + 130, cy)])
    pygame.draw.polygon(tela, hx('#a14040'), [(cx - 10, cy), (cx + 60, cy - 45), (cx + 30, cy)])
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
    for bx in (cx - 6, cx + 108):
        pygame.draw.rect(tela, hx('#2f5d39'), (bx, cy + 66, 14, 14))
        pygame.draw.rect(tela, hx('#3a7146'), (bx + 2, cy + 64, 10, 6))


def desenharCerca(y):
    for px in range(6, LARGURA, 26):
        pygame.draw.rect(tela, hx('#caa46f'), (px, y, 3, 16))
    pygame.draw.rect(tela, hx('#b8945f'), (0, y + 4, LARGURA, 2))
    pygame.draw.rect(tela, hx('#b8945f'), (0, y + 10, LARGURA, 2))


def desenharQuarto():
    desenharCeu(hx('#352a40'), hx('#26203a'), 0, 210)
    pygame.draw.rect(tela, hx('#5a3c28'), (0, 210, LARGURA, 90))
    for yy in range(210, ALTURA, 15):
        pygame.draw.line(tela, hx('#3a2517'), (0, yy), (LARGURA, yy), 1)
    pygame.draw.ellipse(tela, hx('#3f566e'), (G.camaX - 15, G.camaY + 95, 90, 30))
    pygame.draw.ellipse(tela, hx('#4d678a'), (G.camaX - 5, G.camaY + 102, 70, 16))
    pygame.draw.rect(tela, hx('#caa074'), (150, 18, 34, 26))
    pygame.draw.rect(tela, hx('#2a2238'), (153, 21, 28, 20))
    pygame.draw.rect(tela, hx('#e8607f'), (160, 27, 4, 4))
    pygame.draw.rect(tela, hx('#e8607f'), (168, 27, 4, 4))
    pygame.draw.rect(tela, hx('#e8607f'), (162, 30, 8, 4))
    pygame.draw.rect(tela, hx('#e8607f'), (164, 33, 4, 3))

    janela_x, janela_y = 10, 40
    janela_w, janela_h = 80, 65
    janela_surf = pygame.Surface((janela_w, janela_h))
    if not G.quartoLuzAcesa:
        janela_surf.fill(hx('#0e1430'))
        for sx, sy in [(8, 8), (22, 18), (38, 10), (55, 22), (18, 40), (50, 48)]:
            pygame.draw.rect(janela_surf, hx('#fdf6c8'), (sx, sy, 1, 1))
        pygame.draw.circle(janela_surf, hx('#f2efbf'), (62, 14), 5)
    else:
        bandas = 8
        h_banda = janela_h / bandas
        c1, c2 = hx('#9fc6dc'), hx('#dfeef2')
        for i in range(bandas):
            t = i / max(bandas - 1, 1)
            cor = lerp_cor(c1, c2, t)
            pygame.draw.rect(janela_surf, cor, (0, int(i * h_banda), janela_w, int(h_banda) + 1))
        pygame.draw.rect(janela_surf, hx('#ffffff'), (20, 20, 20, 8))
        pygame.draw.rect(janela_surf, hx('#ffffff'), (24, 16, 12, 8))
    tela.blit(janela_surf, (janela_x, janela_y))
    pygame.draw.rect(tela, hx('#1e110a'), (janela_x, janela_y, janela_w, janela_h), 2)
    pygame.draw.line(tela, hx('#1e110a'), (janela_x + janela_w // 2, janela_y),
                     (janela_x + janela_w // 2, janela_y + janela_h), 1)
    pygame.draw.line(tela, hx('#1e110a'), (janela_x, janela_y + janela_h // 2),
                     (janela_x + janela_w, janela_y + janela_h // 2), 1)

    pygame.draw.rect(tela, hx('#4c311f'), (10, 140, 14, 70))
    pygame.draw.rect(tela, hx('#25160d'), (10, 140, 14, 70), 2)
    pygame.draw.rect(tela, hx('#9e714b'), (10, 140, 14, 70), 1)
    pygame.draw.rect(tela, hx('#ffd15c'), (20, 175, 2, 3))
    pygame.draw.rect(tela, hx('#5c3d25'), (G.mesaX, G.mesaY, 55, 60))
    pygame.draw.rect(tela, hx('#331f11'), (G.mesaX + 2, G.mesaY + 60, 4, 30))
    pygame.draw.rect(tela, hx('#331f11'), (G.mesaX + 49, G.mesaY + 60, 4, 30))
    pygame.draw.rect(tela, hx('#382215'), (G.mesaX + 8, G.mesaY + 65, 14, 20))
    if G.quartoLuzAcesa:
        glow = pygame.Surface((40, 40), pygame.SRCALPHA)
        pygame.draw.circle(glow, (255, 220, 130, 60), (20, 20), 18)
        tela.blit(glow, (G.mesaX + 24, G.mesaY - 14))
    pygame.draw.rect(tela, hx('#caa05a'), (G.mesaX + 40, G.mesaY - 6, 6, 12))
    pygame.draw.rect(tela, hx('#ffe7a0'), (G.mesaX + 37, G.mesaY - 12, 12, 7))
    pygame.draw.rect(tela, hx('#68686d'), (G.mesaX + 15, G.mesaY + 20, 20, 4))
    if G.notebookAceso:
        pygame.draw.rect(tela, hx('#a1e4ff'), (G.mesaX + 18, G.mesaY + 6, 12, 9))
    else:
        pygame.draw.rect(tela, hx('#1e1e24'), (G.mesaX + 18, G.mesaY + 10, 15, 10))

    pygame.draw.rect(tela, hx('#6e4424'), (G.camaX, G.camaY, 60, 120))
    pygame.draw.rect(tela, hx('#e3e3f0'), (G.camaX + 2, G.camaY + 28, 56, 92))
    pygame.draw.rect(tela, hx('#cdb4e0'), (G.camaX + 2, G.camaY + 28, 56, 6))
    pygame.draw.rect(tela, hx('#ffffff'), (G.camaX + 6, G.camaY + 6, 20, 15))
    pygame.draw.rect(tela, hx('#ffffff'), (G.camaX + 34, G.camaY + 6, 20, 15))


def desenharTelaNotebook(t):
    sx, sy, sw, sh = G.mesaX + 18, G.mesaY + 6, 12, 9
    px, py, pw, ph = 64, 36, 272, 142
    x = lerp(sx, px, t)
    y = lerp(sy, py, t)
    w = lerp(sw, pw, t)
    h = lerp(sh, ph, t)
    pygame.draw.rect(tela, (18, 20, 28), (x - 4, y - 4, w + 8, h + 8))
    pygame.draw.rect(tela, (40, 44, 56), (x - 4, y - 4, w + 8, h + 8), 1)
    pygame.draw.rect(tela, (10, 12, 20), (x, y, w, h))
    pygame.draw.rect(tela, (22, 26, 40), (int(x + 3), int(y + 3), int(w - 6), int(h - 6)))
    return x, y, w, h


# ==============================================================================
# TELA DE INTRO
# ==============================================================================
def desenharTelaIntro():
    t = G.introTimer

    pulso = (math.sin(t * 0.018) + 1) / 2
    c1 = lerp_cor(hx('#140820'), hx('#200c36'), pulso)
    c2 = lerp_cor(hx('#0a1238'), hx('#162048'), pulso)
    desenharCeu(c1, c2, 0, ALTURA)

    for sx, sy, fase in G.introEstrelas:
        brilho = (math.sin(t * 0.04 + fase * 9) + 1) / 2
        a = int(brilho * 190 + 65)
        tam = 1 if brilho < 0.55 else 2
        pygame.draw.rect(tela, (a, a, min(255, a + 50)), (sx, sy, tam, tam))

    for i in range(6):
        ang = t * 0.013 + i * (math.pi * 2 / 6)
        hcx = LARGURA // 2 + int(math.cos(ang) * (55 + i * 12))
        hcy = 145 + int(math.sin(ang * 0.65) * 18)
        a_c = int((math.sin(t * 0.025 + i * 1.2) + 1) / 2 * 110 + 50)
        sz = 2 + i % 3
        hs = pygame.Surface((sz * 4, sz * 4), pygame.SRCALPHA)
        pontos = [(sz, 0), (sz*2, 0), (sz*3, sz), (sz*3, sz*2),
                  (sz*2, sz*3), (sz, sz*3), (0, sz*2), (0, sz)]
        pygame.draw.polygon(hs, (240, 80, 130, a_c), pontos)
        tela.blit(hs, (hcx - sz*2, hcy - sz*2))

    for ox, oy, cor_t in [(2, 2, hx('#500030')), (1, 1, hx('#800050')), (0, 0, hx('#ffd0e8'))]:
        texto(tela, "joguinho pro", LARGURA // 2 + ox, 55 + oy, 23, cor_t, align='center', bold=True)
    for ox, oy, cor_t in [(2, 2, hx('#500030')), (1, 1, hx('#800050')), (0, 0, hx('#ff88bb'))]:
        texto(tela, "meu amor  <3", LARGURA // 2 + ox, 82 + oy, 23, cor_t, align='center', bold=True)

    desenharMulherPixel(LARGURA // 2 - 24, 148)
    desenharHomemPixel(LARGURA // 2 + 10, 148)

    alfa_btn = int((math.sin(t * 0.07) + 1) / 2 * 160 + 95)
    cor_btn = (min(255, alfa_btn + 60), alfa_btn, min(255, alfa_btn + 90))
    texto(tela, "ENTER ou clique para começar", LARGURA // 2, 196, 11, cor_btn,
          align='center', bold=True)
    texto(tela, "feito com amor  ♥", LARGURA // 2, 215, 9, hx('#886699'), align='center')


# ==============================================================================
# CARTINHA (overlay)
# ==============================================================================
TEXTO_CARTA = [
    ("Para o meu amor <3", True, True),
    ("", False, False),
    ("Obrigada por passar esses", False, False),
    ("8 meses ao meu lado,", False, False),
    ("você é meu tudo  ♥", False, False),
    ("", False, False),
    ("Quero estar pra sempre", False, False),
    ("com você meu gatinho  ♥", False, False),
    ("", False, False),
    ("Com muito amor:", False, False),
    ("mimisf  ♥", True, True),
]


def desenharOverlayCarta():
    ov = pygame.Surface((LARGURA, ALTURA), pygame.SRCALPHA)
    ov.fill((0, 0, 0, 200))
    tela.blit(ov, (0, 0))

    cx, cy, cw, ch = 30, 20, 340, 245
    pygame.draw.rect(tela, hx('#fffdf0'), (cx, cy, cw, ch))
    pygame.draw.rect(tela, hx('#e8c88a'), (cx, cy, cw, ch), 2)
    texto(tela, "♥", LARGURA // 2, cy + 6, 14, hx('#c0305a'), align='center', bold=True)
    y_off = cy + 24
    for (linha, destaque, bold_linha) in TEXTO_CARTA:
        if linha == "":
            y_off += 8
            continue
        cor_linha = hx('#c0305a') if destaque else hx('#3a2520')
        texto(tela, linha, LARGURA // 2, y_off, 11, cor_linha, align='center', bold=bold_linha)
        y_off += 16
    bx, by, bw, bh = LARGURA // 2 - 40, cy + ch - 22, 80, 16
    pygame.draw.rect(tela, hx('#c0305a'), (bx, by, bw, bh))
    pygame.draw.rect(tela, hx('#e8a0b8'), (bx, by, bw, bh), 1)
    texto(tela, "fechar  ♥", LARGURA // 2, by + 2, 10, hx('#ffffff'), align='center', bold=True)
    G._cartaFechaBtnRect = (bx, by, bw, bh)


# ==============================================================================
# OVERLAY DE PAUSA
# ==============================================================================
def desenharOverlayPausa():
    ov = pygame.Surface((LARGURA, ALTURA), pygame.SRCALPHA)
    ov.fill((10, 8, 22, 180))
    tela.blit(ov, (0, 0))
    pw, ph = 200, 96
    px, py = (LARGURA - pw) // 2, (ALTURA - ph) // 2
    pygame.draw.rect(tela, hx('#2a1c3a'), (px, py, pw, ph))
    pygame.draw.rect(tela, hx('#caa074'), (px, py, pw, ph), 2)
    texto(tela, "PAUSA  ♥", LARGURA // 2, py + 14, 18, hx('#ff88bb'), align='center', bold=True)
    texto(tela, "P para continuar", LARGURA // 2, py + 44, 11, hx('#fcf5db'), align='center')
    texto(tela, "M muta  |  + / - volume", LARGURA // 2, py + 62, 9, hx('#c9c9d6'), align='center')
    texto(tela, "F11 tela cheia  |  R recomeça", LARGURA // 2, py + 76, 9, hx('#c9c9d6'), align='center')


# ==============================================================================
# ATUALIZAR
# ==============================================================================
def dist(ax, ay, bx, by):
    return math.hypot(ax - bx, ay - by)


def atualizar():
    global _intro_musica_on
    gerenciarTransicao()
    caixaDialogo.atualizar()
    G.tempoCeu += 1.0

    # Corações flutuantes (sempre, mesmo durante diálogo)
    for c in G.coracoes:
        c.atualizar()
    G.coracoes = [c for c in G.coracoes if c.viva()]

    if G.volumeMsgTimer > 0:
        G.volumeMsgTimer -= 1

    if caixaDialogo.ativo:
        return
    G.tempoPasso += 0.2

    # --- Tela intro ---
    if G.cenaAtual == CENA_INTRO:
        G.introTimer += 1
        if SONS_OK and not _intro_musica_on:
            SOM_INTRO.play(-1)
            _intro_musica_on = True
        return

    # Parar música intro, iniciar música de fundo (independente de SONS_OK)
    if _intro_musica_on:
        if SONS_OK:
            SOM_INTRO.stop()
        _intro_musica_on = False
    # A trilha toca só nas cenas de viagem; ao entrar em casa (cena 5) em diante, silêncio.
    if G.cenaAtual in (CENA_1_ESTRADA, CENA_2_KIKAO, CENA_3_VIAGEM, CENA_4_CHEGADA_CASA):
        iniciar_musica_fundo()  # a função já evita tocar duas vezes
    else:
        parar_musica_fundo()

    if G.cenaAtual == CENA_1_ESTRADA:
        if G.carroX >= LARGURA:
            iniciarTransicao(CENA_2_KIKAO)

    elif G.cenaAtual == CENA_2_KIKAO:
        if G.kikaoEstado == "conduzindo_para_parar":
            ccx, ccy = G.carroX + 24, G.carroY + 10
            if 85 <= ccx <= 135 and 180 <= ccy <= 202:
                G.kikaoEstado = "descendo"
                G.homemX = G.carroX + 15
                G.homemY = G.carroY - 5
                G.homemAtivo = True
                G.homemVisivel = True
                G.homemComLanche = False
                if SONS_OK:
                    SOM_DING.play()
                atualizarStatus("Cena 2: Caminha até à porta da lanchonete!")
        elif G.kikaoEstado == "descendo":
            if abs((G.homemX + 5) - 210) < 12 and (G.homemY + 25) <= 150:
                G.homemVisivel = False
                G.kikaoEstado = "comprando"
                G.dinerTimer = 0
                atualizarStatus("Cena 2: À espera do lanche...")
        elif G.kikaoEstado == "comprando":
            G.dinerTimer += 1
            if G.dinerTimer >= 100:
                G.homemVisivel = True
                G.homemComLanche = True
                G.homemX = 205
                G.homemY = 125
                G.kikaoEstado = "voltando"
                atualizarStatus("Cena 2: Lanche na mão! Volta para o carro!")
        elif G.kikaoEstado == "voltando":
            if dist(G.homemX + 5, G.homemY + 12, G.carroX + 24, G.carroY + 10) < 22:
                G.homemAtivo = False
                G.kikaoEstado = "conduzindo_para_sair"
                atualizarStatus("Cena 2: Conduz para a direita!")
        elif G.kikaoEstado == "conduzindo_para_sair":
            if G.carroX > LARGURA:
                iniciarTransicao(CENA_3_VIAGEM)

    elif G.cenaAtual == CENA_3_VIAGEM:
        # Diálogo do Lusca: exibir quando o carro entra na tela
        if not G.luscaDialogoMostrado and G.carroX >= 20:
            G.luscaDialogoMostrado = True
            caixaDialogo.iniciar("Lusca: *estrala o dedo* hmmm que catupiry bom vei!")
        if G.carroX > LARGURA:
            iniciarTransicao(CENA_4_CHEGADA_CASA)

    elif G.cenaAtual == CENA_4_CHEGADA_CASA:
        if G.kikaoEstado == "conduzindo_para_parar":
            if G.carroX >= 60:
                G.carroX = 60
                G.kikaoEstado = "casal_controlado"
                G.casalX = G.carroX + 15
                G.casalY = G.carroY - 15
                G.casalAtivo = True
                atualizarStatus("Cena 4: Leva o casal até a porta de casa!")
                if SONS_OK and not G.somChegadaTocado:
                    SOM_CHEGADA.play()
                    G.somChegadaTocado = True
        elif G.kikaoEstado == "casal_controlado":
            perto = (dist(G.casalX + 5, G.casalY + 12, G.casaX + 90, G.casaY + 80) < 130)
            for pet in listaPets:
                pet.atualizar(perto)
            if perto:
                G.coracaoTimer += 1
                if G.coracaoTimer >= 16:
                    G.coracaoTimer = 0
                    soltar_coracoes(G.casalX + 6, G.casalY - 6, 1)
            if dist(G.casalX + 5, G.casalY + 25, G.casaX + 35, G.casaY + 68) < 16:
                G.casalAtivo = False
                iniciarTransicao(CENA_5_QUARTO)

    elif G.cenaAtual == CENA_5_QUARTO:
        if G.quartoEstado == "entrando":
            if dist(G.mulherQuartoX, G.mulherQuartoY, G.camaX + 20, G.camaY + 55) < 12:
                G.quartoEstado = "dormindo"
                G.quartoTimer = 0
                atualizarStatus("Cena 5: Boa noite...")
                if SONS_OK and not G.somDingTocado:
                    SOM_DING.play()
                    G.somDingTocado = True
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
                    G.mulherQuartoX = G.camaX + 20
                    G.mulherQuartoY = G.camaY + 55
                    atualizarStatus("Cena 5: Leva a Mimi até o notebook!")
            elif G.quartoEstado == "andando":
                if dist(G.mulherQuartoX, G.mulherQuartoY, G.mesaX + 8, G.mesaY + 28) < 10:
                    G.notebookAceso = True
                    G.quartoEstado = "programando"
                    iniciarTransicao(CENA_6_PROGRAMACAO)

    elif G.cenaAtual == CENA_6_PROGRAMACAO:
        if G.notebookZoom < 1.0:
            G.notebookZoom = min(1.0, G.notebookZoom + 0.045)
        elif not G.introMostrada:
            caixaDialogo.iniciar("mimi: oi moo, fiz um vídeo pra vc <3")
            G.introMostrada = True
        G.cliqueDisponivel = (G.notebookZoom >= 1.0 and G.introMostrada and not caixaDialogo.ativo)
        G.puloCliqueNotebook += 0.12
        if G.cliqueDisponivel:
            G.coracaoTimer += 1
            if G.coracaoTimer >= 28:
                G.coracaoTimer = 0
                soltar_coracoes(random.randint(80, 320), 168, 1)


# ==============================================================================
# DESENHAR
# ==============================================================================
def desenhar():
    _fila_texto.clear()
    shakeX = shakeY = 0
    if G.colidirTimer > 35:
        shakeX = (random.random() - 0.5) * 4.5
        shakeY = (random.random() - 0.5) * 4.5

    tela.fill((0, 0, 0))

    if G.cenaAtual == CENA_INTRO:
        desenharTelaIntro()

    elif G.cenaAtual == CENA_1_ESTRADA:
        tela.fill(COR_GRAMA)
        desenharCeu(hx('#7fc1e8'), hx('#cfeaf6'), 0, 92)
        pygame.draw.circle(tela, hx('#fff4c2'), (322, 44), 16)
        pygame.draw.circle(tela, hx('#fff9d8'), (322, 44), 11)
        desenharNuvensDeriva([(60, 18, 1.0), (220, 30, 0.8), (320, 14, 1.2)])
        desenharArvores()
        desenharFlores(FLORES_CAMPO)
        desenharEstrada(165, 65, True)
        for obs in G.listaObstaculos:
            obs.desenhar()
        desenharCarroPixel(G.carroX, G.carroY)

    elif G.cenaAtual == CENA_2_KIKAO:
        tela.fill(COR_GRAMA)
        desenharCeu(hx('#7fc1e8'), hx('#cfeaf6'), 0, 70)
        desenharNuvensDeriva([(40, 12, 0.9), (300, 20, 1.0)])
        desenharArvores()
        desenharEstrada(165, 65, False)
        desenharLanchonete()
        if G.kikaoEstado == "conduzindo_para_parar":
            pygame.draw.rect(tela, hx('#ffd700'), (85, 180, 50, 22), 1)
            texto(tela, "VAGA", 110, 167, 10, hx('#ffd700'), align='center', bold=True)
        if G.kikaoEstado == "comprando":
            pygame.draw.rect(tela, hx('#1e1e24'), (190, 105, 40, 5))
            pygame.draw.rect(tela, hx('#27ae60'), (190, 105, int(40 * min(G.dinerTimer / 100, 1.0)), 5))
            pygame.draw.rect(tela, hx('#9e714b'), (190, 105, 40, 5), 1)
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
        tela.fill(hx('#6b4a52'))
        desenharCeu(hx('#e8763a'), hx('#f4c06a'), 0, 60)
        desenharCeu(hx('#f4c06a'), hx('#8a6b7a'), 60, 95)
        pygame.draw.circle(tela, hx('#ffe0a0'), (300, 62), 16)
        pygame.draw.circle(tela, hx('#ffb96b'), (300, 62), 12)
        desenharNuvensDeriva([(80, 20, 1.0), (260, 30, 0.8)], cor=(255, 210, 170))
        for bx, by in [(120, 40), (135, 36), (200, 28)]:
            pygame.draw.line(tela, hx('#3a2a30'), (bx, by), (bx + 3, by - 2), 1)
            pygame.draw.line(tela, hx('#3a2a30'), (bx + 3, by - 2), (bx + 6, by), 1)
        desenharArvores()
        desenharEstrada(165, 65, True)
        for obs in G.listaObstaculos:
            obs.desenhar()
        desenharCarroPixel(G.carroX, G.carroY)

    elif G.cenaAtual == CENA_4_CHEGADA_CASA:
        tela.fill(COR_GRAMA)
        desenharCeu(hx('#f0a25a'), hx('#f6d59a'), 0, 34)
        pygame.draw.rect(tela, hx('#6a615a'), (200, 138, 200, 54))
        for cx in range(208, LARGURA, 16):
            pygame.draw.rect(tela, hx('#534b45'), (cx, 138, 1, 54))
        desenharCerca(120)
        desenharFlores([(30, 250, hx('#e57ea0')), (90, 265, hx('#f0e36a')),
                        (150, 255, hx('#c98be0')), (60, 240, hx('#f0e36a'))])
        desenharCasa()
        desenharEstrada(180, 55, False)
        desenharCarroPixel(G.carroX, G.carroY)
        for pet in listaPets:
            pet.desenhar()
        if G.casalAtivo:
            desenharMulherPixel(G.casalX, G.casalY, True)
            desenharHomemPixel(G.casalX - 12, G.casalY + 2, True)
        desenharCoracoes()

    elif G.cenaAtual == CENA_5_QUARTO:
        desenharQuarto()
        if G.quartoEstado == "entrando":
            desenharHomemPixel(G.homemQuartoX, G.homemQuartoY, True)
            desenharMulherPixel(G.mulherQuartoX, G.mulherQuartoY, True)
        elif G.quartoEstado == "dormindo":
            desenharMulherPixel(G.camaX + 10, G.camaY + 10)
            desenharHomemPixel(G.camaX + 40, G.camaY + 10)
            pygame.draw.rect(tela, hx('#cfcfe0'), (G.camaX + 2, G.camaY + 28, 56, 92))
            pygame.draw.rect(tela, hx('#b9b9d4'), (G.camaX + 2, G.camaY + 28, 56, 4))
        else:
            desenharHomemPixel(G.camaX + 40, G.camaY + 10)
            pygame.draw.rect(tela, hx('#cfcfe0'), (G.camaX + 2, G.camaY + 28, 56, 92))
            pygame.draw.rect(tela, hx('#b9b9d4'), (G.camaX + 2, G.camaY + 28, 56, 4))
            desenharMulherPixel(G.mulherQuartoX, G.mulherQuartoY, True)
        ov = pygame.Surface((LARGURA, ALTURA), pygame.SRCALPHA)
        if not G.quartoLuzAcesa:
            ov.fill((12, 10, 24, 180))
        else:
            ov.fill((255, 215, 120, 18))
        tela.blit(ov, (0, 0))

    elif G.cenaAtual == CENA_6_PROGRAMACAO:
        desenharQuarto()
        desenharHomemPixel(G.camaX + 40, G.camaY + 10)
        pygame.draw.rect(tela, hx('#cfcfe0'), (G.camaX + 2, G.camaY + 28, 56, 92))
        desenharMulherPixel(G.mesaX + 4, G.mesaY + 28)
        ov = pygame.Surface((LARGURA, ALTURA), pygame.SRCALPHA)
        ov.fill((10, 8, 20, 120))
        tela.blit(ov, (0, 0))
        x, y, w, h = desenharTelaNotebook(G.notebookZoom)
        G.playRect = None
        G.cartaRect = None
        if G.cliqueDisponivel:
            cx = int(x + w / 2)
            cy = int(y + h / 2)

            pulso = abs(math.sin(G.puloCliqueNotebook)) * 3
            r_vid = int(16 + pulso)
            vid_cx = int(x + w * 0.30)
            vid_cy = cy

            halo = pygame.Surface((LARGURA, ALTURA), pygame.SRCALPHA)
            pygame.draw.circle(halo, (236, 96, 122, 70), (vid_cx, vid_cy), r_vid + 8)
            tela.blit(halo, (0, 0))
            pygame.draw.circle(tela, hx('#ec607a'), (vid_cx, vid_cy), r_vid)
            pygame.draw.circle(tela, hx('#ffffff'), (vid_cx, vid_cy), r_vid, 2)
            pygame.draw.polygon(tela, hx('#ffffff'),
                                [(vid_cx - 5, vid_cy - 7), (vid_cx - 5, vid_cy + 7), (vid_cx + 7, vid_cy)])
            G.playRect = (vid_cx, vid_cy, r_vid + 6)

            r_carta = int(16 + pulso)
            carta_cx = int(x + w * 0.70)
            carta_cy = cy

            halo2 = pygame.Surface((LARGURA, ALTURA), pygame.SRCALPHA)
            pygame.draw.circle(halo2, (100, 180, 255, 60), (carta_cx, carta_cy), r_carta + 8)
            tela.blit(halo2, (0, 0))
            pygame.draw.circle(tela, hx('#4a90d9'), (carta_cx, carta_cy), r_carta)
            pygame.draw.circle(tela, hx('#ffffff'), (carta_cx, carta_cy), r_carta, 2)
            ex, ey = carta_cx - 7, carta_cy - 5
            pygame.draw.rect(tela, hx('#ffffff'), (ex, ey, 14, 10), 1)
            pygame.draw.line(tela, hx('#ffffff'), (ex, ey), (carta_cx, carta_cy + 1), 1)
            pygame.draw.line(tela, hx('#ffffff'), (ex + 14, ey), (carta_cx, carta_cy + 1), 1)
            G.cartaRect = (carta_cx, carta_cy, r_carta + 6)

            cap_vid = "nosso vídeo <3" if G.videoExiste else "video (.mp4)"
            texto(tela, cap_vid, vid_cx, int(y + h) + 4, 10, hx('#ffe9c2'), align='center', bold=True)
            texto(tela, "cartinha ♥", carta_cx, int(y + h) + 4, 10, hx('#c2d8ff'), align='center', bold=True)

            if G.videoMsg:
                texto(tela, G.videoMsg, LARGURA / 2, int(y + h) + 18, 9, hx('#bfe8c2'), align='center')
            if G.cartaMsg:
                texto(tela, G.cartaMsg, LARGURA / 2, int(y + h) + 28, 9, hx('#bfe8c2'), align='center')
            texto(tela, "Pressiona R para recomeçar", LARGURA / 2, ALTURA - 14, 9,
                  hx('#c9c9d6'), align='center')

        desenharCoracoes()

        if G.mostrarCartinha:
            desenharOverlayCarta()

    # HUD
    if G.cenaAtual != CENA_INTRO and controlandoPersonagem():
        hud = pygame.Surface((212, 18), pygame.SRCALPHA)
        hud.fill((20, 20, 20, 184))
        tela.blit(hud, (8, 8))
        t_hud = "WASD/SETAS: conduz o teu carro" if podeConduzir() else "WASD/SETAS: move os personagens"
        texto(tela, t_hud, 12, 10, 10, hx('#ffffff'))

    # Mensagem de volume/mute
    if G.volumeMsgTimer > 0 and G.volumeMsg:
        vm = pygame.Surface((118, 16), pygame.SRCALPHA)
        vm.fill((20, 20, 20, 184))
        tela.blit(vm, (LARGURA - 126, 8))
        texto(tela, G.volumeMsg, LARGURA - 120, 10, 10, hx('#ffe9c2'), bold=True)

    caixaDialogo.desenhar()

    if G.pausado:
        desenharOverlayPausa()

    if G.transicaoAlfa > 0:
        fade = pygame.Surface((LARGURA, ALTURA), pygame.SRCALPHA)
        fade.fill((0, 0, 0, int(G.transicaoAlfa * 255)))
        tela.blit(fade, (0, 0))

    escalada = pygame.transform.scale(tela, (LARGURA * ESCALA, ALTURA * ESCALA))
    janela.fill((0, 0, 0))
    janela.blit(escalada, (int(shakeX * ESCALA), int(shakeY * ESCALA)))
    _render_fila_texto()


# ==============================================================================
# CONTROLES DE SOM / TELA
# ==============================================================================
def ajustar_volume(delta):
    global _volume_musica
    _volume_musica = clamp(_volume_musica + delta, 0.0, 1.0)
    if MUSICA_FUNDO_OK and not _musica_mutada:
        try:
            pygame.mixer.music.set_volume(_volume_musica)
        except Exception:
            pass
    G.volumeMsg = f"Volume: {int(_volume_musica * 100)}%"
    G.volumeMsgTimer = 90


def alternar_mute():
    global _musica_mutada
    _musica_mutada = not _musica_mutada
    if MUSICA_FUNDO_OK:
        try:
            pygame.mixer.music.set_volume(0.0 if _musica_mutada else _volume_musica)
        except Exception:
            pass
    G.volumeMsg = "Som: OFF" if _musica_mutada else "Som: ON"
    G.volumeMsgTimer = 90


def alternar_pausa():
    if G.cenaAtual == CENA_INTRO:
        return
    G.pausado = not G.pausado
    if MUSICA_FUNDO_OK and _musica_fundo_tocando:
        try:
            if G.pausado:
                pygame.mixer.music.pause()
            else:
                pygame.mixer.music.unpause()
        except Exception:
            pass


def alternar_tela_cheia():
    global janela
    G.telaCheia = not G.telaCheia
    try:
        if G.telaCheia:
            janela = pygame.display.set_mode(
                (LARGURA * ESCALA, ALTURA * ESCALA), pygame.FULLSCREEN | pygame.SCALED)
        else:
            janela = pygame.display.set_mode((LARGURA * ESCALA, ALTURA * ESCALA))
    except Exception as e:
        print(f"[Tela] Nao consegui alternar tela cheia: {e}")


# ==============================================================================
# EVENTOS
# ==============================================================================
def avancarDialogo():
    if caixaDialogo.indiceLetra >= len(caixaDialogo.textoCompleto):
        caixaDialogo.ativo = False
    else:
        caixaDialogo.indiceLetra = float(len(caixaDialogo.textoCompleto))
        caixaDialogo.textoAtual = caixaDialogo.textoCompleto


def comecarJogo():
    if SONS_OK:
        SOM_DING.play()
    iniciarTransicao(CENA_1_ESTRADA)


def tratarClique(mx_janela, my_janela):
    mouseX = mx_janela / ESCALA
    mouseY = my_janela / ESCALA

    if G.mostrarCartinha:
        btn = getattr(G, '_cartaFechaBtnRect', None)
        if btn:
            bx, by, bw, bh = btn
            if bx <= mouseX <= bx + bw and by <= mouseY <= by + bh:
                G.mostrarCartinha = False
        return

    if G.cenaAtual == CENA_INTRO:
        comecarJogo()
        return
    if caixaDialogo.ativo:
        avancarDialogo()
        return
    if G.cenaAtual == CENA_6_PROGRAMACAO and G.cliqueDisponivel:
        if G.playRect:
            cx, cy, r = G.playRect
            if dist(mouseX, mouseY, cx, cy) <= r:
                reproduzir_video()
                return
        if G.cartaRect:
            cx, cy, r = G.cartaRect
            if dist(mouseX, mouseY, cx, cy) <= r:
                abrir_cartinha()
                return


TECLA_NOME = {
    pygame.K_w: 'w', pygame.K_a: 'a', pygame.K_s: 's', pygame.K_d: 'd',
    pygame.K_UP: 'arrowup', pygame.K_DOWN: 'arrowdown',
    pygame.K_LEFT: 'arrowleft', pygame.K_RIGHT: 'arrowright',
}


def main():
    rodando = True
    while rodando:
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                rodando = False
            elif ev.type == pygame.KEYDOWN:
                nome = TECLA_NOME.get(ev.key)
                if nome:
                    teclasPressionadas[nome] = True
                if ev.key == pygame.K_ESCAPE and G.mostrarCartinha:
                    G.mostrarCartinha = False
                # Controles globais de som/tela
                if ev.key == pygame.K_m:
                    alternar_mute()
                elif ev.key in (pygame.K_PLUS, pygame.K_EQUALS, pygame.K_KP_PLUS):
                    ajustar_volume(+0.1)
                elif ev.key in (pygame.K_MINUS, pygame.K_KP_MINUS):
                    ajustar_volume(-0.1)
                elif ev.key == pygame.K_F11:
                    alternar_tela_cheia()
                elif ev.key == pygame.K_p:
                    alternar_pausa()
                if ev.key == pygame.K_RETURN:
                    if G.mostrarCartinha:
                        G.mostrarCartinha = False
                    elif G.cenaAtual == CENA_INTRO:
                        comecarJogo()
                    elif caixaDialogo.ativo:
                        avancarDialogo()
                elif ev.key == pygame.K_r:
                    if G.cenaAtual == CENA_6_PROGRAMACAO and not caixaDialogo.ativo:
                        resetarVariaveisCenas()
                        parar_musica_fundo()
                        G.cenaAtual = CENA_INTRO
                        G.introTimer = 0
            elif ev.type == pygame.KEYUP:
                nome = TECLA_NOME.get(ev.key)
                if nome:
                    teclasPressionadas[nome] = False
            elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                if G.pausado:
                    pass
                elif G.cenaAtual == CENA_INTRO:
                    tratarClique(ev.pos[0], ev.pos[1])
                elif G.mostrarCartinha:
                    tratarClique(ev.pos[0], ev.pos[1])
                elif controlandoPersonagem():
                    G.toqueDestinoX = ev.pos[0] / ESCALA
                    G.toqueDestinoY = ev.pos[1] / ESCALA
                    G.toqueAtivo = True
                else:
                    tratarClique(ev.pos[0], ev.pos[1])
            elif ev.type == pygame.MOUSEMOTION:
                if G.toqueAtivo and controlandoPersonagem():
                    G.toqueDestinoX = ev.pos[0] / ESCALA
                    G.toqueDestinoY = ev.pos[1] / ESCALA
            elif ev.type == pygame.MOUSEBUTTONUP and ev.button == 1:
                G.toqueAtivo = False

        if not G.pausado:
            atualizarMovimentoCarroJogador()
            atualizarMovimentoHomem()
            atualizarMovimentoCasalCena4()
            atualizarMovimentoQuartoEntrando()
            atualizarMovimentoMimiQuarto()
            gerenciarObstaculosEColisoes()
            atualizar()
        desenhar()
        pygame.display.flip()
        clock.tick(FPS)

    parar_musica_fundo()
    pygame.quit()


# Volume / mute globais (definidos antes do uso em runtime)
_volume_musica = 0.40
_musica_mutada = False


if __name__ == "__main__":
    main()
