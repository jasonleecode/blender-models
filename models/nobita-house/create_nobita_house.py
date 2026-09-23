"""Nobi residence: editable, illustrated reconstruction of the pre-2005 plan.
Blender 5.1; all geometry/materials procedural. Dimensions are artistic assumptions.
"""
import bpy, math, random, json, sys
from pathlib import Path
from mathutils import Vector

OUT=Path(__file__).resolve().parent
random.seed(1979)
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
for c in list(bpy.data.collections):bpy.data.collections.remove(c)
scene=bpy.context.scene;scene.name='01 外观 · Exterior'
groups={}
def group(name):
    c=bpy.data.collections.new(name);scene.collection.children.link(c);groups[name]=c;return c
site=group('00 庭院与街道 · Garden')
f1=group('10 一楼地板与家具 · Ground floor')
w1=group('11 一楼上部墙体 · Remove for plan')
stairs=group('18 连通楼梯 · Stairs')
f2=group('20 二楼地板与家具 · Upper floor')
w2=group('21 二楼后墙与隔墙 · Back walls')
cut2=group('22 二楼南东外墙 · Remove for cutaway')
roof=group('30 可拆屋顶 · Roofs')
light=group('90 灯光与相机 · Presentation')
lab1=group('91 一楼户型标注 · Ground labels')
lab2=group('92 二楼户型标注 · Upper labels')
active=site
def mat(name,c,rough=.65,metal=0):
    m=bpy.data.materials.new(name);m.diffuse_color=(*c,1);m.use_nodes=True
    m.node_tree.nodes.clear();p=m.node_tree.nodes.new('ShaderNodeBsdfPrincipled');output=m.node_tree.nodes.new('ShaderNodeOutputMaterial');m.node_tree.links.new(p.outputs['BSDF'],output.inputs['Surface'])
    p.inputs['Base Color'].default_value=(*c,1);p.inputs['Roughness'].default_value=rough;p.inputs['Metallic'].default_value=metal
    return m
cream=mat('Warm butter plaster',(.87,.75,.49));white=mat('Warm porcelain',(.94,.9,.77));wood=mat('Dark cedar trim',(.23,.115,.065));oak=mat('Honey oak',(.59,.33,.13))
red=mat('Vermilion roof',(.52,.07,.045));rededge=mat('Roof raised seams',(.68,.12,.055));glass=mat('Soft blue glazing',(.30,.58,.69),.24,.1)
curtain=mat('Nobita blue curtains',(.075,.40,.71));tatamis=[mat('Tatami straw '+str(i),(.49+i*.027,.56+i*.017,.29+i*.014)) for i in range(4)]
binding=mat('Tatami dark green binding',(.16,.24,.16));pale=mat('Shoji rice paper',(.90,.86,.67));sofa=mat('Ochre upholstery',(.57,.32,.10));pink=mat('Pink zabuton',(.69,.26,.30))
gray=mat('Concrete block wall',(.52,.55,.51));stone=mat('Paving',(.7,.7,.62));grass=mat('Lawn',(.28,.46,.16));earth=mat('Garden cut earth',(.22,.17,.11));black=mat('Charcoal',(.055,.068,.063));steel=mat('Brushed metal',(.47,.53,.5),.3,.55)
blue=mat('Futon blue',(.13,.45,.72));tile=mat('Bathroom mint tile',(.49,.70,.65));road=mat('Street',(.25,.29,.3));paper=mat('Paper',(.96,.94,.83));leaf=[mat('Foliage '+str(i),c) for i,c in enumerate([(.13,.32,.10),(.21,.42,.12),(.31,.51,.18),(.40,.57,.22)])]
bookmats=[mat('Book '+str(i),c) for i,c in enumerate([(.65,.18,.13),(.16,.37,.55),(.73,.61,.19),(.31,.46,.21),(.86,.77,.56)])]
def finish(o,name,m=None,bev=0):
    o.name=name
    for c in list(o.users_collection):c.objects.unlink(o)
    active.objects.link(o)
    if m:o.data.materials.append(m)
    if bev:
        b=o.modifiers.new('Rounded illustrated edges','BEVEL');b.width=bev;b.segments=2
        o.modifiers.new('Weighted normals','WEIGHTED_NORMAL')
    return o
def box(n,p,d,m,bev=.015):
    bpy.ops.mesh.primitive_cube_add(size=1,location=p);o=bpy.context.object;o.dimensions=d;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);return finish(o,n,m,bev)
