#!/usr/bin/env python3
"""Генератор линейного набора иконок и спокойных обложек для Notion.

Линейный штрих, единый мид-тил, прозрачный фон — читается и в светлой, и в тёмной теме.
Рендер через rsvg-convert: встроенный MSVG-рендерер ImageMagick молча игнорирует stroke.
"""
import json
import pathlib
import random
import subprocess
import sys

ROOT = pathlib.Path(__file__).parent
SVG = ROOT / "assets/svg-line"
ICO = ROOT / "assets/icons-line"
COV = ROOT / "assets/covers-line"
PUB = ROOT / "publish"
for d in (SVG, ICO, COV):
    d.mkdir(parents=True, exist_ok=True)

STROKE = "#0D9488"   # мид-тил: контрастен и на белом, и на #191919
SW = 1.6

# Геометрия каждой иконки: сетка 24x24, только обводка, скруглённые концы.
GLYPHS = {
    # пульт управления: два рельса с ползунками
    "home": """
      <line x1="3" y1="8.5" x2="7" y2="8.5"/>
      <line x1="11" y1="8.5" x2="21" y2="8.5"/>
      <circle cx="9" cy="8.5" r="2"/>
      <line x1="3" y1="15.5" x2="14" y2="15.5"/>
      <line x1="18" y1="15.5" x2="21" y2="15.5"/>
      <circle cx="16" cy="15.5" r="2"/>""",
    # пазл: выступы читаются даже в сайдбаре на 20px, выемки там сливаются в квадрат
    "ext": """
      <path d="M5 6.4A1.4 1.4 0 0 1 6.4 5H9a2.4 2.4 0 0 1 4.8 0h2.8A1.4 1.4 0 0 1 18 6.4V9a2.4 2.4 0 0 0 0 4.8v3.8A1.4 1.4 0 0 1 16.6 19H6.4A1.4 1.4 0 0 1 5 17.6z"/>""",
    # щит
    "vpn": """
      <path d="M12 3.2 4.6 6.1v5.6c0 4.4 3.1 7.2 7.4 8.9 4.3-1.7 7.4-4.5 7.4-8.9V6.1z"/>""",
    # центральный узел и три агента
    "kontora": """
      <circle cx="12" cy="11.6" r="2.4"/>
      <circle cx="12" cy="4.4" r="1.7"/>
      <circle cx="5.4" cy="17.4" r="1.7"/>
      <circle cx="18.6" cy="17.4" r="1.7"/>
      <line x1="12" y1="9.2" x2="12" y2="6.1"/>
      <line x1="10.2" y1="13.1" x2="6.9" y2="15.9"/>
      <line x1="13.8" y1="13.1" x2="17.1" y2="15.9"/>""",
    # весы
    "mgua": """
      <line x1="12" y1="4.4" x2="12" y2="19.6"/>
      <line x1="8.2" y1="19.6" x2="15.8" y2="19.6"/>
      <line x1="5" y1="8" x2="19" y2="8"/>
      <line x1="5" y1="8" x2="5" y2="9.6"/>
      <line x1="19" y1="8" x2="19" y2="9.6"/>
      <path d="M2.6 9.6h4.8a2.4 2.4 0 0 1-4.8 0z"/>
      <path d="M16.6 9.6h4.8a2.4 2.4 0 0 1-4.8 0z"/>
      <circle cx="12" cy="4.4" r="1.1"/>""",
    # документ с загнутым углом
    "praktika": """
      <path d="M14 3.2H7.2a1.6 1.6 0 0 0-1.6 1.6v14.4a1.6 1.6 0 0 0 1.6 1.6h9.6a1.6 1.6 0 0 0 1.6-1.6V7.6z"/>
      <path d="M14 3.2v4.4h4.4"/>
      <line x1="8.8" y1="13" x2="15.2" y2="13"/>
      <line x1="8.8" y1="16.4" x2="12.8" y2="16.4"/>""",
    # кадр с треугольником
    "content": """
      <rect x="3" y="5" width="18" height="14" rx="2.4"/>
      <path d="M10.6 9.4 15.4 12l-4.8 2.6z"/>""",
    # перекрестие
    "cs2": """
      <circle cx="12" cy="12" r="7.4"/>
      <line x1="12" y1="2.4" x2="12" y2="5.8"/>
      <line x1="12" y1="18.2" x2="12" y2="21.6"/>
      <line x1="2.4" y1="12" x2="5.8" y2="12"/>
      <line x1="18.2" y1="12" x2="21.6" y2="12"/>
      <circle cx="12" cy="12" r="1.15" fill="%s" stroke="none"/>""" % STROKE,
}

