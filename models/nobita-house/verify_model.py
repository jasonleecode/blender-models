"""Open the saved model in Blender, check structure and pack the label font."""
import bpy,json
from pathlib import Path
r=Path(__file__).resolve().parent
assert len(bpy.data.scenes)==6
assert len(bpy.data.objects)>1000
for s in bpy.data.scenes:
    assert s.camera is not None
    assert s.camera.type=='CAMERA'
    assert not s.view_layers[0].layer_collection.children['90 灯光与相机 · Presentation'].exclude
assert any('Closet shelf' in o.name for o in bpy.data.objects)
assert sum(o.name.startswith('Stair tread') for o in bpy.data.objects)==15
treads=sorted([o for o in bpy.data.objects if o.name.startswith('Stair tread')],key=lambda o:o.location.z)
assert treads[0].location.y>treads[-1].location.y
assert abs(treads[-1].location.z+treads[-1].dimensions.z/2-3.45)<.001
landing=bpy.data.objects['Upper landing']
assert landing.location.y+landing.dimensions.y/2>=treads[-1].location.y-treads[-1].dimensions.y/2
floors=[bpy.data.objects[n+' floor'] for n in ['Core','Kitchen','Wet rooms','Reception','Entry']]
for i,a in enumerate(floors):
    for b in floors[i+1:]:
        overlap=[min(a.location[k]+a.dimensions[k]/2,b.location[k]+b.dimensions[k]/2)-max(a.location[k]-a.dimensions[k]/2,b.location[k]-b.dimensions[k]/2) for k in (0,1)]
        assert min(overlap)<.001,(a.name,b.name,'overlapping top surfaces')
bad=[o.name for o in bpy.data.objects if o.type=='MESH' and (len(o.data.vertices)==0 or min(o.dimensions)<0)]
assert not bad,bad
for n in ['01_住宅外观','02_一楼拆顶','03_二楼拆顶','04_大雄房间','05_一楼户型','06_二楼户型']:
    assert (r/(n+'.png')).stat().st_size>10000,n
bpy.context.window.scene=bpy.data.scenes['01 外观 · Exterior']
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=str(r/'大雄家_经典版.blend'),compress=True)
report=dict(status='PASS',blender=bpy.app.version_string,scenes=6,objects=len(bpy.data.objects),renders=6,font_packed=all(f.packed_file is not None for f in bpy.data.fonts if f.filepath and f.filepath!='<builtin>'))
(r/'verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print(report)
