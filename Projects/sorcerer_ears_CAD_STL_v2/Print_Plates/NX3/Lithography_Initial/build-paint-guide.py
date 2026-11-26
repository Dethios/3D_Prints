from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

out=Path(__file__).resolve().parent
project=out.parents[2]
root=project/"previews/Lithography_20261122/Reference_Match"
ear_pictures=[
    root/"Broom_Pin_Match/New_Profile/Marked_Stars/brooms-mounted-marked-stars.png",
    root/"Mickey_Sticker_Base/Wispy_Ornaments/mickey-mounted-wispy-original-ornaments.png",
]
back=(248,245,237)
ink=(27,34,49)
soft=(73,85,100)
page=Image.new("RGB",(1960,1280),back)
draw=ImageDraw.Draw(page)

def font(size,bold=False):
    return ImageFont.truetype("C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf",size)

draw.text((76,48),"Sorcerer ears · Paint guide",font=font(49,True),fill=ink)
draw.text((77,116),"Use the full-color views to paint the white areas. The blue bases and gold rims are shown for orientation.",font=font(25),fill=soft)

for img,name,x,colors in [
    (ear_pictures[0],"Brooms",76,[("#E68A47","Orange wood and hands"),("#FFD22D","Yellow straw"),
     ("#AB6C20","Brown bucket staves"),("#A4A7A8","Silver hoops and handles"),("#ADE1EA","Pale blue water"),("#DFB365","Gold stars")]),
    (ear_pictures[1],"Mickey",1010,[("#F1BA85","Peach face"),("#EBC06A","Gold shoes and rope"),
     ("#F0CC61","Yellow hat symbols"),("#E3BB70","Gold stars and arcs"),("#393443","Deep plum shadows"),("#EEE4DD","Ivory magic and gloves")]),
]:
    draw.text((x,173),name,font=font(34,True),fill=ink)
    pic=Image.open(img).convert("RGB")
    pic=pic.resize((730,730),Image.Resampling.LANCZOS)
    page.paste(pic,(x+60,223))
    for i,(swatch,label) in enumerate(colors):
        c,r=i%2,i//2
        sx,sy=x+c*393,978+r*55
        draw.rounded_rectangle((sx,sy,sx+31,sy+31),radius=6,fill=swatch,outline=(162,151,135),width=1)
        draw.text((sx+45,sy-2),label,font=font(24),fill=ink)

draw.line((77,1150,1883,1150),fill=(199,197,184),width=2)
draw.text((77,1175),"K2 plate",font=font(25,True),fill=ink)
draw.text((213,1175),"Brooms print in white. Mickey prints in blue, white, red and black. Paint the remaining colors on white.",font=font(25),fill=soft)
draw.text((77,1219),"The swatches identify areas to paint. Use the artwork above for the full palette and linework.",font=font(21),fill=soft)
page.save(out/"Sorcerer_NX3_Full_Color_Paint_Guide.png",dpi=(180,180))
