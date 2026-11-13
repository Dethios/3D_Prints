/*******************************************
 Stroller Umbrella Holder by @wallace

 Changelog:
 * 2023-04-21  Initial release
********************************************/

include <BOSL2/std.scad>
include <BOSL2/threading.scad>
include <BOSL2/screws.scad>

CLEARANCE = 0.2;  // set the clearance

MODEL = "rod";  // choose from: rod, topclamp, botclamp

// rod settings
ROD_TOTAL_HEIGHT = 150;  // total height of the rod including the threaded part
THREADED_HEIGHT = 8;  // height of the threaded part
INSERT_HEIGHT = 20;  // height of the umbrella insert
ROD_DIAMETER = 11;
ROD_DIAMETER_EXTRA = 3;  // gives the rod extra thickness to allow for wide inserts
INSERT_DIAMETER = 10 + CLEARANCE*2;  // insert for the umbrella

// clamp settings
CLAMP_DIMENSIONS = [32, 15];  // 2-d dimensions of the clamp
CLAMP_WALL = 2;  // how thick the clamp wall should be
CLAMP_WIDTH = 25;  // how long should the entire clamp be
CLAMP_CONNECTOR_ANGLE = 40;  // the angle of the handle relative to the ground; used to correct the angle of the rod to make it perpendicular to the ground
CLAMP_CONNECTOR_WIDTH = 18;  // how far out should the rod connector stick
CLAMP_ROUNDING = 2;


// past this point, you're on your own :)
cone_height = ROD_TOTAL_HEIGHT - THREADED_HEIGHT;
clamp_connector_wedge = CLAMP_CONNECTOR_WIDTH / tan(CLAMP_CONNECTOR_ANGLE);

$fn=100;

module _thread(internal = false) {
    d = internal ? ROD_DIAMETER + CLEARANCE*2 : ROD_DIAMETER;  // $slope doesn't work, so...
    threaded_rod(d=d,
                 height=THREADED_HEIGHT,
                 pitch=2,
                 anchor=BOTTOM,
                 internal=internal) children();
}

module rod() {
    diff() {
        _thread()
            attach(TOP)
            cyl(d=ROD_DIAMETER + ROD_DIAMETER_EXTRA,
                height=cone_height,
                chamfer1=2.5,
                anchor=BOTTOM
            )
                attach(TOP)
                cyl(d=INSERT_DIAMETER,
                    height=INSERT_HEIGHT,
                    anchor=TOP,
                    chamfer2=-1,
                    $tag="remove");
    }
}

module _clamp_ear() {
    cuboid([3, CLAMP_WIDTH, 8], anchor=BOTTOM+LEFT) {
    position(FRONT+BOTTOM+RIGHT) orient(FRONT)
        fillet(l=CLAMP_WIDTH, r=4, anchor=TOP);
    position(LEFT) orient(RIGHT) up(0.5)
      screw_hole("M3", head="socket", thread="none", length=5, $tag="remove");
    }
}

module clamp(side = "bottom") {
    diff() {
        right_half() {
            rect_tube(isize=CLAMP_DIMENSIONS, wall=CLAMP_WALL, h=CLAMP_WIDTH, rounding=CLAMP_ROUNDING, irounding=1.5) {
                attach(FRONT) _clamp_ear();
                attach(BACK, norot=true) xrot(-90) _clamp_ear();
                if (side == "top") {
                    attach(RIGHT)
                        prismoid(size1=[CLAMP_DIMENSIONS.y + CLAMP_WALL*2 - CLAMP_ROUNDING*2, CLAMP_WIDTH],
                                 size2=[(CLAMP_DIMENSIONS.y + CLAMP_WALL*2 - CLAMP_ROUNDING*2)/2, CLAMP_WIDTH-clamp_connector_wedge],
                                 shift=[0, -clamp_connector_wedge/2],
                                 h=CLAMP_CONNECTOR_WIDTH,
                                 rounding2=[CLAMP_ROUNDING, CLAMP_ROUNDING, 0, 0])
                            attach(BACK, overlap=THREADED_HEIGHT-0.001)  // fix preview
                                tag("remove") _thread(internal=true);
                }
            }
        }
    }
}

if (MODEL == "rod") rod();
if (MODEL == "topclamp") clamp("top");
if (MODEL == "botclamp") clamp("bot");
