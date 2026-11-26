"""Compare the latest reference detail with assembled, actual R5 print meshes."""
from PIL import Image,ImageDraw

from build_r5 import R5,R2
from render_r3 import meshes
from render_wand import view,font,PAPER,INK


def main():
    model=meshes(R5)
    board=Image.new("RGB",(1696,1090),PAPER)
    draw=ImageDraw.Draw(board)
    draw.text((32,18),"Castle wand  /  R5",font=font(42,True),fill=INK)
    draw.text((35,78),"CAD mesh preview   /   140 mm star width",font=font(20),fill="#615762")
    def label(x,y,title,sub):
        draw.text((x,y),title,font=font(25,True),fill=INK)
        draw.text((x,y+35),sub,font=font(16),fill="#615762")
    def panel(x,y,title,sub,target,direction,span,size):
        label(x,y,title,sub)
        board.paste(view(model,target,direction,span,size),(x,y+62))
    panel(30,135,"Front assembly","Open purple doorway beneath the cream Mickey",
          (0,-8,8),(.045,.025,1),197,(650,860))
    label(700,135,"Latest reference","Bow loops, notched tails and paired curls")
    detail=Image.open(R2.parent/"art/R5/reference_comparison.png").convert("RGB").crop((16,51,569,447))
    board.paste(detail.resize((460,329),Image.Resampling.LANCZOS),(700,197))
    panel(1198,135,"R5 geometry","Released front meshes in the wand palette",
          (0,-47,8),(.03,.03,1),68,(460,329))
    panel(700,575,"Assembled clearance","The new bow sits in front of the fixed rim",
          (0,-41,9),(.55,-.74,.83),62,(465,378))
    panel(1198,575,"Bow and curl relief","Shallow folded loops and curved gold ribbons",
          (0,-45,9),(.18,-.53,.83),65,(460,378))
    board.save(R5/"castle_wand_R5_preview.png")

if __name__=="__main__":
    main()
