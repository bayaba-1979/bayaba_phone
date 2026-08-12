#!/usr/bin/env python3
"""
RVC voice conversion pipeline — TTS → RVC timbre swap.
Powered by RvcPyInfer (onnxruntime + pyworld, no PyTorch).

Source priority for RVC (best Korean quality first):
  1. Edge TTS (InJoonNeural) → RVC  ← best quality, needs internet
  2. Kokoro TTS (jf_alpha) → RVC    ← offline, Japanese accent preserved

RVC preserves pronunciation/intonation, so source TTS quality = output quality.

필요한 파일 (voice_models/rvc/):
  pretrained/vec-768-layer-12.onnx  — ContentVec (download once)
  pretrained/rmvpe.onnx              — RMVPE pitch (optional, dio works without)
  parksy.onnx                        — RVC voice model (user provides)

사용법:
  python3 -m director.rvc_infer check            # 상태 진단
  python3 -m director.rvc_infer convert in.wav out.wav  # 변환
"""

from __future__ import annotations

import asyncio
import os
import sys
import tempfile
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_REPO_ROOT = _HERE.parent
_RVC_DIR = _REPO_ROOT / "voice_models" / "rvc"
_DEFAULT_VEC = _RVC_DIR / "pretrained" / "vec-768-layer-12.onnx"
_DEFAULT_RMVPE = _RVC_DIR / "pretrained" / "rmvpe.onnx"
_DEFAULT_RVC = _RVC_DIR / "parksy.onnx"

# ── lazy imports ──────────────────────────────────────────────────────

def _get_context():
    from RvcPyInfer import RvcContext, OrtProviders
    rmvpe_path = _DEFAULT_RMVPE if _DEFAULT_RMVPE.exists() else None
    return RvcContext(providers=OrtProviders(devices=["CPU"]), rmvpe=rmvpe_path)


# ── RVC 변환 코어 ─────────────────────────────────────────────────────

def rvc_convert(
    src_wav: str | Path,
    dst_wav: str | Path,
    *,
    model_path: str | Path | None = None,
    vec_path: str | Path | None = None,
    rmvpe_path: str | Path | None = None,
    f0_up_semitone: float = 0,
    f0_algorithm: str = "dio",
) -> Path:
    """RVC 음성 변환 — source WAV → target voice WAV.

    Returns: 출력 파일 경로
    """
    import time
    import soundfile as sf

    t0 = time.time()
    src, dst = Path(src_wav), Path(dst_wav)
    dst.parent.mkdir(parents=True, exist_ok=True)

    vec = Path(vec_path or _DEFAULT_VEC)
    rvc = Path(model_path or _DEFAULT_RVC)
    rmvpe = Path(rmvpe_path or _DEFAULT_RMVPE) if f0_algorithm == "rmvpe" else None

    if not vec.exists():
        raise FileNotFoundError(f"ContentVec not found: {vec}")
    if not rvc.exists():
        raise FileNotFoundError(f"RVC model not found: {rvc}")

    ctx = _get_context()

    audio, sr = sf.read(str(src))
    if audio.ndim > 1:
        audio = audio.mean(axis=1)

    # index_rate → RvcPyInfer param
    task = ctx.build_task(
        vec, str(rvc), sr,
        (audio.astype("float32"), sr),
        f0extract_algorithm=f0_algorithm,
        f0_up_semitone=f0_up_semitone,
        index_path=str(Path.home() / "rvc_models" / "parksy_rvc" / "parksy_rvc.index"),
        index_rate=0.75,
    )

    if task is None:
        raise RuntimeError("RVC task build returned None")

    results = task.run()
    if not results:
        raise RuntimeError("RVC inference returned no results")
    converted, out_sr = results[0]
    sf.write(str(dst), converted, out_sr)

    elapsed = time.time() - t0
    dur = len(converted) / out_sr
    print(f"  rvc: {dur:.1f}s → {dst.name} ({elapsed:.1f}s, RTF {elapsed/dur:.1f})", flush=True)
    return dst


# ── Source TTS providers ──────────────────────────────────────────────

async def _tts_edge_to_wav(text: str, dest: Path, voice: str = "ko-KR-SunHiNeural") -> float:
    """Edge TTS → WAV (여성 베이스 — 누나 RVC 적용 전 기본)."""
    import edge_tts

    communicate = edge_tts.Communicate(text, voice, rate="-8%")
    await communicate.save(str(dest))
    if dest.stat().st_size < 100:
        raise RuntimeError("Edge TTS empty output")
    from director.voice_engine import ffprobe_duration
    return ffprobe_duration(dest)