def cyl(n,p,r,depth,m,verts=16):
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts,radius=r,depth=depth,location=p);return finish(bpy.context.object,n,m,.008)
def ball(n,p,s,m):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=16,ring_count=8,radius=1,location=p);o=bpy.context.object;o.scale=s;return finish(o,n,m)
def beam(n,a,b,width,m):
    a,b=Vector(a),Vector(b);o=box(n,(a+b)/2,(width,width,(b-a).length),m,.008);o.rotation_euler=(b-a).to_track_quat('Z','Y').to_euler();return o
def mesh(n,v,f,m):
    me=bpy.data.meshes.new(n);me.from_pydata(v,[],f);me.update();o=bpy.data.objects.new(n,me);active.objects.link(o);o.data.materials.append(m);return o
fontpath='/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'
font=bpy.data.fonts.load(fontpath) if Path(fontpath).exists() else None
def text(n,t,p,size,m,rot=(0,0,0)):
    d=bpy.data.curves.new(n,'FONT');d.body=t;d.size=size;d.align_x='CENTER';d.extrude=.001
    if font:d.font=font
    o=bpy.data.objects.new(n,d);active.objects.link(o);o.location=p;o.rotation_euler=rot;d.materials.append(m);return o

# Each floor has low walls that remain in the plan, and separately removable tall walls.
def wall(n,a,b,z,height,upper,w=.15):
    global active
    original=active;cx=(a[0]+b[0])/2;cy=(a[1]+b[1])/2
    dx=max(abs(a[0]-b[0]),w);dy=max(abs(a[1]-b[1]),w);low=min(.78,height)
    box(n+' low',(cx,cy,z+low/2),(dx,dy,low),cream)
    if height>low:
        active=upper;box(n+' upper',(cx,cy,z+(low+height)/2),(dx,dy,height-low),cream)
    active=original
def window(n,x,y,z,width=2,height=1.4,side=False,col=None):
    global active
    old=active;active=col or active
    def b(nn,u,v,h,du,dv,dh,m):return box(n+nn,(x+v if side else x+u,y+u if side else y+v,z+h),(dv if side else du,du if side else dv,dh),m,.012)
    b(' blue panes',0,0,0,width,.055,height,glass)
    for u in [-width/2,0,width/2]:b(' mullion',u,-.035,0,.055,.095,height+.12,wood)
    for h in [-height/2,0,height/2]:b(' frame',0,-.035,h,width+.12,.095,.055,wood)
    b(' sill',0,-.08,-height/2-.05,width+.23,.23,.08,oak)
    for sign in [-1,1]:
        for i in range(5):b(' curtain fold',sign*(width/2-.12-i*.05),.047,0,.073,.075,height-.10,curtain)
    active=old
def outside_wall_window(n,a,b,z,h,upper,win_center,ww=2,wh=1.4):
    # axis-aligned wall with a real opening, not glass applied on solid plaster.
    global active
    side=abs(a[0]-b[0])<.01;lo=a[1] if side else a[0];hi=b[1] if side else b[0]
    def p(t):return (a[0],t) if side else (t,a[1])
    wall(n+' left',p(lo),p(win_center-ww/2),z,h,upper);wall(n+' right',p(win_center+ww/2),p(hi),z,h,upper)
    wall(n+' below',p(win_center-ww/2),p(win_center+ww/2),z,.85,upper)
    old=active;active=upper
    p1,p2=p(win_center-ww/2),p(win_center+ww/2)
    box(n+' header',((p1[0]+p2[0])/2,(p1[1]+p2[1])/2,z+(.85+wh+h)/2),(.15 if side else ww,ww if side else .15,h-.85-wh),cream)
    window(n+' window',a[0] if side else win_center,win_center if side else a[1],z+.85+wh/2,ww,wh,side,upper);active=old
def tatami(n,x,y,z,w=3.48,d=3.48):
    # Six mats in a traditional staggered layout, with woven stripes and fabric edges.
    mw=w/2;mh=d/3
    for row in range(3):
        for col in range(2):
            cx=x-w/2+mw*(col+.5);cy=y-d/2+mh*(row+.5)
            box(n+' mat',(cx,cy,z),(mw-.022,mh-.022,.055),random.choice(tatamis),.01)
            for yy in [cy-mh/2+.025,cy+mh/2-.025]:box(n+' border',(cx,yy,z+.032),(mw-.018,.045,.009),binding,0)
            for k in range(14):box(n+' weave',(cx-mw/2+.08+k*(mw-.16)/14,cy,z+.031),(.006,mh-.09,.004),tatamis[0],0)
