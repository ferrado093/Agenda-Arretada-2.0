"""Gera os ícones do app Android a partir de assets/icone.png (1024x1024, PNG).
Roda no GitHub depois de 'npx cap add android'."""
import os
from PIL import Image, ImageDraw

RES = os.environ.get("RES_DIR", "android/app/src/main/res")
img = Image.open("assets/icone.png").convert("RGBA")
bg = img.getpixel((4, 4))[:3]
DENS = {"mdpi": 1, "hdpi": 1.5, "xhdpi": 2, "xxhdpi": 3, "xxxhdpi": 4}

for nome, f in DENS.items():
    pasta = f"{RES}/mipmap-{nome}"
    os.makedirs(pasta, exist_ok=True)
    s = int(48 * f)
    base = img.resize((s, s), Image.LANCZOS)
    for arq, forma in (("ic_launcher.png", "quadrado"), ("ic_launcher_round.png", "redondo")):
        m = Image.new("L", (s, s), 0)
        dr = ImageDraw.Draw(m)
        if forma == "redondo":
            dr.ellipse((0, 0, s - 1, s - 1), fill=255)
        else:
            dr.rounded_rectangle((0, 0, s - 1, s - 1), radius=int(s * 0.18), fill=255)
        q = Image.new("RGBA", (s, s), (0, 0, 0, 0))
        q.paste(base, (0, 0), m)
        q.save(f"{pasta}/{arq}")
    fs = int(108 * f)
    inner = int(fs * 0.72)
    fg = Image.new("RGBA", (fs, fs), (0, 0, 0, 0))
    fg.paste(img.resize((inner, inner), Image.LANCZOS), ((fs - inner) // 2, (fs - inner) // 2))
    fg.save(f"{pasta}/ic_launcher_foreground.png")

os.makedirs(f"{RES}/mipmap-anydpi-v26", exist_ok=True)
xml = ('<?xml version="1.0" encoding="utf-8"?>\n'
       '<adaptive-icon xmlns:android="http://schemas.android.com/apk/res/android">\n'
       '    <background android:drawable="@color/ic_launcher_background"/>\n'
       '    <foreground android:drawable="@mipmap/ic_launcher_foreground"/>\n'
       '</adaptive-icon>\n')
for arq in ("ic_launcher.xml", "ic_launcher_round.xml"):
    open(f"{RES}/mipmap-anydpi-v26/{arq}", "w").write(xml)

os.makedirs(f"{RES}/values", exist_ok=True)
open(f"{RES}/values/ic_launcher_background.xml", "w").write(
    '<?xml version="1.0" encoding="utf-8"?>\n<resources>\n'
    f'    <color name="ic_launcher_background">#{bg[0]:02X}{bg[1]:02X}{bg[2]:02X}</color>\n</resources>\n')
print("Icones gerados em", RES)
