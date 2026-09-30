#!/usr/bin/env python3
"""Deterministically export and validate scenario-owned Warcraft III MDL models."""
from __future__ import annotations
import argparse, hashlib, json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "scenario/assets/custom-models/models.json"
IMPORT_ROOT = ROOT / "map/AgeOfSailWorld.w3x/war3mapImported/age_of_sail/characters"
GENERATED = ROOT / "scenario/visuals/generated"
SEQUENCES = (("Stand",0,1000),("Walk",1100,1900),("Attack",2000,2600),("Death",2700,3500),("Decay Flesh",3600,4400))
ATTACHMENTS = ("origin","head","chest","hand,left","hand,right","weapon")

class ModelError(ValueError): pass
def load(path=SOURCE): return json.loads(Path(path).read_text(encoding="utf-8"))
def box(cx,cy,cz,sx,sy,sz):
    return [(cx+x*sx,cy+y*sy,cz+z*sz) for z in (-.5,.5) for y in (-.5,.5) for x in (-.5,.5)]
FACES=((0,1,3),(0,3,2),(4,6,7),(4,7,5),(0,4,5),(0,5,1),(2,3,7),(2,7,6),(0,2,6),(0,6,4),(1,5,7),(1,7,3))

def geometry(row):
    h=row["height"]; parts=[(0,0,h*.48,28,20,h*.48),(0,0,h*.82,22,18,h*.24),(0,0,h*.96,21,20,20)]
    silhouettes={"regal_robe":(42,34),"warrior_tunic":(30,24),"naval_coat":(34,27),"feather_cloak":(48,18),"scholar_robe":(38,30),"draped_dress":(43,34),"long_coat":(36,28),"navigator_cloak":(44,22),"lamellar_armor":(39,31)}
    w,d=silhouettes[row["silhouette"]]; parts[0]=(0,0,h*.42,w,d,h*.62)
    head={"turban":(28,24,9),"tanjak":(32,18,10),"bicorne":(36,17,8),"crest":(13,18,24),"crown":(25,23,13),"cap":(26,22,8),"braids":(29,21,12),"songkok":(23,21,14),"broad_hat":(40,29,5),"topknot":(12,12,18),"official_hat":(37,18,12),"war_hat":(39,30,9)}[row["headgear"]]
    parts.append((0,0,h+head[2]*.45,*head))
    equip={"sword":(4,4,58),"kris":(5,4,38),"spear":(4,4,104),"folio":(22,5,28),"paddle":(8,4,94)}[row["equipment"]]
    parts.append((w*.62,0,h*.49,*equip))
    vertices=[]; triangles=[]
    for part in parts:
        start=len(vertices); vertices += box(*part)
        triangles += [tuple(start+i for i in face) for face in FACES]
    return vertices,triangles

def _mdl_raw(row):
    verts,faces=geometry(row); h=row["height"]
    vs=",\n".join("\t\t{ %.6f, %.6f, %.6f }"%v for v in verts)
    fs=",\n".join("\t\t{ %d, %d, %d }"%f for f in faces)
    seq="\n".join(f'\tAnim "{n}" {{ Interval {{ {a}, {b} }}, MinimumExtent {{ -32, -24, 0 }}, MaximumExtent {{ 32, 24, {h+20} }}, BoundsRadius {h}, }}' for n,a,b in SEQUENCES)
    atts="\n".join(f'Attachment "{n}" {{ ObjectId {i+2}, Parent 0, AttachmentID {i}, }}' for i,n in enumerate(ATTACHMENTS))
    return f'''Version {{ FormatVersion 800, }}\nModel "aos_{row['id']}" {{ NumGeosets 1, NumGeosetAnims 1, NumBones 1, NumAttachments 6, BlendTime 150, MinimumExtent {{ -32, -24, 0 }}, MaximumExtent {{ 32, 24, {h+20} }}, BoundsRadius {h}, }}\nSequences 5 {{\n{seq}\n}}\nTextures 1 {{ Bitmap {{ Image "", ReplaceableId 1, }} }}\nMaterials 1 {{ Material {{ Layer {{ FilterMode None, static TextureID 0, }} }} }}\nGeoset {{\n\tVertices {len(verts)} {{\n{vs}\n\t}}\n\tNormals {len(verts)} {{\n''' + ",\n".join("\t\t{ 0.000000, 0.000000, 1.000000 }" for _ in verts) + f'''\n\t}}\n\tTVertices {len(verts)} {{\n''' + ",\n".join("\t\t{ 0.000000, 0.000000 }" for _ in verts) + f'''\n\t}}\n\tVertexGroup {{\n''' + ",\n".join("\t\t0" for _ in verts) + f'''\n\t}}\n\tFaces 1 {len(faces)*3} {{ Triangles {{\n{fs}\n\t}} }}\n\tGroups 1 1 {{ Matrices {{ 0 }} }}\n\tMinimumExtent {{ -32, -24, 0 }}, MaximumExtent {{ 32, 24, {h+20} }}, BoundsRadius {h}, MaterialID 0, SelectionGroup 0,\n}}\nGeosetAnim {{ static Alpha 1.000000, GeosetId 0, }}\nBone "Root" {{ ObjectId 0, GeosetId 0, GeosetAnimId 0, Translation 3 {{ Linear, 2700: {{ 0,0,0 }}, 3500: {{ 0,0,-{h*.7:.6f} }}, 4400: {{ 0,0,-{h:.6f} }}, }} }}\n{atts}\nPivotPoints 8 {{\n''' + ",\n".join("\t{ 0.000000, 0.000000, %.6f }"%(h if i==3 else h*.55 if i in (4,5,6,7) else 0) for i in range(8)) + f'''\n}}\nCollisionShape "Collision" {{ ObjectId 8, Shape Box, Vertices 2 {{ {{ -22,-18,0 }}, {{ 22,18,{h} }} }}, }}\nCamera "Portrait" {{ Position {{ 110,-150,{h*.78:.6f} }}, FieldOfView 0.610865, FarClip 1000, NearClip 8, Target {{ Position {{ 0,0,{h*.70:.6f} }}, }} }}\n'''

