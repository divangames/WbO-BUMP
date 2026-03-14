"""
Создаёт installer_banner.bmp и installer_small.bmp для Inno Setup
из изображения сплеш-экрана (splash_banka.png или bg.webp).
Размеры: баннер 202x386 (Inno 6), маленький 55x58.
"""
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    print("Требуется: pip install Pillow")
    raise

BASE = Path(__file__).parent
ASSETS = BASE / "Assets" / "images"
# Порядок: сначала сплеш, потом фон
CANDIDATES = [
    ASSETS / "splash_banka.png",
    ASSETS / "bg.webp",
    ASSETS / "1bg.webp",
    ASSETS / "faicon.png",
]

def main():
    src = None
    for p in CANDIDATES:
        if p.exists():
            src = p
            break
    if not src:
        print("Не найден ни один файл для баннера. Добавьте Assets/images/splash_banka.png или bg.webp")
        return False

    img = Image.open(src).convert("RGB")
    # Баннер: 202x386 (сохраняем пропорции, обрезаем по центру)
    w, h = 202, 386
    img_big = img.copy()
    img_big.thumbnail((w * 2, h * 2), Image.Resampling.LANCZOS)
    # Центрируем и обрезаем до w x h
    tw, th = img_big.size
    left = max(0, (tw - w) // 2)
    top = max(0, (th - h) // 2)
    img_big = img_big.crop((left, top, left + w, top + h))
    if img_big.size != (w, h):
        img_big = img_big.resize((w, h), Image.Resampling.LANCZOS)
    out_big = BASE / "installer_banner.bmp"
    img_big.save(out_big, "BMP")
    print(f"Создан: {out_big}")

    # Маленький: 55x58
    img_small = img.copy()
    img_small.thumbnail((120, 120), Image.Resampling.LANCZOS)
    tw, th = img_small.size
    w2, h2 = 55, 58
    left = max(0, (tw - w2) // 2)
    top = max(0, (th - h2) // 2)
    img_small = img_small.crop((left, top, left + w2, top + h2))
    if img_small.size != (w2, h2):
        img_small = img_small.resize((w2, h2), Image.Resampling.LANCZOS)
    out_small = BASE / "installer_small.bmp"
    img_small.save(out_small, "BMP")
    print(f"Создан: {out_small}")
    return True

if __name__ == "__main__":
    import sys
    sys.exit(0 if main() else 1)
