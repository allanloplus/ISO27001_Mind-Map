"""組出 index.html：把控制措施對照（src/control_map.json）與旁白時間軸（narration/timing.json）嵌入 src/template.html。

    python tools/build.py                       # 產生 index.html
    python tools/build.py --fragment out.html   # 另存不含 <html>/<head> 外框的版本（Artifact 發布用）
"""
import argparse, json, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent


def body():
    m = json.loads((ROOT / "src/control_map.json").read_text(encoding="utf-8"))
    timing = json.loads((ROOT / "narration/timing.json").read_text(encoding="utf-8"))
    j = lambda o: json.dumps(o, ensure_ascii=False, separators=(",", ":"))
    return ((ROOT / "src/template.html").read_text(encoding="utf-8")
            .replace("/*CTRL*/", j(m["ctrl"])).replace("/*CAPS*/", j(m["caps"])).replace("/*TIMING*/", j(timing)))


def main(fragment):
    b = body()
    if fragment:
        pathlib.Path(fragment).write_text(b, encoding="utf-8")
    head, rest = b.split("</style>", 1)
    (ROOT / "index.html").write_text(
        '<!doctype html>\n<html lang="zh-Hant-TW">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
        + head + "</style>\n</head>\n<body>" + rest + "</body>\n</html>\n", encoding="utf-8")
    print("index.html written")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--fragment")
    main(ap.parse_args().fragment)
