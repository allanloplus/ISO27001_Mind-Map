"""產生雙人旁白：羅宇倫 Allan 老師（台灣口音男聲）＋助教阿拉蕾（活潑女聲）。

預設使用 Microsoft Edge 線上神經語音（台灣國語，需可連線 speech.platform.bing.com）：
    pip install edge-tts soundfile imageio-ffmpeg
    python tools/tts.py

離線備案（Kokoro v1.1-zh，口音偏大陸普通話）：
    pip install sherpa-onnx soundfile opencc-python-reimplemented imageio-ffmpeg
    下載並解壓 https://github.com/k2-fsa/sherpa-onnx/releases/download/tts-models/kokoro-multi-lang-v1_1.tar.bz2
    python tools/tts.py --engine kokoro --model-dir kokoro-multi-lang-v1_1

輸出：assets/narration.mp3（完整旁白）、narration/timing.json（每段長度與每句起訖時間）
"""
import argparse, asyncio, json, pathlib, re, subprocess
import numpy as np, soundfile as sf, imageio_ffmpeg

ROOT = pathlib.Path(__file__).resolve().parent.parent
FF = imageio_ffmpeg.get_ffmpeg_exe()
SR = 24000
# A = Allan 老師、R = 阿拉蕾
EDGE = {"A": dict(voice="zh-TW-YunJheNeural", rate="+6%", pitch="+3Hz"),
        "R": dict(voice="zh-TW-HsiaoYuNeural", rate="+14%", pitch="+40Hz")}
KOKORO = {"A": dict(sid=68, speed=1.08), "R": dict(sid=39, speed=1.15)}
LEAD, GAP, TAIL, FIRST_LEAD, MIN_SCENE = 0.5, 0.3, 0.6, 1.0, 5.0
DIGITS = "零一二三四五六七八九"
SAY = [(r"ISO 2700(\d)", lambda m: "ISO 二七零零" + DIGITS[int(m[1])]),
       (r"A\.(\d)", lambda m: "A " + DIGITS[int(m[1])]),
       (r"〇", "零"), (r"～", "")]


def say(text):
    for pat, rep in SAY:
        text = re.sub(pat, rep, text)
    return text


def decode(mp3: bytes):
    p = subprocess.run([FF, "-loglevel", "error", "-i", "pipe:0", "-f", "f32le", "-ac", "1", "-ar", str(SR), "pipe:1"],
                       input=mp3, capture_output=True, check=True)
    return np.frombuffer(p.stdout, dtype=np.float32)


def edge_engine():
    import edge_tts

    async def run(text, o):
        buf = bytearray()
        async for c in edge_tts.Communicate(text, o["voice"], rate=o["rate"], pitch=o["pitch"]).stream():
            if c["type"] == "audio":
                buf += c["data"]
        return bytes(buf)

    return lambda who, text: decode(asyncio.run(run(say(text), EDGE[who])))


def kokoro_engine(d):
    import opencc, sherpa_onnx
    d = str(d).rstrip("/") + "/"
    tts = sherpa_onnx.OfflineTts(sherpa_onnx.OfflineTtsConfig(
        model=sherpa_onnx.OfflineTtsModelConfig(kokoro=sherpa_onnx.OfflineTtsKokoroModelConfig(
            model=d + "model.onnx", voices=d + "voices.bin", tokens=d + "tokens.txt",
            data_dir=d + "espeak-ng-data", dict_dir=d + "dict",
            lexicon=d + "lexicon-us-en.txt," + d + "lexicon-zh.txt"), num_threads=4),
        rule_fsts=d + "date-zh.fst," + d + "phone-zh.fst," + d + "number-zh.fst"))
    cc = opencc.OpenCC("t2s")
    fix = lambda t: cc.convert(say(t).replace("ISO", "I S O").replace("著", "着"))
    return lambda who, text: np.array(tts.generate(fix(text), **KOKORO[who]).samples, dtype=np.float32)


def trim(x, thr=0.01):
    idx = np.where(np.abs(x) > thr)[0]
    return x[max(0, idx[0] - 240): idx[-1] + 2400] if len(idx) else x


def main(engine, model_dir):
    speak = kokoro_engine(model_dir) if engine == "kokoro" else edge_engine()
    scenes = json.loads((ROOT / "narration/lines.json").read_text(encoding="utf-8"))
    track, timing, t = [], [], 0.0
    for k, lines in enumerate(scenes):
        pos = FIRST_LEAD if k == 0 else LEAD
        out = []
        for who, text in lines:
            x = trim(speak(who, text))
            out.append(dict(who=who, text=text, start=round(pos, 2), end=round(pos + len(x) / SR, 2)))
            track.append((t + pos, x))
            pos += len(x) / SR + GAP
        dur = round(max(MIN_SCENE, pos - GAP + TAIL), 2)
        timing.append(dict(dur=dur, lines=out))
        t += dur
        print(f"{k + 1:02}  {dur:5.1f}s")
    audio = np.zeros(int((t + 1) * SR), dtype=np.float32)
    for start, x in track:
        i = int(start * SR)
        audio[i:i + len(x)] += x
    audio *= 0.95 / max(1e-6, np.abs(audio).max())
    wav = ROOT / "narration/narration.wav"
    sf.write(wav, audio, SR)
    subprocess.run([FF, "-y", "-loglevel", "error", "-i", str(wav), "-ac", "1", "-b:a", "64k",
                    str(ROOT / "assets/narration.mp3")], check=True)
    wav.unlink()
    (ROOT / "narration/timing.json").write_text(json.dumps(timing, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"total {t:.1f}s")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--engine", choices=["edge", "kokoro"], default="edge")
    ap.add_argument("--model-dir", help="Kokoro 模型目錄（--engine kokoro 時需要）")
    a = ap.parse_args()
    main(a.engine, a.model_dir)
