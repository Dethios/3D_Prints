from pathlib import Path
import sys
from PIL import Image, ImageDraw, ImageFont, ImageOps

out=Path(__file__).resolve().parent
label=sys.argv[1]
images=[
    ("Sticker reference",out/"sticker-composition.png"),
    ("Fitted NX3 ear",out/f"mickey-mounted-sticker-{label}.png"),
]
page=Image.new("RGB",(1350,780),(249,239,222))
draw=ImageDraw.Draw(page)
font=ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf",25)
for i,(name,path) in enumerate(images):
    panel=ImageOps.contain(Image.open(path).convert("RGB"),(640,710),Image.Resampling.LANCZOS)
    x=20+i*665
    draw.text((x,13),name,font=font,fill=(32,42,57))
    page.paste(panel,(x+(640-panel.width)//2,52+(710-panel.height)//2))
page.save(out/f"sticker-fit-comparison-{label}.png")
