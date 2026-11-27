"""Cut a one-shoulder breakaway coupon from the final cradle and real R6 head."""
from build_fixture import HERE,R6,FILE,base,cq,trimesh,json,ELEV

def main():
    # Keep the actual lower tip, curved gold underside and first lateral tie.
    limits=base.rect(34.,55.,-19.02,15.02,-.1,34.5)
    parent=cq.Assembly.load(str(R6/"purple_castle_card_wand_R6.step"))
    def crop(name):
        shape=parent.objects[name].obj.rotate((0,0,0),(1,0,0),90).translate((0,0,ELEV))
        return shape.intersect(limits).clean()
    carrier=crop("head_purple")
    # Outside the cropped X=34 face, an integral basal grip keeps the sample
    # upright after release. It joins the cut face above the support teeth.
    heel=base.rect(25.5,33.65,-6.0,1.2,0,1.55)
    post=base.rect(28.0,33.65,-3.0,-1.2,1.45,34.50)
    link=base.rect(33.50,34.25,-2.75,-1.35,22.3,34.50)
    carrier=base.combine([carrier,heel,post,link])
    fixture=cq.importers.importStep(str(HERE/(FILE+".step"))).val().intersect(limits).clean()
    shapes={"release_coupon_carrier_purple":carrier,"release_coupon_rim_gold":crop("head_gold"),
            "release_coupon_cradle_blue_A":fixture}
    dest=HERE/"release_coupon"
    dest.mkdir(exist_ok=True)
    report={}
    for name,shape in shapes.items():
        p=dest/(name+".stl")
        mesh=base.save_stl(shape,p)
        assert shape.isValid() and mesh.is_volume and len(mesh.split())==1,(name,len(shape.Solids()))
        report[name]={"sha256":base.digest(p),"bounds_mm":mesh.bounds.round(4).tolist(),"solid_count":1}
    from validate_wand import solid
    parts=[solid(trimesh.load_mesh(dest/(n+".stl"))) for n in shapes]
    for i,a in enumerate(parts):
        for b in parts[i+1:]:
            assert abs((a^b).volume())<1.e-6
    (dest/"coupon_layout.json").write_text(json.dumps(report,indent=2)+"\n")
    print(report)

if __name__=="__main__":
    main()
