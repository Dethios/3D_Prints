from pathlib import Path
import sys

from PIL import Image, ImageDraw, ImageFont

out = Path(__file__).resolve().parent
before = Image.open(out.parent/"Mickey_Qwen_Targeted_Hands/mickey-mounted-qwen-targeted-hands.png").convert("RGB")
selected = Image.open(out/sys.argv[1]).convert("RGB")
reference = Image.open(out/"animation-pose-reference.png").convert("RGB")
paper = (245,238,221)
page = Image.new("RGB",(1290,685),paper)
font = ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf",22)
draw=ImageDraw.Draw(page)
for x,name,image,areas in [
    (24,"Animation reference",reference,((215,16,335,96),(62,230,135,300))),
    (421,"Enamel artwork before edit",before,((633,192,827,354),(349,526,480,666))),
    (855,"Targeted Qwen revision",selected,((633,192,827,354),(349,526,480,666))),
]:
    draw.text((x,18),name,font=font,fill=(36,38,39))
    for y,area in zip((62,378),areas):
        crop=image.crop(area)
        scale=2 if image is not reference else 3
        crop=crop.resize((crop.width*scale,crop.height*scale),Image.Resampling.LANCZOS)
        page.paste(crop,(x,y))
page.save(out/(Path(sys.argv[1]).stem+"-comparison.png"))
