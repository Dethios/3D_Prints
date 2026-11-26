"""Continuous vector artwork on the lower half of the fitted trio relief."""

import math

import numpy as np
from shapely import contains_xy
from shapely.geometry import LineString, Polygon
from shapely.ops import unary_union
from svgpathtools import parse_path


def path_points(d):
    for contour in parse_path(d).continuous_subpaths():
        points=[]
        for segment in contour:
            n=max(3,math.ceil(segment.length()/2.0))
            points.extend((p.real,p.imag) for p in (segment.point(j/n) for j in range(n)))
        tail=contour[-1].end
        points.append((tail.real,tail.imag))
        yield points


def shape(d):
    return unary_union([Polygon(p).buffer(0) for p in path_points(d)])


def line(d,width):
    return unary_union([LineString(p).buffer(width/2,quad_segs=5) for p in path_points(d)])


def native_pixels(u,v,source_shape):
    return (u+.5)*1254/source_shape[1]-.5,(v+.5)*1254/source_shape[0]-.5


def coverage(region,x,y):
    result=contains_xy(region,x,y).astype(float)*.40
    for dx,dy in ((1.15,0),(-1.15,0),(0,1.15),(0,-1.15)):
        result+=.15*contains_xy(region,x+dx,y+dy)
    return result


INK=(25,18,23)
RED=(211,17,46)
RED_LIGHT=(224,25,55)
RED_SHADOW=(175,15,40)
BLUE=(16,64,179)
BLUE_SHADOW=(15,48,150)
GOLD=(255,184,5)
GOLD_LIGHT=(255,198,13)
GOLD_SHADOW=(222,129,0)
SKIN=(249,195,143)
SKIN_SHADOW=(229,164,115)

# The cleared region ends at the lower face and scarf contours. The new
# robe goes through the mounting-side curve so its color stays continuous.
ERASE=shape(
 "M 61 700 Q 124 698 201 690 L 215 704 Q 225 735 249 746 "
 "Q 293 725 340 716 Q 417 700 485 713 L 531 728 "
 "Q 530 696 559 677 Q 608 646 675 632 Q 735 620 801 636 "
 "L 842 655 Q 916 713 984 684 L 1040 668 L 1104 716 "
 "L 1150 855 L 1130 1090 L 920 1330 L 30 1390 L 45 808 Z"
)

BLUE_GARMENT=shape(
 "M 78 655 Q 130 643 200 668 L 218 724 Q 191 778 159 831 "
 "Q 127 861 112 867 Q 100 837 94 792 Q 83 737 79 689 Z"
)
BLUE_CREASE=shape(
 "M 88 763 Q 113 739 145 723 Q 182 706 201 710 Q 157 746 130 783 "
 "Q 114 808 105 839 Q 96 806 88 763 Z"
)
BLUE_OUTER=line("M 77 662 Q 80 714 94 792 Q 100 837 112 867",5.7)
YELLOW_ROBE=shape(
 "M 825 697 Q 880 688 913 710 Q 962 669 1007 665 "
 "Q 1072 701 1109 756 L 1158 860 Q 1194 991 1128 1087 "
 "L 872 1305 L 615 1345 Q 596 1253 612 1140 "
 "Q 618 1014 652 945 Q 674 882 721 826 Z"
)
YELLOW_SHADOW=shape(
 "M 1018 692 Q 1065 734 1059 799 Q 1058 835 1036 872 "
 "Q 978 927 921 984 Q 857 1049 763 1162 "
 "L 815 1224 L 1159 969 L 1151 832 Z"
)
YELLOW_CUFF=shape(
 "M 698 969 Q 727 922 777 892 Q 831 860 887 863 "
 "L 925 895 Q 857 915 809 953 Q 764 990 726 1032 Z"
)
RED_ROBE=shape(
 "M 237 704 Q 251 728 280 754 Q 317 783 358 824 "
 "Q 445 852 544 843 Q 587 854 628 908 Q 655 949 673 1000 "
 "Q 699 1064 685 1130 L 677 1319 L 499 1405 L 105 1260 "
 "L 43 1046 Q 46 976 77 887 Q 101 813 156 779 "
 "Q 195 743 237 704 Z"
)
RED_SLEEVE=shape(
 "M 232 740 Q 183 763 151 799 Q 104 847 96 908 "
 "Q 101 969 142 1011 Q 173 1045 222 1065 "
 "L 323 1050 Q 301 974 281 914 Q 251 805 232 740 Z"
)
RED_FOLD=shape(
 "M 103 881 Q 140 963 211 998 Q 275 1029 323 1040 L 306 1058 "
 "Q 213 1041 150 994 Q 115 967 103 881 Z"
)
RED_CUFF=shape(
 "M 485 1082 Q 533 1034 580 1013 Q 624 992 655 1009 "
 "Q 677 1048 674 1110 Q 617 1086 567 1121 Q 531 1147 495 1187 Z"
)
RED_FACE=shape(
 "M 183 606 L 555 606 L 557 679 Q 545 710 535 730 Q 453 716 388 724 "
 "Q 318 733 271 761 Q 233 779 222 767 Q 218 735 201 714 L 194 660 Z"
)
YELLOW_FACE=shape(
 "M 825 598 L 1060 593 L 1061 623 Q 1044 641 1035 651 "
 "Q 1011 680 986 703 Q 970 724 948 738 Q 935 731 921 712 "
 "Q 891 680 865 661 L 835 651 Z"
)