def table(n,x,y,z,w=1.25,d=.8,h=.72):
    box(n+' top',(x,y,z+h),(w,d,.09),oak,.035)
    for dx in [-w/2+.1,w/2-.1]:
        for dy in [-d/2+.1,d/2-.1]:box(n+' leg',(x+dx,y+dy,z+h/2),(.075,.075,h),wood)
def chair(n,x,y,z,rot=0):
    pieces=[]
    pieces.append(box(n+' seat',(x,y,z+.42),(.48,.48,.09),oak,.035))
    for dx in [-.18,.18]:
        for dy in [-.18,.18]:pieces.append(box(n+' leg',(x+dx,y+dy,z+.2),(.055,.055,.4),wood))
    pieces.append(box(n+' back',(x,y+.22,z+.72),(.48,.055,.5),oak,.03))
    if rot:
        for o in pieces:
            dx,dy=o.location.x-x,o.location.y-y;o.location.x=x+math.cos(rot)*dx-math.sin(rot)*dy;o.location.y=y+math.sin(rot)*dx+math.cos(rot)*dy;o.rotation_euler.z=rot
def gable(n,x0,x1,y0,y1,z,rise):
    yc=(y0+y1)/2
    for edge in [y0,y1]:
        mesh(n+' plane',[(x0,edge,z),(x1,edge,z),(x1,yc,z+rise),(x0,yc,z+rise)],[(0,1,2,3)],red)
        beam(n+' eave',(x0,edge,z),(x1,edge,z),.13,rededge)
        for i in range(int((x1-x0)/.32)+1):
            x=x0+i*(x1-x0)/int((x1-x0)/.32);beam(n+' roof seam',(x,edge,z+.045),(x,yc,z+rise+.045),.035,rededge)
    beam(n+' ridge',(x0-.03,yc,z+rise+.06),(x1+.03,yc,z+rise+.06),.15,rededge)
    for x in [x0,x1]:
        mesh(n+' triangular gable',[(x,y0,z-.06),(x,y1,z-.06),(x,yc,z+rise-.06)],[(0,1,2)],cream)
        for edge in [y0,y1]:beam(n+' bargeboard',(x,edge,z),(x,yc,z+rise),.14,wood)
def shed(n,x0,x1,y0,y1,z0,z1):
    mesh(n,[(x0,y0,z0),(x1,y0,z0),(x1,y1,z1),(x0,y1,z1)],[(0,1,2,3)],red)
    for i in range(int((x1-x0)/.34)+1):
        x=x0+i*(x1-x0)/int((x1-x0)/.34);beam(n+' seam',(x,y0,z0+.04),(x,y1,z1+.04),.035,rededge)
    beam(n+' eave',(x0,y1,z1),(x1,y1,z1),.14,rededge)

# Site: south garden, eastern entrance gate and a quiet street.
active=site
box('Diorama earth',(0,0,-.24),(18.5,14,.55),earth,.18);box('Garden lawn',(0,0,.04),(18.4,13.9,.10),grass,.1)
box('East pavement',(9.4,0,-.08),(1.3,16,.18),stone);box('Residential street',(11.3,0,-.16),(2.5,16,.12),road)
box('South pavement',(0,-7.15,-.08),(20,1.1,.18),stone)
for y in [i*.8-7 for i in range(19)]:box('Pavement joint',(9.4,y,.017),(1.28,.018,.008),gray,0)
def fence(a,b):
    cx=(a[0]+b[0])/2;cy=(a[1]+b[1])/2;dx=abs(a[0]-b[0]);dy=abs(a[1]-b[1]);box('Concrete garden wall',(cx,cy,.68),(max(dx,.18),max(dy,.18),1.3),gray)
    box('Wall cap',(cx,cy,1.37),(max(dx+.1,.25),max(dy+.1,.25),.09),stone)
    for z in [.38,.73,1.08]:beam('Mortar bed',(a[0],a[1]-.096,z),(b[0],b[1]-.096,z),.012,stone)
    length=math.dist(a,b)
    for i in range(int(length/.75)):
        t=(i+.5)*.75/length;x=a[0]+(b[0]-a[0])*t;y=a[1]+(b[1]-a[1])*t
        box('Concrete joint',(x,y-.101,.73),(.011,.013,1.26),stone,0)
