#!/usr/bin/env python3
"""Render and validate deterministic, dependency-free Warcraft TGA icons."""
from __future__ import annotations
import argparse, hashlib, json, math, struct
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/"scenario/visuals/custom-2d-assets.json"
DEFAULT_OUT=ROOT/"_build/custom-2d"
PALETTES={
 "iron":((30,38,43),(183,174,145)),"navy":((18,39,62),(210,157,66)),"verdigris":((18,62,59),(100,207,170)),
 "parchment":((67,43,25),(235,205,142)),"gold":((66,37,13),(247,188,47)),"crimson":((69,18,22),(231,91,53)),
 "earth":((55,34,22),(209,151,91)),"bronze":((52,35,20),(206,139,58)),"turquoise":((13,53,57),(54,210,195)),
 "ming":((66,13,18),(239,184,74)),"ocean":((10,43,61),(81,190,196)),"lapis":((20,30,76),(236,184,61)),"spice":((67,27,18),(225,128,43))}

class AssetError(ValueError): pass
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def pixels(n=64): return [[(0,0,0,0) for _ in range(n)] for _ in range(n)]
def put(p,x,y,c):
 if 0<=y<len(p) and 0<=x<len(p): p[y][x]=c
def line(p,a,b,c,w=1):
 x0,y0=a; x1,y1=b; steps=max(abs(x1-x0),abs(y1-y0),1)
 for i in range(steps+1):
  x=round(x0+(x1-x0)*i/steps); y=round(y0+(y1-y0)*i/steps)
  for yy in range(y-w,y+w+1):
   for xx in range(x-w,x+w+1):
    if (xx-x)**2+(yy-y)**2<=w*w+1: put(p,xx,yy,c)
def poly(p,points,c):
 ys=range(max(0,min(y for _,y in points)),min(len(p)-1,max(y for _,y in points))+1)
 for y in ys:
  xs=[]
  for (x1,y1),(x2,y2) in zip(points,points[1:]+points[:1]):
   if (y1<=y<y2) or (y2<=y<y1): xs.append(x1+(y-y1)*(x2-x1)/(y2-y1))
  xs.sort()
  for a,b in zip(xs[::2],xs[1::2]):
   for x in range(math.ceil(a),math.floor(b)+1): put(p,x,y,c)
def rect(p,box,c):
 x0,y0,x1,y1=box
 for y in range(y0,y1+1):
  for x in range(x0,x1+1): put(p,x,y,c)
def circle(p,cx,cy,r,c):
 for y in range(cy-r,cy+r+1):
  for x in range(cx-r,cx+r+1):
   if (x-cx)**2+(y-cy)**2<=r*r: put(p,x,y,c)