def arc_points(xs,ys):
    """Smooth shared arc through the measured outer fan rib tips."""
    tips=np.column_stack((xs,ys))
    chunks=[]
    for i in range(len(tips)-1):
        p0=tips[max(i-1,0)]
        p1=tips[i]
        p2=tips[i+1]
        p3=tips[min(i+2,len(tips)-1)]
        t=np.linspace(0.,1.,24)[:,None]
        path=.5*((2*p1)+(-p0+p2)*t+(2*p0-5*p1+4*p2-p3)*t*t+(-p0+3*p1-3*p2+p3)*t*t*t)
        chunks.append(path)
    return tips,chunks


def fan_layers(pivot,tip_x,tip_y,outer_colors,heel_colors=None,heel_ratio=.4):
    """The blades, ribs, heel and outer edge share one continuous curve."""
    p=np.array(pivot,dtype=float)
    tips,arc=arc_points(tip_x,tip_y)
    outer=Polygon(np.vstack((p,*[v[:-1] for v in arc],arc[-1][-1],p))).buffer(0)
    layers=[(outer.buffer(3.2),INK,1.02)]
    for i,curve in enumerate(arc):
        if heel_colors:
            heel=p+(curve-p)*heel_ratio
            panels=[(np.vstack((curve,heel[::-1])),outer_colors[i%len(outer_colors)],2.28),
                    (np.vstack((p,heel,p)),heel_colors[i%len(heel_colors)],1.80)]
        else:
            panels=[(np.vstack((p,curve,p)),outer_colors[i%len(outer_colors)],2.17)]
        for points,rgb,height in panels:
            layers.append((Polygon(points).buffer(.32),rgb,height))
    if heel_colors:
        joined=np.concatenate([p+(v[:-1]-p)*heel_ratio for v in arc]+[(p+(arc[-1][-1:]-p)*heel_ratio)])
        layers.append((LineString(joined).buffer(3.1,quad_segs=5),INK,1.06))
    crease=[LineString([p,v]).buffer(2.9,quad_segs=5) for v in tips[1:-1]]
    layers.append((unary_union(crease).intersection(outer),INK,1.05))
    return layers


ORANGE_LAYERS=fan_layers(
    (432,1092),
    (155,199,258,327,401,480,554,622,671,704),
    (878,806,755,726,712,716,733,769,814,851),
    ((255,143,45),(255,113,21)),
    ((189,116,118),(208,136,139)),.405,
)
YELLOW_LAYERS=fan_layers(
    (713,948),
    (533,581,631,688,747,807,865,916,963,980),
    (720,675,649,637,639,649,677,716,774,833),
    ((255,209,21),(255,229,55)),
)

