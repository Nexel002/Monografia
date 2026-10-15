"""Vídeos da visão computacional: tudo o que o backend lê é WebM, numa pasta própria.

Os vídeos chegam em qualquer formato (mp4, mov, avi, ...) para `dados/videos/`. Antes de serem lidos, são
convertidos para WebM (VP9, sem áudio, no máximo 960 px de largura) em `dados/videos_webm/`; a análise, o modo
ao vivo e a API só usam essa pasta. Reduz o peso em disco e na rede, e dá um formato único ao resto do código.

Largura máxima de 960 px: o YOLO trabalha a 480-960 px e o modo ao vivo já reduz para 960 px (LARGURA_DE_TRABALHO),
por isso a análise não perde informação que alguma vez usasse. O fps e o número de fotogramas mantêm-se, porque
os tempos da contagem por janelas e a sincronização com o browser dependem deles.

O ffmpeg vem no pacote `imageio-ffmpeg`, sem instalar nada no sistema. Também converte o vídeo anotado para H.264,
que o OpenCV não sabe escrever (ver `converter_para_h264`).

Uso (a partir de backend/):
    uv run python -m gestao_trafego.visao.video --converter-tudo     # converte tudo o que está em dados/videos/
    uv run python -m gestao_trafego.visao.video caminho/do/video.mov  # converte um vídeo
"""

import argparse
import subprocess
from pathlib import Path

import cv2
import imageio_ffmpeg

from gestao_trafego.comum.configuracao import RAIZ

PASTA_ORIGINAIS = RAIZ / "dados" / "videos"
PASTA_WEBM = RAIZ / "dados" / "videos_webm"
LARGURA_MAXIMA = 960
EXTENSOES_DE_VIDEO = {".mp4", ".mov", ".avi", ".mkv", ".m4v", ".wmv", ".flv", ".mpg", ".mpeg", ".ts", ".3gp", ".webm"}


def _executar_ffmpeg(argumentos: list[str], nome: str) -> None:
    resultado = subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-loglevel", "error", *argumentos], capture_output=True, text=True)
    if resultado.returncode != 0:
        raise RuntimeError(f"O ffmpeg falhou ao converter {nome}: {resultado.stderr.strip()}")


def converter_para_h264(entrada: Path, saida: Path) -> Path:
    if entrada.resolve() == saida.resolve():
        raise ValueError("A saída tem de ser diferente da entrada.")
    _executar_ffmpeg([
        "-i", str(entrada), "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
        # yuv420p: sem isto alguns browsers não reproduzem; faststart: o vídeo arranca sem descarregar tudo
        "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-an", str(saida),
    ], entrada.name)
    return saida


def _fotogramas(caminho: Path) -> int:
    captura = cv2.VideoCapture(str(caminho))
    try:
        if not captura.isOpened():
            raise RuntimeError(f"O OpenCV não consegue abrir {caminho.name}.")
        return int(captura.get(cv2.CAP_PROP_FRAME_COUNT))
    finally:
        captura.release()


def _debito_maximo_kbps(origem: Path) -> int:
    """80 % do débito do vídeo de origem. Medido em 15/10/2026: um MP4 de 640x360 já muito comprimido (62 MB)
    crescia para 100 MB em VP9 com qualidade constante (crf), porque o crf mantém a qualidade e não o tamanho.
    Com este tecto o WebM nunca fica mais pesado do que o original, que é o objectivo da conversão."""
    captura = cv2.VideoCapture(str(origem))
    fps = captura.get(cv2.CAP_PROP_FPS) or 30.0
    fotogramas = captura.get(cv2.CAP_PROP_FRAME_COUNT)
    captura.release()
    if fotogramas <= 0:
        return 2000
    return max(200, int(0.8 * origem.stat().st_size * 8 / 1000 / (fotogramas / fps)))


def garantir_webm(origem: Path, pasta_destino: Path = PASTA_WEBM) -> Path:
    """Devolve o caminho do WebM de `origem` em `pasta_destino`, convertendo-o se ainda não existir (ou se a
    origem for mais recente). Um vídeo que já é WebM e já está na pasta devolve-se tal como está.

    A conversão escreve para um ficheiro temporário e só no fim o renomeia: uma conversão interrompida
    (PC lento, janela fechada) nunca deixa um WebM truncado que a cache daria por bom.
    """
    origem = Path(origem)
    if not origem.is_file():
        raise FileNotFoundError(f"Não existe o vídeo: {origem}")
    pasta_destino.mkdir(parents=True, exist_ok=True)
    destino = pasta_destino / f"{origem.stem}.webm"
    if destino.resolve() == origem.resolve():
        return destino
    if destino.is_file() and destino.stat().st_mtime >= origem.stat().st_mtime:
        return destino

    debito = _debito_maximo_kbps(origem)
    temporario = destino.with_name(destino.stem + ".parcial.webm")
    try:
        _executar_ffmpeg([
            "-i", str(origem),
            # min(960, iw): nunca ampliar; -2: altura par, que o codec exige
            "-vf", f"scale='min({LARGURA_MAXIMA},iw)':-2",
            "-fps_mode", "passthrough",  # sem duplicar nem largar fotogramas
            "-c:v", "libvpx-vp9", "-crf", "34", "-b:v", f"{debito}k", "-row-mt", "1", "-deadline", "good", "-cpu-used", "5",
            "-an", str(temporario),
        ], origem.name)
        _fotogramas(temporario)  # falha alto se o resultado não abrir
        temporario.replace(destino)
    finally:
        temporario.unlink(missing_ok=True)
    return destino


def exigir_webm(video: Path) -> Path:
    """Garante que quem lê o vídeo recebeu um WebM; a conversão faz-se à entrada (`garantir_webm`), não aqui."""
    if Path(video).suffix.lower() != ".webm":
        raise ValueError(f"O backend só lê WebM; converta {Path(video).name} primeiro com garantir_webm().")
    return Path(video)


def listar_originais() -> list[Path]:
    return sorted(f for f in PASTA_ORIGINAIS.glob("*") if f.suffix.lower() in EXTENSOES_DE_VIDEO)


def converter_tudo() -> list[Path]:
    """Converte todos os vídeos de `dados/videos/` que ainda não têm WebM actual."""
    convertidos = []
    for origem in listar_originais():
        t_antes = (PASTA_WEBM / f"{origem.stem}.webm")
        ja_existia = t_antes.is_file() and t_antes.stat().st_mtime >= origem.stat().st_mtime
        destino = garantir_webm(origem)
        estado = "já estava convertido" if ja_existia else "convertido"
        print(f"{origem.name}: {estado} -> {destino.name} | {origem.stat().st_size / 1e6:.1f} MB -> {destino.stat().st_size / 1e6:.1f} MB "
              f"| fotogramas {_fotogramas(origem)} -> {_fotogramas(destino)}", flush=True)
        convertidos.append(destino)
    if not convertidos:
        print(f"Não há vídeos em {PASTA_ORIGINAIS}.")
    return convertidos


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("video", nargs="?", type=Path, help="um vídeo a converter")
    parser.add_argument("--converter-tudo", action="store_true", help="converte tudo o que está em dados/videos/")
    argumentos = parser.parse_args()
    if argumentos.converter_tudo:
        converter_tudo()
    elif argumentos.video:
        print(garantir_webm(argumentos.video))
    else:
        parser.error("indique um vídeo ou --converter-tudo")