def icon(asset,n=64):
 p=pixels(n); bg,fg=PALETTES[asset["palette"]]; ink=(*fg,255); dark=(*bg,255); edge=(244,222,173,255)
 circle(p,32,32,29,(*bg,245)); circle(p,32,32,25,(*bg,255))
 s=asset["symbol"]
 if s in {"crossed_muskets","matchlock"}:
  line(p,(13,50),(51,17),ink,3); line(p,(14,46),(49,16),dark,1)
  if s=="crossed_muskets": line(p,(14,17),(51,50),edge,3)
  else: poly(p,[(13,48),(25,42),(31,47),(18,54)],ink); line(p,(38,27),(45,37),edge,1)
 elif s in {"cannon","swivel_gun"}:
  line(p,(15,27),(48,35),ink,5 if s=="cannon" else 3); rect(p,(17,36,46,40),edge); circle(p,22,45,7,ink); circle(p,43,45,7,ink)
 elif s=="relic": poly(p,[(32,10),(45,25),(40,51),(24,51),(19,25)],ink); circle(p,32,29,7,dark); line(p,(32,19),(32,39),edge,1)
 elif s in {"chart","register","archive","codex"}:
  rect(p,(16,13,48,51),ink); rect(p,(20,17,44,47),dark); line(p,(24,23),(40,23),edge,1); line(p,(24,30),(39,30),edge,1); line(p,(24,37),(37,37),edge,1)
  if s=="chart": line(p,(22,42),(40,20),edge,2); circle(p,34,31,5,ink)
  elif s=="codex": line(p,(32,15),(32,49),edge,1); circle(p,38,37,4,edge)
  elif s=="archive": poly(p,[(27,31),(32,24),(37,31),(32,39)],edge)
 elif s in {"cargo","customs_chest"}:
  rect(p,(14,27,50,50),ink); rect(p,(17,19,47,29),edge); line(p,(14,34),(50,34),dark,2); rect(p,(29,30,35,40),edge)
  if s=="customs_chest": line(p,(22,43),(44,43),dark,1)
 elif s=="rockets":
  for dx in (-10,0,10): poly(p,[(32+dx,12),(38+dx,22),(35+dx,42),(29+dx,42),(26+dx,22)],ink); poly(p,[(29+dx,43),(35+dx,43),(32+dx,55)],edge)
 elif s=="horse": poly(p,[(14,48),(19,28),(27,15),(39,17),(49,28),(43,35),(46,51),(37,51),(33,37),(25,39),(23,51)],ink); circle(p,40,24,2,dark)
 elif s=="goldwork": circle(p,32,32,18,ink); circle(p,32,32,11,dark); circle(p,32,32,5,edge)
 elif s=="mosaic":
  for y in range(17,48,8):
   for x in range(17,48,8): poly(p,[(x,y-4),(x+4,y),(x,y+4),(x-4,y)],ink if (x+y)//8%2 else edge)
 elif s=="wreck": poly(p,[(12,39),(50,39),(43,51),(20,51)],ink); line(p,(31,39),(31,15),edge,2); poly(p,[(33,17),(48,30),(33,30)],edge); line(p,(15,55),(50,55),ink,2)
 else: raise AssetError(f"unsupported symbol {s}")
 return p
def downsample(p,size):
 factor=len(p)//size; out=pixels(size)
 for y in range(size):
  for x in range(size):
   block=[p[y*factor+yy][x*factor+xx] for yy in range(factor) for xx in range(factor)]
   out[y][x]=tuple(round(sum(v[i] for v in block)/len(block)) for i in range(4))
 return out
def tga_bytes(p):
 h=len(p); w=len(p[0]); header=struct.pack("<BBBHHBHHHHBB",0,0,2,0,0,0,0,0,w,h,32,0x28)
 return header+b"".join(bytes((b,g,r,a)) for row in p for r,g,b,a in row)
def luminance(c): return .2126*c[0]+.7152*c[1]+.0722*c[2]
def metrics(p):
 opaque=[c for row in p for c in row if c[3]>=128]; transparent=sum(c[3]<128 for row in p for c in row)
 border=[*p[0],*p[-1],*(row[0] for row in p),*(row[-1] for row in p)]
 return {"opaquePixels":len(opaque),"transparentPixels":transparent,"luminanceRange":round(max(map(luminance,opaque))-min(map(luminance,opaque)),2),"borderOpaquePixels":sum(c[3]>=128 for c in border)}
def validate_source(doc):
 if doc.get("format")!="age_of_sail_custom_2d_v1": raise AssetError("invalid format")
 ids=[a.get("id") for a in doc.get("assets",[])]
 if len(ids)!=16 or len(set(ids))!=len(ids): raise AssetError("expected 16 unique high-priority assets")
 for a in doc["assets"]:
  if a.get("kind")!="icon" or a.get("role") not in {"equipment","treasure"} or not a.get("uses"): raise AssetError(f"{a.get('id')}: invalid use metadata")
  if a.get("palette") not in PALETTES: raise AssetError(f"{a['id']}: invalid palette")
 return doc
def build(output=DEFAULT_OUT):
 doc=validate_source(json.loads(SOURCE.read_text())); imports=output/"imports/ReplaceableTextures/CommandButtons"; imports.mkdir(parents=True,exist_ok=True)
 rows=[]
 for a in sorted(doc["assets"],key=lambda x:x["id"]):
  p=icon(a); path=imports/f"BTN_AOS_{a['id']}.tga"; path.write_bytes(tga_bytes(p)); m=metrics(downsample(p,32))
  if m["luminanceRange"]<70 or m["borderOpaquePixels"]>124 or path.stat().st_size>doc["style"]["maximumBytes"]: raise AssetError(f"{a['id']}: objective readability threshold failed")
  rows.append({**a,"importPath":f"ReplaceableTextures\\CommandButtons\\BTN_AOS_{a['id']}.tga","source":str(SOURCE.relative_to(ROOT)),"sourceSha256":sha(SOURCE),"derivativeSha256":sha(path),"bytes":path.stat().st_size,"dimensions":[64,64],"channels":"BGRA8","metrics32":m,"license":doc["provenance"]["license"],"attribution":doc["provenance"]["attribution"],"mipmapPolicy":doc["style"]["mipmapPolicy"],"compression":doc["style"]["compression"],"colorSpace":doc["style"]["colorSpace"],"teamColor":doc["style"]["teamColor"]})
 manifest={"format":"warcraft_custom_2d_imports_v1","generatorVersion":1,"sourceSha256":sha(SOURCE),"assets":rows,"remainingWork":doc["remainingWork"]}
 (output/"custom-2d-imports.json").write_text(json.dumps(manifest,indent=2,sort_keys=True)+"\n")
 # SVG contact sheets remain labelled/editable and show both authored and in-game sizes.
 cells=[]
 for i,row in enumerate(rows):
  x=(i%4)*230; y=(i//4)*110; href="imports/"+row["importPath"].replace("\\","/")
  cells.append(f'<image href="{href}" x="{x}" y="{y}" width="64" height="64"/><image href="{href}" x="{x+72}" y="{y}" width="32" height="32"/><text x="{x}" y="{y+82}">{row["id"]}</text><text x="{x+72}" y="{y+49}">32px</text>')
 svg='<svg xmlns="http://www.w3.org/2000/svg" width="920" height="440"><style>text{font:12px sans-serif;fill:#eee}svg{background:#18212a}</style>'+''.join(cells)+'</svg>\n'
 (output/"contact-sheet.svg").write_text(svg)
 return manifest
def main():
 ap=argparse.ArgumentParser(); ap.add_argument("--output",type=Path,default=DEFAULT_OUT); ap.add_argument("--check",action="store_true"); args=ap.parse_args(); first=build(args.output)
 if args.check:
  before={p.relative_to(args.output):sha(p) for p in args.output.rglob("*") if p.is_file()}; second=build(args.output); after={p.relative_to(args.output):sha(p) for p in args.output.rglob("*") if p.is_file()}
  if first!=second or before!=after: raise AssetError("conversion is not deterministic")
 print(f"custom 2D assets: {len(first['assets'])} validated in {args.output}")
if __name__=="__main__": main()
