"""由旁白音量算出 Allan 老師的嘴型（口型同步）：每 0.06 秒一格，0=閉嘴、1=微開、2=張開。

    python tools/mouth.py      # 讀 assets/narration.mp3，寫入 narration/mouth.txt

產生旁白（tools/tts.py）後執行，再執行 tools/build.py。
"""
import pathlib, subprocess
import numpy as np, imageio_ffmpeg

ROOT = pathlib.Path(__file__).resolve().parent.parent
STEP, SR = 0.06, 16000


def main():
    raw = subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-loglevel", "error", "-i", str(ROOT / "assets/narration.mp3"),
                          "-f", "f32le", "-ac", "1", "-ar", str(SR), "pipe:1"], capture_output=True, check=True).stdout
    x = np.frombuffer(raw, dtype=np.float32)
    n = int(STEP * SR)
    rms = np.array([np.sqrt(np.mean(x[i:i + n] ** 2)) for i in range(0, len(x) - n, n)])
    ref = np.percentile(rms[rms > 1e-3], 90)
    lv = np.where(rms < 0.22 * ref, 0, np.where(rms < 0.55 * ref, 1, 2))
    # hold an open mouth for at least two steps so it does not flicker
    for i in range(1, len(lv) - 1):
        if lv[i] == 0 and lv[i - 1] > 0 and lv[i + 1] > 0:
            lv[i] = 1
    (ROOT / "narration/mouth.txt").write_text("".join(map(str, lv)) + "\n", encoding="utf-8")
    print(f"{len(lv)} steps, open {np.mean(lv > 0):.0%}")


if __name__ == "__main__":
    main()