fence((-8.7,-6.5),(8.5,-6.5));fence((-8.7,-6.5),(-8.7,6.5));fence((-8.7,6.5),(8.5,6.5));fence((8.5,-6.5),(8.5,2.2));fence((8.5,4.2),(8.5,6.5))
for y in [2.15,4.25]:box('Gate pillar',(8.5,y,.95),(.38,.38,1.9),gray);box('Gate cap',(8.5,y,1.94),(.46,.46,.1),stone)
for y in [2.3+i*.15 for i in range(13)]:box('Wood entrance gate',(8.55,y,.75),(.09,.07,1.2),wood)
for z in [.25,1.17]:box('Gate rail',(8.55,3.2,z),(.10,1.95,.07),wood)
box('Nameplate',(8.72,2.12,1.47),(.035,.30,.5),white)
text('Nobi nameplate','野\n比',(8.749,2.12,1.37),.17,black,(math.pi/2,0,math.pi/2))
box('Mailbox',(8.68,4.23,1.19),(.36,.34,.26),red,.035)
for x in [6.7,7.35,8.0]:box('Entry stepping stone',(x,3.15,.13),(.56,.9,.12),stone,.08)
for i in range(8):box('Garden stepping stone',(5.0-i*.9,-4.4,.11),(.66,.48,.11),stone,.09)
def bush(x,y,z=0,s=1):
    for i in range(5):ball('Shrub foliage',(x+random.uniform(-.45,.45)*s,y+random.uniform(-.35,.35)*s,z+.65*s),(.53*s,.47*s,.56*s),random.choice(leaf))
for x,y,s in [(-7,-4,1.25),(-7,2,1),(6,-5.8,.9),(2,-5.8,.7),(-2,-5.7,.8),(-7,5.5,1.2),(7,5.5,.8)]:bush(x,y,s=s)
for x,y in [(-6.8,-4.5),(-7.0,4.7)]:
    cyl('Garden tree trunk',(x,y,1.5),.16,3,wood)
    for i in range(10):ball('Tree canopy',(x+random.uniform(-.8,.8),y+random.uniform(-.8,.8),3+random.uniform(-.15,1)),(.9,.8,.9),random.choice(leaf))
for y in [-3.0,-2.2,-1.4]:
    cyl('Flower pot',(7.75,y,.24),.21,.4,red);bush(7.75,y,.20,.38)

# Ground floor. Z=.55 finished floor; upstairs Z=3.45.
active=f1;z=.55;H=2.72
for n,x,y,w,d in [('Core',0,-.9,8.4,4.2),('Kitchen',-4.65,3.2,3.1,4),('Wet rooms',.55,2.45,7.3,2.5),('Reception',5.7,.1,3,4.2),('Entry',5.2,3.15,2,1.9)]:
    box(n+' foundation',(x,y,.20),(w,d,.40),gray);box(n+' floor',(x,y,z-.075),(w,d,.15),oak)
tatami('Parents tatami',-2.35,-1.12,z+.035,3.48,3.48);tatami('Living tatami',2.32,-1.12,z+.035,3.48,3.48)
outside_wall_window('Parents south',(-4.2,-3),(-.55,-3),z,H,w1,-2.38,2.5)
outside_wall_window('Living south',(.55,-3),(4.2,-3),z,H,w1,2.35,2.5)
wall('Stair south',(-.55,-3),(.55,-3),z,H,w1)
outside_wall_window('West core',(-4.2,-3),(-4.2,1.2),z,H,w1,-.8,1.7)
outside_wall_window('Reception east',(7.2,-2),(7.2,2.2),z,H,w1,.1,2.5)
wall('Reception south',(4.2,-2),(7.2,-2),z,H,w1);wall('Reception north',(4.2,2.2),(7.2,2.2),z,H,w1)
wall('Kitchen west',(-6.2,1.2),(-6.2,5.2),z,H,w1);outside_wall_window('Kitchen north',(-6.2,5.2),(-3.1,5.2),z,H,w1,-4.65,1.65,1.15)
wall('Kitchen east',(-3.1,3.7),(-3.1,5.2),z,H,w1);wall('Kitchen south',(-6.2,1.2),(-4.2,1.2),z,H,w1)
wall('Service north',(-3.1,3.7),(4.2,3.7),z,H,w1)
for x in [-3.1,-1.0,.65,1.75]:wall('Wet partition',(x,2),(x,3.7),z,H,w1)
for a,b in [(-3.1,-1.8),(-1,.0),(.65,.85)]:wall('Service doorway wall',(a,1.9),(b,1.9),z,H,w1)
wall('Entry north',(4.2,4.1),(6.2,4.1),z,H,w1);wall('Entry east door side',(6.2,3.55),(6.2,4.1),z,H,w1)
wall('Entry east door side2',(6.2,2.2),(6.2,2.55),z,H,w1)
for x in [-.55,.55]:wall('Stair partition',(x,-3),(x,.25),z,H,w1)
for a,b in [(-4.2,-2.4),(-1.4,-.55),(.55,1.1),(2.4,4.2)]:wall('Hall partition',(a,1.2),(b,1.2),z,H,w1)
wall('Reception partition',(4.2,-3),(4.2,.6),z,H,w1)
active=w1
box('Entry door',(6.22,3.07,1.55),(.09,.97,2.0),wood)
for y in [2.74,2.96,3.18,3.4]:box('Entry frosted glass',(6.28,y,1.9),(.04,.15,.95),pale)
beam('Door handle',(6.34,2.7,1.25),(6.34,2.7,1.5),.035,steel)
active=f1;box('Genkan stone lower',(5.75,3.12,.45),(.85,1.55,.10),stone)
box('Shoe cabinet',(4.7,3.8,1.05),(.8,.5,.95),oak)
for yy in [2.8,3.05]:ball('Shoes',(5.8,yy,.54),(.18,.08,.06),black)
# Straight stair actually reaches a matching opening in the upper slab.
active=stairs
for i in range(15):
    y=1.2-(i+.5)*.23;h=(i+1)*(2.9/15)
    box('Stair tread %02d'%i,(0,y,z+h-.055),(1.02,.25,.11),oak)
