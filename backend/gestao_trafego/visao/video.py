"""Conversão do vídeo anotado para H.264, o formato que os browsers sabem reproduzir.

O OpenCV escreve MPEG-4 parte 2 (`mp4v`), que o Chrome e o Edge não reproduzem: o dashboard mostrava o
leitor de vídeo vazio. O H.264 do OpenCV exigiria uma DLL à parte; usa-se o ffmpeg que vem no pacote
`imageio-ffmpeg`, sem instalar nada no sistema.

Uso para converter um vídeo já existente (a partir de backend/):
    uv run python -m gestao_trafego.visao.video entrada.mp4 [saida.mp4]
"""

import subprocess
import sys
from pathlib import Path

import imageio_ffmpeg


def converter_para_h264(entrada: Path, saida: Path) -> Path:
    if entrada.resolve() == saida.resolve():
        raise ValueError("A saída tem de ser diferente da entrada.")
    comando = [
        imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-loglevel", "error", "-i", str(entrada),
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
        # yuv420p: sem isto alguns browsers não reproduzem; faststart: o vídeo arranca sem descarregar tudo
        "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-an", str(saida),
    ]
    resultado = subprocess.run(comando, capture_output=True, text=True)
    if resultado.returncode != 0:
        raise RuntimeError(f"O ffmpeg falhou ao converter {entrada.name}: {resultado.stderr.strip()}")
    return saida


if __name__ == "__main__":
    origem = Path(sys.argv[1])
    destino = Path(sys.argv[2]) if len(sys.argv) > 2 else origem.with_name(origem.stem + "_h264.mp4")
    print(converter_para_h264(origem, destino))