def mdl(row):
    # The collision node occupies the otherwise unused object/pivot slot 1.
    return _mdl_raw(row).replace(
        'CollisionShape "Collision" { ObjectId 8,',
        'CollisionShape "Collision" { ObjectId 1,',
    )

def validate_source(data):
    if data.get("format")!="age_of_sail_custom_models_v1": raise ModelError("invalid source format")
    ids=[x.get("id") for x in data.get("models",[])];
    if len(ids)!=14 or len(ids)!=len(set(ids)): raise ModelError("expected 14 unique high-priority models")
    for row in data["models"]:
        if not re.fullmatch(r"[a-z][a-z0-9_]*",row["id"]): raise ModelError("unsafe model ID")
        v,f=geometry(row); b=data["budgets"]
        if len(v)>b["modelMaxVertices"] or len(f)>b["modelMaxTriangles"]: raise ModelError("model geometry budget exceeded")
    return True

def build(data):
    validate_source(data); imports=[]; objects=[]; snapshots=[]
    for row in sorted(data["models"],key=lambda x:x["id"]):
        text=mdl(row); path=f"war3mapImported/age_of_sail/characters/{row['id']}.mdl"
        vertices,triangles=geometry(row)
        imports.append({"id":f"character_{row['id']}_model","kind":"unit_model","importPath":path,"source":f"scenario/assets/custom-models/models.json#{row['id']}","sha256":hashlib.sha256(text.encode()).hexdigest(),"license":data["shared"]["license"],"attribution":data["shared"]["attribution"],"derivativeOf":None,"vertices":len(vertices),"triangles":len(triangles),"textureBytes":0,"animations":len(SEQUENCES),"runtimeUse":data["shared"]["runtimeUse"]})
        objects.append({"entityKind":"character","entityId":row["id"],"modelPath":path,"portraitCamera":"Portrait","teamColorSource":"controller","variation":{"silhouette":row["silhouette"],"headgear":row["headgear"],"equipment":row["equipment"]}})
        snapshots.append({"label":row["id"],"states":{n:{"interval":[a,b],"rootZAtEnd": -row["height"] if n=="Decay Flesh" else (-row["height"]*.7 if n=="Death" else 0)} for n,a,b in SEQUENCES}})
    return imports,objects,snapshots

def preview(data):
    cards=[]
    for i,row in enumerate(sorted(data["models"],key=lambda x:x["id"])):
        x=20+(i%4)*245; y=20+(i//4)*150
        cards.append(f'<g transform="translate({x} {y})"><rect width="225" height="130" fill="#17202a" stroke="#d4ac0d"/><circle cx="112" cy="35" r="13" fill="#c39b77"/><path d="M82 105 L92 52 L132 52 L142 105 Z" fill="#b03a2e"/><text x="112" y="121" text-anchor="middle" fill="white" font-size="12">{row["id"]}</text><text x="112" y="16" text-anchor="middle" fill="#f7dc6f" font-size="10">{row["headgear"]} / {row["equipment"]}</text></g>')
    return '<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="620" viewBox="0 0 1000 620"><rect width="100%" height="100%" fill="#0b0f14"/>'+''.join(cards)+'</svg>\n'

def write_outputs(data):
    imports,objects,snapshots=build(data); IMPORT_ROOT.mkdir(parents=True,exist_ok=True); GENERATED.mkdir(parents=True,exist_ok=True)
    for row in data["models"]: (IMPORT_ROOT/f"{row['id']}.mdl").write_text(mdl(row),encoding="utf-8",newline="\n")
    outputs={"custom-model-imports.json":{"format":"age_of_sail_model_imports_v1","imports":imports},"custom-model-object-data.json":{"format":"age_of_sail_model_objects_v1","objects":objects},"custom-model-animation-snapshots.json":snapshots,"custom-model-scene-fixtures.json":{"fixtures":[{"id":x,"activeModels":min(96,n),"triangles":min(96,n)*60,"textureBytes":0,"effects":e} for x,n,e in (("local_battle",64,8),("naval",36,12),("settlement",48,4),("city_capture",72,16),("representation_reconstruction",96,0),("cross_map",32,0))]},"custom-model-contact-sheet.svg":preview(data)}
    for name,value in outputs.items(): (GENERATED/name).write_text(value if isinstance(value,str) else json.dumps(value,indent=2,sort_keys=True)+"\n",encoding="utf-8",newline="\n")
    return imports

def main(argv=None):
    parser=argparse.ArgumentParser(); parser.add_argument("--check",action="store_true"); args=parser.parse_args(argv); data=load(); expected=build(data)
    if args.check:
        import tempfile
        # Structural equivalence is checked directly against deterministic generation.
        for row in data["models"]:
            path=IMPORT_ROOT/f"{row['id']}.mdl"
            if not path.is_file() or path.read_text(encoding="utf-8")!=mdl(row): raise ModelError(f"stale generated model: {row['id']}")
        if json.loads((GENERATED/"custom-model-imports.json").read_text())!={"format":"age_of_sail_model_imports_v1","imports":expected[0]}: raise ModelError("stale import manifest")
    else: write_outputs(data)
    print(json.dumps({"models":len(data["models"]),"triangles":sum(len(geometry(x)[1]) for x in data["models"]),"textureBytes":0},sort_keys=True))
if __name__=="__main__": main()