beam('Stair stringer left',(-.44,1.2,z),(-.44,-2.25,3.45),.12,wood);beam('Stair stringer right',(.44,1.2,z),(.44,-2.25,3.45),.12,wood)
active=f1
# Tatami living room: low table, cushions and a Showa television.
table('Chabudai low table',2.2,-.9,z+.08,1.45,.95,.35)
for x,y in [(2.2,-1.9),(2.2,.15),(3.35,-.9)]:box('Zabuton',(x,y,z+.11),(.65,.65,.13),pink,.12)
cyl('Tea tray',(2.25,-.9,z+.50),.22,.025,wood)
for x in [2.1,2.35]:cyl('Tea cup',(x,-.9,z+.56),.045,.1,white)
box('TV cabinet',(3.67,.6,z+.24),(.7,.68,.48),oak)
box('Retro television',(3.68,.6,z+.78),(.64,.58,.60),wood,.07);box('TV glass',(3.68,.296,z+.8),(.51,.025,.39),black,.07)
beam('TV antenna',(3.68,.6,z+1.1),(3.35,.6,z+1.45),.017,steel)
# Parents' room with bedding, storage and flower alcove.
for x in [-3.2,-1.9]:
    box('Folded futon',(x,-1.0,z+.12),(1.1,1.8,.18),white,.13);box('Futon quilt',(x,-1.3,z+.23),(1.1,1.1,.15),pale,.1);box('Pillow',(x,-.4,z+.28),(.68,.35,.18),white,.09)
# Reception room sofa and coffee table.
box('Reception sofa base',(5.15,.0,z+.29),(.76,2.3,.36),sofa,.09);box('Sofa back',(4.86,0,z+.70),(.2,2.35,.9),sofa,.09)
for y in [-1.1,1.1]:box('Sofa arm',(5.16,y,z+.58),(.8,.18,.58),sofa,.08)
table('Coffee table',6.15,0,z, .65,1.35,.4)
# Kitchen and dining area.
box('Kitchen counter',(-4.65,4.78,z+.44),(2.75,.65,.88),white)
box('Countertop',(-4.65,4.78,z+.93),(2.82,.70,.07),steel)
box('Sink rim',(-4.0,4.78,z+.98),(.76,.51,.045),steel);box('Sink basin',(-4.0,4.78,z+.99),(.61,.37,.045),black)
beam('Tap upright',(-3.8,5.0,z+1),(-3.8,5.0,z+1.29),.035,steel);beam('Tap spout',(-3.8,5.0,z+1.29),(-3.8,4.8,z+1.29),.035,steel)
for x in [-5.3,-4.9]:cyl('Stove burner',(x,4.75,z+1),.14,.025,black)
for x in [-5.6,-4.7,-3.8]:box('Cupboard handle',(x,4.42,z+.61),(.25,.035,.025),wood)
box('Refrigerator',(-5.77,1.85,z+.85),(.70,.75,1.7),white,.06);box('Fridge divider',(-5.77,1.46,z+1.23),(.68,.015,.025),steel)
table('Dining table',-4.50,3.0,z,1.35,.88)
for x in [-4.95,-4.1]:chair('Dining chair',x,2.25,z);chair('Dining chair',x,3.75,z,math.pi)
# Wet rooms; open top tub built from four walls.
box('Bath tile floor',(-2.1,2.8,z+.025),(1.85,1.75,.05),tile)
box('Bath tub bottom',(-2.1,3.15,z+.14),(1.5,.77,.2),white,.07)
for y in [2.72,3.58]:box('Bath tub side',(-2.1,y,z+.37),(1.6,.12,.65),white,.06)
for x in [-2.85,-1.35]:box('Bath tub end',(x,3.15,z+.37),(.12,.8,.65),white,.06)
box('Bath water',(-2.1,3.15,z+.38),(1.4,.69,.025),glass)
box('Washing machine',(-.55,3.1,z+.43),(.65,.65,.85),white,.04);cyl('Washer lid',(-.55,3.1,z+.88),.23,.02,glass)
box('Wash basin stand',(.16,3.1,z+.36),(.48,.6,.72),white);box('Wash basin',(.16,3.1,z+.76),(.53,.65,.13),white,.08)
ball('Toilet bowl',(1.17,3.05,z+.32),(.29,.41,.29),white);box('Toilet cistern',(1.17,3.48,z+.64),(.49,.22,.6),white,.045)