# Four visible curled fingers stay under one uninterrupted top contour.
# The thumb is hidden behind the fan hinge.
RED_GRIP=shape(
    "M 486 1180 Q 454 1171 430 1152 "
    "Q 414 1159 405 1150 Q 398 1142 405 1133 "
    "Q 390 1129 387 1118 Q 386 1108 394 1102 "
    "Q 381 1097 382 1084 Q 382 1076 390 1070 "
    "Q 379 1062 388 1052 Q 409 1035 453 1045 "
    "Q 487 1052 503 1073 Q 519 1096 508 1123 "
    "Q 497 1150 486 1180 Z"
)
GRIP_CREASE=line(
    "M 390 1070 Q 409 1064 430 1077 M 394 1102 Q 413 1096 434 1108 "
    "M 405 1133 Q 420 1128 437 1139",5.1
)
YELLOW_HAND=shape(
    "M 713 974 Q 702 949 705 932 Q 704 908 699 893 "
    "Q 695 870 704 851 Q 710 840 726 829 "
    "Q 735 821 741 825 Q 748 815 755 818 Q 764 815 768 825 "
    "Q 777 817 783 824 Q 788 830 781 838 Q 792 833 795 841 "
    "Q 795 850 785 861 Q 773 875 770 888 Q 768 907 773 920 "
    "Q 749 938 731 952 Q 720 962 713 974 Z"
)
YELLOW_CREASE=line(
    "M 741 825 Q 716 844 715 865 M 767 825 Q 741 843 735 872 "
    "M 781 838 Q 762 854 752 881",4.9
)


CLOTH_LAYERS=[
        (YELLOW_ROBE.buffer(3.0),INK,1.0),(YELLOW_ROBE,GOLD,1.48),
        (YELLOW_SHADOW.intersection(YELLOW_ROBE),GOLD_SHADOW,1.34),
        (YELLOW_CUFF.intersection(YELLOW_ROBE),GOLD_LIGHT,1.62),
        (line("M 716 1016 Q 764 953 818 925 Q 864 903 898 900",5.6).intersection(YELLOW_ROBE),INK,1.01),
        (RED_ROBE.buffer(3.0),INK,1.0),(RED_ROBE,RED,1.46),
        (RED_SLEEVE.intersection(RED_ROBE),RED_LIGHT,1.54),
        (RED_FOLD.intersection(RED_ROBE),RED_SHADOW,1.30),
        (RED_CUFF.intersection(RED_ROBE),RED_LIGHT,1.57),
        (line("M 105 893 Q 130 958 183 993 Q 227 1023 282 1031 M 489 1084 Q 546 1015 613 1007 Q 635 1005 655 1010",5.5).intersection(RED_ROBE),INK,1.03),
]
FAN_LAYERS=[
        *YELLOW_LAYERS,
        (YELLOW_HAND.buffer(2.9),INK,1.02),(YELLOW_HAND,SKIN,2.40),(YELLOW_CREASE,INK,1.17),
        *ORANGE_LAYERS,
        (RED_GRIP.buffer(3.0),INK,1.0),(RED_GRIP,SKIN,2.40),(GRIP_CREASE,INK,1.17),
]


def continuous_trio(alpha,height,color,u,v,source_shape):
    """Lay out the replacement foreground once, with shared edges."""
    x,y=native_pixels(u,v,source_shape)
    original_alpha=alpha
    erase=coverage(ERASE,x,y)
    alpha=alpha.copy()*(1-erase)
    depth=height.copy()*(1-erase)
    canvas=color*alpha[:,:,None]
    def paint(region,rgb,z,fade=1.):
        w=coverage(region,x,y)*fade
        nonlocal alpha,depth,canvas
        alpha+=(1-alpha)*w
        depth+=(z-depth)*w
        canvas+=(np.asarray(rgb)/255.*w[:,:,None]-canvas*w[:,:,None])
    blue_fade=np.clip((y-658)/39,0,1)
    paint(BLUE_GARMENT,BLUE,1.45,blue_fade)
    paint(BLUE_CREASE,BLUE_SHADOW,1.28,blue_fade)
    paint(BLUE_OUTER,INK,.98,blue_fade)
    for region,rgb,z in CLOTH_LAYERS:
        paint(region,rgb,z)
    # Reapply the source faces over the clothing, behind the original fan
    # edges. This maintains their facial features and the old dark outline.
    head=np.maximum(coverage(YELLOW_FACE,x,y),
                    coverage(RED_FACE,x,y)*(~((x<226)&(y>710))))
    alpha+=head*(original_alpha-alpha)
    depth+=head*(height-depth)
    canvas+=head[:,:,None]*(color*original_alpha[:,:,None]-canvas)
    for region,rgb,z in FAN_LAYERS:
        paint(region,rgb,z)
    return alpha,depth,canvas/np.maximum(alpha[:,:,None],.0001)