# Обложки: два близких тона одного семейства, приглушённые и светлые.
COVERS = {
    "home":     ("#E8F4F1", "#BCDFD8"),
    "ext":      ("#EBEEF9", "#C6D1EB"),
    "vpn":      ("#E9EFF4", "#C5D5E1"),
    "kontora":  ("#F0ECF7", "#D3C8E5"),
    "mgua":     ("#F7F1E5", "#E7D7BA"),
    "praktika": ("#F3F1ED", "#DCD7CE"),
    "content":  ("#F9EEF1", "#ECCCD5"),
    "cs2":      ("#E9F5EE", "#C5E2D1"),
}

TPL = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24">
  <g fill="none" stroke="{stroke}" stroke-width="{sw}" stroke-linecap="round" stroke-linejoin="round">
{body}
  </g>
</svg>
"""


def run(cmd):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if r.returncode != 0:
        print(f"  ОШИБКА: {cmd}\n  {r.stderr.strip()[:300]}", file=sys.stderr)
        return False
    return True


def main():
    if not subprocess.run("command -v rsvg-convert", shell=True,
                          capture_output=True).returncode == 0:
        print("rsvg-convert не найден — без него stroke не отрендерится. Прерываю.")
        sys.exit(1)

    made = {}
    print("=== иконки ===")
    for name, body in GLYPHS.items():
        svg = SVG / f"{name}.svg"
        svg.write_text(TPL.format(stroke=STROKE, sw=SW, body=body))
        png = ICO / f"{name}.png"
        # 512px: Notion масштабирует иконку и в сайдбаре, и в шапке страницы
        if run(f"rsvg-convert -w 512 -h 512 -o '{png}' '{svg}'"):
            size = png.stat().st_size
            # пустой рендер (проигнорированный stroke) весит ~300-400 байт
            flag = "  ПОДОЗРИТЕЛЬНО ПУСТАЯ" if size < 1200 else ""
            print(f"  {name:9} {size:>7} байт{flag}")
            made[f"icons/{name}.png"] = png

    print("=== обложки ===")
    for name, (a, b) in COVERS.items():
        png = COV / f"{name}.png"
        if run(f"magick -size 1500x400 -define gradient:angle=100 "
               f"gradient:'{a}-{b}' -strip '{png}'"):
            print(f"  {name:9} {png.stat().st_size:>7} байт")
            made[f"covers/{name}.png"] = png

    # Публикуем под случайными числовыми именами: в публичном репо
    # ничего не должно выдавать, что это за проекты.
    fm_path = ROOT / "filemap.json"
    filemap = json.loads(fm_path.read_text()) if fm_path.exists() else {}
    used = set(filemap.values())
    print("=== публикация ===")
    for key, src in made.items():
        while True:
            rnd = f"{random.randint(10_000_000, 99_999_999)}.png"
            if rnd not in used:
                break
        used.add(rnd)
        filemap[key] = rnd
        (PUB / rnd).write_bytes(src.read_bytes())
        print(f"  {key:22} -> {rnd}")

    fm_path.write_text(json.dumps(filemap, indent=1, ensure_ascii=False))
    print(f"\nfilemap.json обновлён, записей: {len(filemap)}")


if __name__ == "__main__":
    main()