# Upper floor slab leaves the central stairwell open.
active=f2;z2=3.45;H2=2.6
for x in [-2.375,2.375]:box('Upper suspended floor',(x,-.9,z2-.1),(3.65,4.2,.20),oak)
box('Upper landing',(0,-2.6,z2-.1),(1.1,.8,.2),oak)
tatami('Nobita six tatami',2.35,-1.23,z2+.035,3.45,3.24);tatami('Spare six tatami',-2.35,-1.23,z2+.035,3.45,3.24)
outside_wall_window('Nobita south',(.55,-3),(4.2,-3),z2,H2,cut2,2.35,2.25)
outside_wall_window('Spare south',(-4.2,-3),(-.55,-3),z2,H2,cut2,-2.35,2.25)
outside_wall_window('Nobita east',(4.2,-3),(4.2,1.2),z2,H2,cut2,-1.05,2.0)
outside_wall_window('Spare west',(-4.2,-3),(-4.2,1.2),z2,H2,w2,-1.05,1.9)
wall('Upper north',(-4.2,1.2),(4.2,1.2),z2,H2,w2)
wall('Upper stair south',(-.55,-3),(.55,-3),z2,H2,cut2)
for x in [-.55,.55]:wall('Upper hall room partition',(x,-1.65),(x,1.2),z2,H2,w2)
beam('Upper stair rail',(-.48,-2.20,4.3),(-.48,.9,4.3),.065,wood)
for y in [-2.1,-1.5,-.9,-.3,.3,.9]:box('Stair baluster',(-.48,y,3.86),(.045,.045,.83),wood)
# Exposed timber around upper facade.
active=cut2
for x in [-4.25,-.55,.55,4.25]:box('Facade vertical timber',(x,-3.09,4.77),(.095,.10,2.7),wood)
box('Facade floor band',(0,-3.09,3.42),(8.65,.16,.17),wood)
active=f2
# Doraemon's oshiire: one door slid open, pillow and blue bedding on upper shelf.
box('Nobita closet back',(2.0,1.08,4.7),(2.75,.12,2.35),wood)
for x in [.63,3.37]:box('Closet side',(x,.7,4.7),(.12,.86,2.35),oak)
for zc in [3.58,4.68,5.86]:box('Closet shelf',(2.0,.7,zc),(2.8,.85,.1),oak)
box('Closed sliding fusuma',(1.29,.245,4.72),(1.3,.055,2.23),pale)
for x in [.65,1.94]:box('Fusuma edge',(x,.209,4.72),(.045,.05,2.24),wood)
o=cyl('Round fusuma pull',(1.78,.199,4.68),.055,.03,black);o.rotation_euler.x=math.pi/2
box('Doraemon blue futon',(2.67,.68,4.86),(1.15,.67,.24),blue,.11);box('Doraemon pillow',(2.67,.91,5.04),(.65,.25,.13),white,.07)
box('Rolled winter quilt',(2.5,.71,3.86),(1.2,.65,.35),white,.12)
# Built-in closet in spare room.
box('Spare closet',(-2.35,.7,4.65),(3.1,.85,2.4),oak)
for x in [-3.1,-1.58]:box('Spare fusuma',(x,.245,4.68),(1.46,.06,2.22),pale)
# Desk under the south window, with a slightly opened time-machine drawer.
table('Nobita study desk',2.15,-2.49,z2,1.65,.68,.77)
box('Desk drawers',(2.68,-2.49,z2+.38),(.46,.6,.69),oak)
for zz in [z2+.21,z2+.43,z2+.65]:
    box('Drawer face',(2.68,-2.17,zz),(.42,.055,.18),oak);box('Drawer handle',(2.68,-2.13,zz),(.13,.03,.02),wood)
