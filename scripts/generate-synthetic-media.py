#!/usr/bin/env python3
"""Petites fixtures synthetiques, sans micro/camera ni capture utilisateur."""
import argparse
from array import array
import math
from pathlib import Path
import sys
import wave


def generate(directory):
    directory.mkdir(parents=True, exist_ok=True)
    video = directory / 'FourPeople_1280x720_30.y4m'
    audio = directory / 'fakeAudioStream.wav'
    if video.exists() or audio.exists():
        raise SystemExit('Fixtures presentes : refus d ecrasement.')
    width, height, frames = 1280, 720, 2
    with video.open('xb') as out:
        out.write(b'YUV4MPEG2 W1280 H720 F30:1 Ip A1:1 C420jpeg\n')
        for phase in range(frames):
            row = bytes(48 if ((x // 160) + phase) % 2 else 196 for x in range(width))
            out.write(b'FRAME\n' + row * height + bytes([96 + phase * 32]) * (width * height // 4)
                      + bytes([160 - phase * 32]) * (width * height // 4))
    samples = array('h', (int(3000 * math.sin(2 * math.pi * 440 * i / 48000)) for i in range(48000)))
    if sys.byteorder != 'little': samples.byteswap()
    with wave.open(str(audio), 'wb') as out:
        out.setnchannels(1); out.setsampwidth(2); out.setframerate(48000); out.writeframes(samples.tobytes())
    return video, audio


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    for path in generate(args.output): print(path.name, path.stat().st_size, 'bytes')