def _kokoro_to_wav(text: str, dest: Path, speaker_id: int = 37, speed: float = 0.95) -> float:
    """Kokoro TTS → WAV (offline fallback)."""
    import sherpa_onnx
    import soundfile as sf

    model_file = _find_kokoro_model()
    if model_file is None:
        raise RuntimeError("No Kokoro model found")

    tokens_file = model_file.parent / "tokens.txt"
    voices_file = model_file.parent / "voices.bin"
    dict_dir = model_file.parent / "dict"
    tts_lang = os.environ.get("SHERPA_LANG", "ko")

    tts_config = sherpa_onnx.OfflineTtsConfig(
        model=sherpa_onnx.OfflineTtsModelConfig(
            kokoro=sherpa_onnx.OfflineTtsKokoroModelConfig(
                model=str(model_file),
                voices=str(voices_file) if voices_file.exists() else "",
                tokens=str(tokens_file),
                data_dir=str(model_file.parent),
                dict_dir=str(dict_dir) if dict_dir.is_dir() else "",
                lang=tts_lang,
            ),
            num_threads=4,
            provider="cpu",
        ),
    )
    tts = sherpa_onnx.OfflineTts(tts_config)
    audio = tts.generate(text, sid=speaker_id, speed=speed)
    sf.write(str(dest), audio.samples, audio.sample_rate)
    return len(audio.samples) / audio.sample_rate


# ── 메인 파이프라인: TTS → RVC ────────────────────────────────────────

def tts_to_rvc(
    text: str,
    dest: Path,
    *,
    rvc_model: str | Path | None = None,
    source: str = "edge",
    edge_voice: str = "ko-KR-SunHiNeural",
    speaker_id: int = 37,
    speed: float = 0.95,
) -> tuple[float, str]:
    """TTS + RVC voice conversion end-to-end.

    source: "edge" (best Korean, needs internet) | "kokoro" (offline)

    Returns (duration_sec, provider_id).
    """
    import soundfile as sf

    tts_wav = Path(tempfile.mktemp(suffix=".wav", prefix="tts_"))
    try:
        # Stage 1: TTS → WAV
        if source == "edge":
            dur = asyncio.run(_tts_edge_to_wav(text, tts_wav, voice=edge_voice))
            prov = f"edge+{edge_voice}+rvc"
        elif source == "kokoro":
            dur = _kokoro_to_wav(text, tts_wav, speaker_id=speaker_id, speed=speed)
            prov = "kokoro+rvc"
        else:
            raise ValueError(f"Unknown source: {source}")

        # Stage 2: RVC voice conversion
        converted = rvc_convert(tts_wav, dest, model_path=rvc_model)

        data, sr2 = sf.read(str(converted))
        return len(data) / sr2, f"local/{prov}"

    finally:
        tts_wav.unlink(missing_ok=True)


# ── Helpers ───────────────────────────────────────────────────────────

def _find_kokoro_model() -> Path | None:
    for d in [
        _REPO_ROOT / "voice_models" / "kokoro-fp32-v1_0",
        _REPO_ROOT / "kokoro-multi-lang-v1_0",
        Path("/root/work/voice_models/kokoro-fp32-v1_0"),
        Path("/root/work/kokoro-multi-lang-v1_0"),
    ]:
        onnx = d / "model.onnx"
        if onnx.exists():
            return onnx
    return None


def check_rvc_ready() -> dict:
    status = {
        "kokoro_model": _find_kokoro_model() is not None,
        "edge_tts": True,  # edge-tts 7.2.8 installed
        "contentvec_model": _DEFAULT_VEC.exists(),
        "rmvpe_model": _DEFAULT_RMVPE.exists(),
        "rvc_model": _DEFAULT_RVC.exists(),
        "pyworld": True,
        "rvcpyinfer": True,
    }
    status["ready"] = status["contentvec_model"] and status["rvc_model"]
    status["missing"] = [k for k, v in status.items() if not v and k != "ready"]
    return status


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 -m director.rvc_infer check|test")
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "check":
        import json
        print(json.dumps(check_rvc_ready(), indent=2, ensure_ascii=False))
    elif cmd == "test":
        text = sys.argv[2] if len(sys.argv) > 2 else "안녕 헬레나, 오늘은 전자가 진짜 일하는 날이야"
        dest = Path(sys.argv[3]) if len(sys.argv) > 3 else Path("/tmp/rvc_test.wav")
        # test with Edge TTS source (best quality)
        dur, prov = tts_to_rvc(text, dest, source="edge")
        print(f"✅ {prov}: {dur:.1f}s → {dest}")
    else:
        sys.exit(f"Unknown: {cmd}")