box('Desk open main drawer',(1.87,-2.04,z2+.61),(.74,.49,.13),oak)
box('Drawer interior blue',(1.87,-2.04,z2+.683),(.63,.37,.012),blue)
chair('Nobita desk chair',1.95,-1.55,z2)
box('Homework paper',(1.90,-2.5,z2+.835),(.36,.26,.009),paper)
text('Test score','0',(1.92,-2.51,z2+.847),.12,red)
for i in range(4):box('Desk books',(2.57,-2.66,z2+.84+i*.05),(.28,.25,.045),bookmats[i])
cyl('Pencil holder',(1.48,-2.64,z2+.93),.06,.20,blue)
for i in range(4):beam('Pencil',(1.46+i*.016,-2.64,z2+.92),(1.45+i*.021,-2.64,z2+1.16),.012,bookmats[i])
beam('Desk lamp stalk',(1.58,-2.65,z2+.88),(1.58,-2.65,z2+1.28),.025,wood)
ball('Desk lamp shade',(1.58,-2.60,z2+1.27),(.17,.12,.08),curtain)
# Bookshelf along the east side, facing into the room.
box('Bookshelf back',(4.03,-.85,4.40),(.09,.95,1.78),oak)
for y in [-1.36,-.34]:box('Bookshelf side',(3.84,y,4.4),(.45,.055,1.83),oak)
for zz in [3.53,4.08,4.65,5.24]:box('Bookshelf shelf',(3.84,-.85,zz),(.45,1.08,.065),oak)
for row in range(3):
    for i in range(9):box('Nobita manga',(3.82,-1.27+i*.094,3.59+row*.56+.19),(.33,.068,.36),random.choice(bookmats),.004)
box('Spare room cushion',(-2.35,-1.0,z2+.10),(.65,.65,.15),pink,.09)
table('Spare low writing table',-2.35,-2.1,z2,1.3,.65,.35)

# All roofs removable as a collection. The main roof is red standing-seam metal.
active=roof
gable('Main red roof',-4.65,4.65,-3.48,1.68,6.15,1.35)
shed('Rear service roof',-4.5,4.5,1.25,4.02,3.58,3.10)
gable('Kitchen wing roof',-6.55,-2.90,1.0,5.57,3.38,.82)
gable('Reception wing roof',4.15,7.57,-2.37,2.54,3.27,.70)
gable('Entry porch roof',4.05,6.66,2.13,4.44,3.23,.48)
# Gutters and downpipes, useful to the characteristic silhouette.
active=w1
for x in [-4.35,4.38]:
    beam('Rain downpipe',(x,-3.12,.2),(x,-3.12,3.3),.075,steel)
active=roof;beam('Main gutter',(-4.68,-3.47,6.10),(4.68,-3.47,6.10),.09,wood)
# Simple rooftop aerial.
beam('TV aerial mast',(-3.5,.3,6.6),(-3.5,.3,8.15),.032,steel)
beam('TV aerial boom',(-4.2,.3,8.02),(-2.8,.3,8.02),.025,steel)
for x in [-4,-3.65,-3.3,-2.95]:beam('TV antenna element',(x,-.1,8.02),(x,.7,8.02),.02,steel)

# Plan labels appear only in floor-study scenes; no labels floating in exterior.
active=lab1
for t,x,y in [('父母卧室',-2.35,-2.5),('起居和室',2.35,-2.5),('会客室',5.85,-1.5),('厨房 / 餐厅',-4.6,1.55),('浴室',-2.1,2.08),('洗面',-.25,2.1),('卫生间',1.17,2.0),('玄关',5.05,2.5)]:text('1F label '+t,t,(x,y,z+.13),.19,black)
active=lab2
for t,x,y in [('大雄的房间',2.3,-.5),('和室 / 原奶奶房间',-2.3,-.65),('哆啦A梦的壁橱',2.05,1.36)]:text('2F label '+t,t,(x,y,z2+.13),.20,black)

