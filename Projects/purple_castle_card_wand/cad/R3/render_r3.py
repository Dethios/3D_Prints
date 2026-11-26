"""Matched views of the R2 and R3 STL surfaces under the same lighting."""
from PIL import Image,ImageDraw
import trimesh

from build_r3 import R3,R2
from render_wand import view,font,PAPER,INK


def meshes(folder):
    return {path.stem:trimesh.load_mesh(path) for path in (folder/"print_parts").glob("*.stl")}


def make_board():
    old,new=meshes(R2),meshes(R3)
    board=Image.new("RGB",(1700,1090),PAPER)
    text=ImageDraw.Draw(board)
    text.text((36,20),"Castle wand  /  R3",font=font(42,True),fill=INK)
    text.text((38,79),"CAD mesh preview   /   140 mm star width",font=font(20),fill="#615762")

    def panel(parts,x,y,title,caption,target,direction,span,size):
        text.text((x,y),title,font=font(25,True),fill=INK)
        text.text((x,y+35),caption,font=font(16),fill="#615762")
        board.paste(view(parts,target,direction,span,size),(x,y+62))

    panel(new,30,145,"Front assembly","Cream doorway emblem and rose between two gold curls",
          (0,-12,6),(.065,.035,1),198,(650,865))
    p={"target":(0,-31,6),"direction":(.06,.04,1),"span":60,"size":(460,297)}
    panel(old,700,145,"Previous scrolls","R2",**p)
    panel(new,1198,145,"Simplified curls","R3",**p)
    panel(new,700,570,"Castle relief","Curved roofs, tower walls and cornices",
          (0,3,9),(.48,-.73,.78),63,(465,385))
    panel(new,1198,570,"Bow relief","Padded loops, recessed folds and rounded knot",
          (0,-65,12),(.42,-.72,.79),54,(460,385))
    board.save(R3/"castle_relief_comparison.png")

if __name__=="__main__":
    make_board()
