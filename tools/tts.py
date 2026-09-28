"""產生雙人旁白：羅宇倫 Allan Lo 顧問（成熟男聲）＋助教阿拉蕾（可愛女聲）。

離線語音合成：sherpa-onnx + Kokoro v1.1-zh（kokoro-multi-lang-v1_1）
    pip install sherpa-onnx soundfile opencc-python-reimplemented imageio-ffmpeg
    下載並解壓 https://github.com/k2-fsa/sherpa-onnx/releases/download/tts-models/kokoro-multi-lang-v1_1.tar.bz2
    python tools/tts.py --model-dir <kokoro-multi-lang-v1_1 目錄>

輸出：assets/narration.mp3（完整旁白）、narration/timing.json（每段長度與每句起訖時間）
"""
import argparse, json, pathlib, re, subprocess
import numpy as np, soundfile as sf, opencc, sherpa_onnx, imageio_ffmpeg

ROOT = pathlib.Path(__file__).resolve().parent.parent
VOICE = {"A": dict(sid=68, speed=1.08), "R": dict(sid=39, speed=1.15)}  # A=Allan 顧問、R=阿拉蕾
LEAD, GAP, TAIL, FIRST_LEAD, MIN_SCENE = 0.5, 0.3, 0.6, 1.0, 5.0
SAY = [(r"ISO 2700(\d)", lambda m: "I S O 二七零零" + "零一二三四五六七八九"[int(m[1])]),
       (r"A\.(\d)", lambda m: "A " + "零一二三四五六七八九"[int(m[1])]),
       (r"〇", "零"), (r"～", ""), (r"著", "着")]
cc = opencc.OpenCC("t2s")


def say(text):
    for pat, rep in SAY:
        text = re.sub(pat, rep, text)
    return cc.convert(text)


def engine(d):
    d = str(d).rstrip("/") + "/"
    return sherpa_onnx.OfflineTts(sherpa_onnx.OfflineTtsConfig(
        model=sherpa_onnx.OfflineTtsModelConfig(kokoro=sherpa_onnx.OfflineTtsKokoroModelConfig(
            model=d + "model.onnx", voices=d + "voices.bin", tokens=d + "tokens.txt",
            data_dir=d + "espeak-ng-data", dict_dir=d + "dict",
            lexicon=d + "lexicon-us-en.txt," + d + "lexicon-zh.txt"), num_threads=4),
        rule_fsts=d + "date-zh.fst," + d + "phone-zh.fst," + d + "number-zh.fst"))


def trim(x, thr=0.01):
    idx = np.where(np.abs(x) > thr)[0]
    return x[max(0, idx[0] - 240): idx[-1] + 2400] if len(idx) else x


def main(model_dir):
    tts = engine(model_dir)
    scenes = json.loads((ROOT / "narration/lines.json").read_text(encoding="utf-8"))
    sr = tts.sample_rate
    track, timing, t = [], [], 0.0
    for k, lines in enumerate(scenes):
        pos = FIRST_LEAD if k == 0 else LEAD
        out = []
        for who, text in lines:
            a = tts.generate(say(text), **VOICE[who])
            x = trim(np.array(a.samples, dtype=np.float32))
            out.append(dict(who=who, text=text, start=round(pos, 2), end=round(pos + len(x) / sr, 2)))
            track.append((t + pos, x))
            pos += len(x) / sr + GAP
        dur = round(max(MIN_SCENE, pos - GAP + TAIL), 2)
        timing.append(dict(dur=dur, lines=out))
        t += dur
        print(f"{k + 1:02}  {dur:5.1f}s")
    audio = np.zeros(int((t + 1) * sr), dtype=np.float32)
    for start, x in track:
        i = int(start * sr)
        audio[i:i + len(x)] += x
    audio *= 0.95 / max(1e-6, np.abs(audio).max())
    wav = ROOT / "narration/narration.wav"
    sf.write(wav, audio, sr)
    subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-loglevel", "error", "-i", str(wav),
                    "-ac", "1", "-b:a", "64k", str(ROOT / "assets/narration.mp3")], check=True)
    wav.unlink()
    (ROOT / "narration/timing.json").write_text(json.dumps(timing, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"total {t:.1f}s")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--model-dir", required=True)
    main(ap.parse_args().model_dir)