active=light
world=bpy.data.worlds.new('Warm illustration sky');world.use_nodes=True
world.node_tree.nodes.clear();bg=world.node_tree.nodes.new('ShaderNodeBackground');wo=world.node_tree.nodes.new('ShaderNodeOutputWorld');world.node_tree.links.new(bg.outputs[0],wo.inputs[0]);bg.inputs[0].default_value=(.70,.82,1,1);bg.inputs[1].default_value=.5
def area(n,p,power,size,target):
    d=bpy.data.lights.new(n,'AREA');o=bpy.data.objects.new(n,d);active.objects.link(o);o.location=p;d.energy=power;d.shape='DISK';d.size=size;o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler()
area('Large soft afternoon light',(-7,-9,16),2300,9,(0,0,2));area('Sky fill',(7,3,12),1700,8,(0,0,3))
d=bpy.data.lights.new('Sun','SUN');d.energy=1.8;d.angle=math.radians(18);o=bpy.data.objects.new('Sun',d);light.objects.link(o);o.rotation_euler=(.45,-.6,-.4)
def cam(n,p,target,scale):
    d=bpy.data.cameras.new(n);o=bpy.data.objects.new(n,d);active.objects.link(o);o.location=p;o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler();d.type='ORTHO';d.ortho_scale=scale;return o
hero=cam('Camera exterior',(19,-26,18),(0,.1,2.5),24.5)
groundcam=cam('Camera ground cutaway',(14,-20,23),(0,.8,.7),19)
uppercam=cam('Camera upper cutaway',(11,-16,18),(0,-.9,3.9),12.3)
roomcam=cam('Camera Nobita room',(-1,-10,12),(2.1,-.7,4.5),6.7)
plan1=cam('Camera ground plan',(0,.9,25),(0,.9,0),15)
plan2=cam('Camera upper plan',(0,-.9,24),(0,-.9,0),10)
def config(s,c,excludes,res=(1600,1400)):
    s.camera=c;s.world=world;s.unit_settings.system='METRIC';s.render.engine='CYCLES';s.cycles.samples=32;s.cycles.use_denoising=True
    s.render.resolution_x=res[0];s.render.resolution_y=res[1];s.render.resolution_percentage=100;s.render.image_settings.file_format='PNG'
    s.view_settings.view_transform='AgX';s.render.film_transparent=False
    for ch in s.view_layers[0].layer_collection.children:ch.exclude=ch.name in excludes
    s['reconstruction_note']='Pre-2005 inferred layout; artistic dimensions; not an official production blueprint.'
def newscene(n,c,excluded,res):
    s=bpy.data.scenes.new(n)
    for g in groups.values():s.collection.children.link(g)
    config(s,c,[g.name for g in excluded],res);return s
config(scene,hero,[lab1.name,lab2.name])
s1=newscene('02 一楼拆顶 · Ground cutaway',groundcam,[f2,w2,cut2,roof,w1,lab2],(1600,1400))
s2=newscene('03 二楼拆顶 · Upper cutaway',uppercam,[site,f1,w1,roof,cut2,lab1],(1600,1250))
s3=newscene('04 大雄房间 · Nobita room',roomcam,[site,f1,w1,roof,cut2,w2,lab1,lab2],(1500,1400))
s4=newscene('05 一楼俯视 · Ground plan',plan1,[f2,w2,cut2,roof,w1,lab2,site],(1500,1250))
s5=newscene('06 二楼俯视 · Upper plan',plan2,[site,f1,w1,roof,cut2,w2,lab1],(1500,1000))
for screen in bpy.data.screens:
    for a in screen.areas:
        if a.type=='VIEW_3D':a.spaces.active.region_3d.view_perspective='CAMERA';a.spaces.active.clip_end=200
bpy.context.window.scene=scene
for o in bpy.context.selected_objects:o.select_set(False)
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'大雄家_经典版.blend'),compress=True)
stats={'objects':len(bpy.data.objects),'meshes':len(bpy.data.meshes),'materials':len(bpy.data.materials),'scenes':[s.name for s in bpy.data.scenes],'unit':'metres','ground_floor_level':.55,'upper_floor_level':3.45,'reference':'LIFULL HOMES pre-2005 inferred plan','dimensions_are_assumed':True}
(OUT/'model_info.json').write_text(json.dumps(stats,ensure_ascii=False,indent=2))
for s,name in [(scene,'01_住宅外观'),(s1,'02_一楼拆顶'),(s2,'03_二楼拆顶'),(s3,'04_大雄房间'),(s4,'05_一楼户型'),(s5,'06_二楼户型')]:
    bpy.context.window.scene=s;s.render.filepath=str(OUT/(name+'.png'));bpy.ops.render.render(write_still=True)
bpy.context.window.scene=scene
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'大雄家_经典版.blend'),compress=True)
print('COMPLETE',json.dumps(stats,ensure_ascii=False))
