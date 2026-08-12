#!/usr/bin/env python3
"""
RVC 성우 더빙 — Edge TTS (여성 베이스) → RVC 음색 변환 → MP3

표준 파이프라인:
  Edge TTS (ko-KR-SunHiNeural, -8%)
  → RVC (rmvpe, index_rate=0.75)
  → MP3 128kbps

RVC 모델 교체만으로 새 성우 음색 적용 가능.
"""
from __future__ import annotations

import argparse
import asyncio
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import soundfile as sf


def _find_repo_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent


async def tts_generate(text: str, dest: Path, voice: str, rate: str) -> float:
    """Edge TTS → WAV. Returns duration in seconds."""
    import edge_tts

    communicate = edge_tts.Communicate(text, voice, rate=rate)
    await communicate.save(str(dest))
    if dest.stat().st_size < 100:
        raise RuntimeError("Edge TTS empty output")

    data, sr = sf.read(str(dest))
    return len(data) / sr


def rvc_convert(
    src_wav: Path,
    dst_wav: Path,
    *,
    rvc_model: Path,
    rvc_index: Path | None = None,
    vec_model: Path | None = None,
    rmvpe_model: Path | None = None,
    index_rate: float = 0.75,
    f0_up_semitone: float = 0,
) -> tuple[float, float]:
    """
    RVC 음색 변환. Returns (duration_sec, elapsed_sec).
    """
    from RvcPyInfer import RvcContext, OrtProviders

    repo = _find_repo_root()
    rvc_dir = repo / "voice_models" / "rvc"

    if vec_model is None:
        vec_model = rvc_dir / "pretrained" / "vec-768-layer-12.onnx"
    if rmvpe_model is None:
        rmvpe_model = rvc_dir / "pretrained" / "RMVPE.onnx"

    if not vec_model.exists():
        raise FileNotFoundError(f"ContentVec not found: {vec_model}")
    if not rvc_model.exists():
        raise FileNotFoundError(f"RVC model not found: {rvc_model}")

    t0 = time.time()

    audio, sr = sf.read(str(src_wav))
    if audio.ndim > 1:
        audio = audio.mean(axis=1)

    ctx = RvcContext(
        providers=OrtProviders(devices=["CPU"]),
        rmvpe=rmvpe_model if rmvpe_model.exists() else None,
    )

    task = ctx.build_task(
        vec_model,
        str(rvc_model),
        sr,
        (audio.astype("float32"), sr),
        f0extract_algorithm="rmvpe" if rmvpe_model and rmvpe_model.exists() else "dio",
        f0_up_semitone=f0_up_semitone,
        index_path=str(rvc_index) if rvc_index and rvc_index.exists() else None,
        index_rate=index_rate,
    )

    results = task.run()
    if not results:
        raise RuntimeError("RVC inference returned no results")

    converted, out_sr = results[0]
    dst_wav.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(dst_wav), converted, out_sr)

    elapsed = time.time() - t0
    dur = len(converted) / out_sr
    rms = float(np.sqrt(np.mean(converted**2)))

    print(f"  RVC 변환: {dur:.1f}초 → {dst_wav.name}")
    print(f"  소요시간: {elapsed:.1f}초 (RTF {elapsed/dur:.1f})")
    print(f"  RMS: {rms:.3f} {'✅' if 0.05 < rms < 0.3 else '⚠️'}")

    return dur, elapsed


def compress_mp3(src_wav: Path, dst_mp3: Path, bitrate: str = "128k") -> Path:
    """WAV → MP3 압축."""
    dst_mp3.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "ffmpeg", "-y", "-i", str(src_wav),
            "-codec:a", "libmp3lame", "-b:a", bitrate,
            str(dst_mp3),
        ],
        capture_output=True,
        check=True,
    )
    size_kb = dst_mp3.stat().st_size / 1024
    print(f"  MP3 압축: {size_kb:.0f}KB → {dst_mp3.name}")
    return dst_mp3


async def main():
    parser = argparse.ArgumentParser(description="RVC 성우 더빙 파이프라인")
    parser.add_argument("--text", required=True, help="더빙할 텍스트")
    parser.add_argument("--name", default="dub_output", help="출력 파일명 (확장자 제외)")
    parser.add_argument("--out-dir", default="/tmp/dub", help="출력 디렉토리")
    parser.add_argument("--voice", default="ko-KR-SunHiNeural", help="Edge TTS 음성")
    parser.add_argument("--rate", default="-8%", help="Edge TTS 속도")
    parser.add_argument("--rvc-model", required=True, help="RVC .onnx 모델 경로")
    parser.add_argument("--rvc-index", default=None, help="RVC .index 경로")
    parser.add_argument("--index-rate", type=float, default=0.75, help="Feature retrieval blend")
    parser.add_argument("--f0-up", type=float, default=0, help="피치 조정 (semitones)")
    parser.add_argument("--skip-rvc", action="store_true", help="RVC 스킵 (베이스 음성만)")
    parser.add_argument("--sample-rate", type=int, default=48000, help="중간 WAV 샘플레이트")
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    name = args.name
    rvc_model = Path(args.rvc_model)
    rvc_index = Path(args.rvc_index) if args.rvc_index else None

    print("=" * 60)
    print(f"🎙️  RVC 성우 더빙: {name}")
    print(f"    베이스 음성: {args.voice} ({args.rate})")
    print(f"    RVC 모델:    {rvc_model.name}")
    if rvc_index:
        print(f"    RVC 인덱스:  {rvc_index.name}")
    print(f"    index_rate:  {args.index_rate}")
    print("=" * 60)

    total_t0 = time.time()

    # ── STEP 1: Edge TTS ─────────────────────────────────
    print("\n━━━ STEP 1: Edge TTS ━━━")
    print(f"음성: {args.voice} / 속도: {args.rate}")
    tts_wav = out_dir / f"{name}_raw.wav"
    dur = await tts_generate(args.text, tts_wav, args.voice, args.rate)
    print(f"길이: {dur:.1f}초")

    if args.skip_rvc:
        final_wav = tts_wav
    else:
        # ── STEP 2: RVC 변환 ─────────────────────────────
        print("\n━━━ STEP 2: RVC 음색 변환 ━━━")
        print(f"모델: {rvc_model.name}")
        print(f"f0method: rmvpe / index_rate: {args.index_rate}")
        rvc_wav = out_dir / f"{name}_rvc.wav"

        # 샘플레이트 맞추기 (필요시)
        if args.sample_rate != 48000:
            resampled = out_dir / f"{name}_resampled.wav"
            subprocess.run([
                "ffmpeg", "-y", "-i", str(tts_wav),
                "-ar", str(args.sample_rate), "-ac", "1",
                str(resampled),
            ], capture_output=True, check=True)
            src_wav = resampled
        else:
            src_wav = tts_wav

        rvc_convert(
            src_wav, rvc_wav,
            rvc_model=rvc_model,
            rvc_index=rvc_index,
            index_rate=args.index_rate,
            f0_up_semitone=args.f0_up,
        )
        final_wav = rvc_wav

    # ── STEP 3: MP3 압축 ─────────────────────────────────
    print("\n━━━ STEP 3: MP3 압축 ━━━")
    final_mp3 = out_dir / f"{name}.mp3"
    compress_mp3(final_wav, final_mp3, bitrate="128k")

    total_elapsed = time.time() - total_t0
    print(f"\n{'='*60}")
    print(f"✅ 완료: {final_mp3}")
    print(f"총 소요시간: {total_elapsed:.0f}초")
    print(f"{'='*60}")


if __name__ == "__main__":
    asyncio.run(main())
