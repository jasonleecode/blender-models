import bpy
import math
import random
from pathlib import Path
from mathutils import Vector

OUT = Path(__file__).resolve().parent
random.seed(41)
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
for c in list(bpy.data.collections):
    if c.name != 'Collection':
        bpy.data.collections.remove(c)
base = bpy.data.collections.get('Collection')
base.name = '00 • Presentation'
collections = {}
def group(name):
    c = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(c)
    collections[name] = c
    return c
site = group('01 • Forest & ground')
structure = group('02 • Timber structure')
roof = group('03 • Standing seam roof')
glasscol = group('04 • Glazing & frames')
deck = group('05 • Deck & balcony')
lower = group('06 • Ground floor — living & kitchen')
upper = group('07 • Upper floor — bedroom')
stairs = group('08 • Staircase')
lights = group('09 • Lighting')
active = base

def move(obj, col=None):
    for c in list(obj.users_collection): c.objects.unlink(obj)
    (col or active).objects.link(obj)
    return obj

def material(name, color, rough=0.5, metal=0):
    m = bpy.data.materials.new(name)
    m.diffuse_color = (*color, 1)
    m.use_nodes = True
    m.node_tree.nodes.clear()
    p = m.node_tree.nodes.new('ShaderNodeBsdfPrincipled')
    p.name = 'Principled BSDF'
    out = m.node_tree.nodes.new('ShaderNodeOutputMaterial')
    m.node_tree.links.new(p.outputs['BSDF'], out.inputs['Surface'])
    p.inputs['Base Color'].default_value = (*color, 1)
    p.inputs['Roughness'].default_value = rough
    p.inputs['Metallic'].default_value = metal
    return m

def woodmat(name, dark, light):
    m = material(name, light, .44)
    n = m.node_tree.nodes; l = m.node_tree.links
    tc = n.new('ShaderNodeTexCoord')
    mapping = n.new('ShaderNodeVectorMath'); mapping.operation='MULTIPLY'
    mapping.inputs[1].default_value=(4, 48, 5)
    noise=n.new('ShaderNodeTexNoise'); noise.inputs['Scale'].default_value=2.6
    noise.inputs['Detail'].default_value=3
    ramp=n.new('ShaderNodeValToRGB')
    ramp.color_ramp.elements[0].position=.2
    ramp.color_ramp.elements[0].color=(*dark,1)
    ramp.color_ramp.elements[1].position=.8
    ramp.color_ramp.elements[1].color=(*light,1)
    bump=n.new('ShaderNodeBump'); bump.inputs['Strength'].default_value=.14
    bump.inputs['Distance'].default_value=.035
    l.new(tc.outputs['Generated'],mapping.inputs[0]); l.new(mapping.outputs[0],noise.inputs[0])
    l.new(noise.outputs['Fac'],ramp.inputs[0]); l.new(ramp.outputs[0],n.get('Principled BSDF').inputs['Base Color'])
    l.new(noise.outputs['Fac'],bump.inputs['Height']); l.new(bump.outputs[0],n.get('Principled BSDF').inputs['Normal'])
    return m

timber = woodmat('Honey larch | visible grain', (.22,.09,.033),(.62,.34,.135))
plankmats=[woodmat('Cedar plank '+str(i),(.17+.018*i,.075+.009*i,.032),(.39+.035*i,.20+.018*i,.085+.008*i)) for i in range(5)]
oak = woodmat('Interior pale oak', (.36,.22,.11),(.7,.51,.29))
charcoal=material('Graphite zinc roof',(.035,.06,.064),.32,.65)
black=material('Blackened steel',(.018,.025,.027),.29,.7)
stone=material('Warm limestone',(.43,.43,.36),.88)
earth=material('Earth • cut edge',(.115,.09,.062),1)
soil=material('Forest moss',(.135,.18,.105),.98)
cream=material('Linen • ivory',(.81,.77,.64),.95)
sage=material('Upholstery • sage',(.21,.30,.22),.9)
rust=material('Terracotta',(.43,.16,.065),.8)
darkwood=material('Bark',(.13,.075,.035),.95)
pine=[material('Needles '+str(i),c,.92) for i,c in enumerate([(.035,.105,.068),(.055,.155,.098),(.085,.20,.12),(.11,.23,.13)])]
grassmats=[material('Grass '+str(i),c,.95) for i,c in enumerate([(.15,.22,.085),(.23,.30,.12),(.32,.34,.14)])]
glass=material('Clear architectural glazing',(.65,.82,.84),.1)
n=glass.node_tree.nodes; n.clear(); l=glass.node_tree.links
output=n.new('ShaderNodeOutputMaterial'); mix=n.new('ShaderNodeMixShader'); mix.inputs[0].default_value=.065
trans=n.new('ShaderNodeBsdfTransparent'); trans.inputs[0].default_value=(.92,.97,.98,1)
gloss=n.new('ShaderNodeBsdfGlossy'); gloss.inputs['Color'].default_value=(.6,.8,.84,1); gloss.inputs['Roughness'].default_value=.12
l.new(trans.outputs[0],mix.inputs[1]); l.new(gloss.outputs[0],mix.inputs[2]); l.new(mix.outputs[0],output.inputs[0])
emission=material('Warm LED', (1,.53,.15),.4)
p=emission.node_tree.nodes.get('Principled BSDF'); p.inputs['Emission Color'].default_value=(1,.47,.12,1); p.inputs['Emission Strength'].default_value=3

def finish(obj,name,mat,bevel=0,col=None):
    obj.name=name; move(obj,col)
    if mat: obj.data.materials.append(mat)
    if bevel:
        mod=obj.modifiers.new('Soft crafted edges','BEVEL'); mod.width=bevel; mod.segments=2
        mod=obj.modifiers.new('Weighted normals','WEIGHTED_NORMAL')
    return obj

def cube(name,loc,scale,mat,bevel=0,col=None):
    bpy.ops.mesh.primitive_cube_add(size=1,location=loc)
    o=bpy.context.object; o.dimensions=scale
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    return finish(o,name,mat,bevel,col)

def mesh(name,verts,faces,mat,col=None):
    me=bpy.data.meshes.new(name); me.from_pydata(verts,[],faces); me.update()
    o=bpy.data.objects.new(name,me); (col or active).objects.link(o)
    if mat: me.materials.append(mat)
    return o

def beam(name,a,b,width,mat,depth=None,col=None):
    a,b=Vector(a),Vector(b)
    o=cube(name,(a+b)/2,(width,depth or width,(b-a).length),mat,.015,col)
    o.rotation_euler=(b-a).to_track_quat('Z','Y').to_euler()
    return o

def cylinder(name,loc,r,depth,mat,vertices=24,col=None):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices,radius=r,depth=depth,location=loc)
    return finish(bpy.context.object,name,mat,.02,col)

def sphere(name,loc,scale,mat,sub=2,col=None):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=sub,radius=1,location=loc)
    o=bpy.context.object; o.scale=scale
    return finish(o,name,mat,0,col)

def area(name,loc,power,color,size,target):
    d=bpy.data.lights.new(name,'AREA'); d.energy=power; d.color=color; d.shape='DISK'; d.size=size
    o=bpy.data.objects.new(name,d); lights.objects.link(o); o.location=loc
    o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler()
    return o

# A shallow oval slice of woodland, with a finished earthen edge.
active=site
o=cylinder('Woodland island', (0,.5,-.39),12.5,.7,earth,96); o.scale.y=.89
o=cylinder('Moss top', (0,.5,-.035),12.5,.10,soil,96); o.scale.y=.89

# Foundations and timber ground floor at 0.90 m.
active=structure
for x in [-2.8,0,2.8]:
    for y in [-3.4,0,3.4]:
        cube('Concrete pier',(x,y,.36),(.46,.46,.72),stone,.045)
        cube('Steel pier shoe',(x,y,.76),(.5,.5,.13),black,.015)
for x in [-2.8,0,2.8]: cube('Foundation bearer',(x,0,.85),(.21,8,.24),timber,.02)
cube('Ground floor slab',(0,0,.98),(7.1,7.9,.22),oak,.025)
for i in range(32): cube('Ground floor oak boards',(-3.45+i*.22,0,1.104),(.212,7.86,.025),plankmats[(i+2)%5],.005)

# A-frame: 7.6 m span, 7.4 m rise above the deck; clear two-storey interior.
for y in [-4.03,-1.35,1.35,4.03]:
    for side in [-1,1]: beam('Larch A-frame rafter',(side*3.78,y,.91),(0,y,8.34),.23,timber,.28)
    beam('Upper level tie beam',(-2.14,y,4.18),(2.14,y,4.18),.24,timber)
beam('Ridge beam',(0,-4.3,8.32),(0,4.3,8.32),.24,timber)

# Mezzanine with an actual stair opening at the right rear.
cube('Upper floor main slab',(-.50,.10,4.18),(3.14,7.72,.20),oak,.02)
cube('Upper floor over living room',(1.53,-2.02,4.18),(.95,3.48,.20),oak,.02)
for i in range(19):
    x=-2.04+i*.215
    length=7.7 if x<1.0 else 3.46
    y=.10 if x<1.0 else -2.02
    cube('Upper floor boards',(x,y,4.292),(.208,length,.025),oak,.004)

# Rear triangular cedar gable, cut board by board.
for i in range(36):
    x=-3.5+i*.2; top=8.18-abs(x)*1.965
    if top>1.1: cube('Rear cedar cladding',(x,3.96,(top+1.1)/2),(.192,.15,top-1.1),plankmats[i%5],.006)

# Two sloped standing-seam roof surfaces. Right surface includes a real skylight opening.
active=roof
def roofpoint(side,t,y,offset=0): return (side*(3.96*(1-t)+offset), y, .78+7.72*t+offset*.51)
def roofpatch(name,side,t0,t1,y0,y1,mat):
    o=mesh(name,[roofpoint(side,t0,y0),roofpoint(side,t0,y1),roofpoint(side,t1,y1),roofpoint(side,t1,y0)],[(0,1,2,3)],mat)
    sol=o.modifiers.new('Roof thickness','SOLIDIFY'); sol.thickness=.085
    return o
roofpatch('West roof',-1,0,1,-4.4,4.4,charcoal)
roofpatch('East roof • below skylight',1,0,.43,-4.4,4.4,charcoal)
roofpatch('East roof • above skylight',1,.77,1,-4.4,4.4,charcoal)
roofpatch('East roof • front',1,.43,.77,-4.4,-.2,charcoal)
roofpatch('East roof • rear',1,.43,.77,2.25,4.4,charcoal)
roofpatch('Rooflight glass',1,.43,.77,-.2,2.25,glass)
for t in [.43,.77]: beam('Rooflight perimeter',roofpoint(1,t,-.2,.05),roofpoint(1,t,2.25,.05),.10,black)
for y in [-.2,1.025,2.25]: beam('Rooflight cross frame',roofpoint(1,.43,y,.05),roofpoint(1,.77,y,.05),.10,black)
for side in [-1,1]:
    for i in range(19):
        y=-4.38+i*.485
        intervals=[(0,1)] if side<0 or not (-.2<y<2.25) else [(0,.43),(.77,1)]
        for a,b in intervals: beam('Raised roof seam',roofpoint(side,a,y,.035),roofpoint(side,b,y,.035),.027,charcoal)
    beam('Front timber bargeboard',roofpoint(side,0,-4.43),roofpoint(side,1,-4.43),.23,timber,.18)
    beam('Back roof trim',roofpoint(side,0,4.43),roofpoint(side,1,4.43),.12,charcoal)
    beam('Eave gutter',(side*3.98,-4.4,.83),(side*3.98,4.4,.83),.12,charcoal)
beam('Ridge cap',(0,-4.48,8.53),(0,4.48,8.53),.13,charcoal)

# Glazed front gable, ground entrance and upstairs balcony doors.
active=glasscol
mesh('Full height glass gable',[(-3.60,-4.08,1.10),(3.60,-4.08,1.10),(0,-4.08,8.16)],[(0,1,2)],glass)
for side in [-1,1]: beam('Gable edge frame',(side*3.60,-4.11,1.10),(0,-4.11,8.16),.09,black)
for z in [1.12,4.20,6.35]:
    w=(8.16-z)/1.961
    beam('Gable horizontal mullion',(-w,-4.125,z),(w,-4.125,z),.09,black)
for x in [-1.02,1.02]: beam('Gable tall mullion',(x,-4.125,1.12),(x,-4.125,8.16-abs(x)*1.961),.075,black)
beam('Front door transom',(-1.02,-4.15,3.38),(1.02,-4.15,3.38),.075,black)
beam('Entry door center',(0,-4.15,1.12),(0,-4.15,3.38),.065,black)
for x in [-.13,.13]: beam('Bronze entrance handle',(x,-4.23,2.05),(x,-4.23,2.48),.035,timber)
beam('Bedroom door center',(0,-4.15,4.3),(0,-4.15,6.34),.065,black)

# Cedar terrace, three broad approach steps and slim balcony railings.
active=deck
for x in [-3.8,0,3.8]:
    for y in [-6.4,-4.5]: cube('Deck pier',(x,y,.4),(.35,.35,.8),stone,.025)
for i in range(42): cube('Terrace board',(-4.12+i*.20,-5.29,.995),(.19,3.05,.16),plankmats[i%5],.014)
cube('Terrace front fascia',(0,-6.83,.85),(8.45,.15,.30),timber,.02)
for i in range(3):
    z=.19+i*.25; y=-7.88+i*.38
    cube('Approach step',(0,y,z/2),(2.65,.42,z),timber,.025)
    for j in range(2): cube('Step tread',(0,y-.105+j*.21,z+.025),(2.69,.2,.055),plankmats[3],.008)
cube('Upper balcony cantilever',(0,-4.77,4.18),(3.66,1.50,.18),timber,.025)
for i in range(18): cube('Balcony cedar board',(-1.70+i*.2,-4.77,4.29),(.192,1.5,.055),plankmats[i%5],.006)
for x in [-1.82,1.82]:
    beam('Balcony side handrail',(x,-5.50,5.30),(x,-4.06,5.30),.055,black)
    for y in [-5.50,-4.10]: beam('Balcony post',(x,y,4.29),(x,y,5.30),.055,black)
    for y in [-5.3,-5.1,-4.9,-4.7,-4.5,-4.3]: beam('Balcony side spindle',(x,y,4.34),(x,y,5.28),.022,black)
beam('Balcony top handrail',(-1.84,-5.50,5.30),(1.84,-5.50,5.30),.065,timber)
beam('Balcony lower rail',(-1.82,-5.50,4.36),(1.82,-5.50,4.36),.045,black)
for i in range(19): beam('Balcony front spindle',(-1.8+i*.2,-5.50,4.36),(-1.8+i*.2,-5.50,5.29),.022,black)
for side in [-1,1]: beam('Balcony timber brace',(side*1.64,-4.04,3.02),(side*1.64,-5.28,4.10),.13,timber)

# Compact interior: sofa, wool rug, round table, kitchenette and wood stove.
active=lower
cube('Woven wool rug',(-.62,-1.58,1.14),(3.45,2.7,.045),cream,.06)
cube('Sofa oak base',(-2.03,-1.23,1.42),(1.03,2.6,.32),oak,.05)
cube('Sofa back',(-2.48,-1.23,1.98),(.25,2.68,1.02),sage,.11)
for y in [-2.06,-1.23,-.40]: cube('Sofa seat cushion',(-1.96,y,1.72),(.91,.79,.26),sage,.10)
for y in [-2.62,.16]: cube('Sofa arm',(-2.01,y,1.88),(1.10,.19,.72),sage,.06)
for y,mat in [(-1.98,cream),(-.43,rust)]:
    o=cube('Throw pillow',(-2.24,y,2.02),(.23,.57,.52),mat,.1); o.rotation_euler.y=-.18
cylinder('Coffee table top',(-.47,-1.72,1.70),.70,.10,oak,48)
for a in [0,2.094,4.189]: beam('Table leg',(-.47+math.cos(a)*.43,-1.72+math.sin(a)*.43,1.16),(-.47+math.cos(a)*.36,-1.72+math.sin(a)*.36,1.65),.055,black)
cube('Book • terracotta',(-.66,-1.67,1.77),(.40,.28,.045),rust,.008)
cylinder('Ceramic cup',(-.18,-1.9,1.82),.085,.14,cream)
cube('Kitchen cabinets',(-.68,3.37,1.64),(2.92,.78,1.05),sage,.035)
cube('Kitchen stone counter',(-.68,3.37,2.20),(3.03,.88,.095),stone,.025)
for x in [-1.68,-.72,.25]:
    cube('Cabinet door',(x,2.964,1.64),(.88,.045,.93),sage,.012)
    beam('Cabinet handle',(x-.15,2.91,1.97),(x+.15,2.91,1.97),.025,black)
cube('Induction hob',(-1.48,3.30,2.259),(.73,.53,.024),black,.015)
cylinder('Sink',(.10,3.35,2.258),.27,.022,black,36)
beam('Faucet',(.10,3.69,2.23),(.10,3.69,2.62),.04,black)
beam('Faucet spout',(.10,3.69,2.62),(.10,3.42,2.62),.04,black)
cube('Rear kitchen shelf',(-.7,3.66,2.92),(2.85,.45,.10),oak,.018)
for i in range(5): cylinder('Shelf jar',(-1.75+i*.32,3.61,3.10),.095,.24,cream if i%2 else rust)
cylinder('Stove hearth',(2.30,-2.16,1.16),.60,.08,stone,40)
cube('Wood stove',(2.30,-2.16,1.68),(.69,.60,.83),black,.045)
cube('Stove glass',(2.30,-2.472,1.69),(.49,.018,.47),charcoal,.02)
for i in range(3): beam('Firewood ember',(2.13+i*.13,-2.49,1.48),(2.19+i*.13,-2.49,1.66),.038,emission)
cylinder('Stove flue',(2.30,-2.16,3.06),.085,1.97,black)
cylinder('Stove exterior chimney',(2.30,-2.16,4.98),.105,1.91,black,col=roof)
cylinder('Chimney rain cap',(2.30,-2.16,5.99),.18,.09,black,col=roof)

# Seventeen timber treads connect both floors through the right-hand opening.
active=stairs
for i in range(17):
    y=-.80+i*.255; z=1.10+(i+1)*3.2/17
    cube('Stair tread %02d'%(i+1),(1.52,y,z-.045),(.97,.275,.09),oak,.013)
    if i%2==0: beam('Stair baluster',(1.04,y,z),(1.04,y,z+.90),.025,black)
for x in [1.12,1.94]: beam('Steel stair stringer',(x,-.93,1.12),(x,3.39,4.19),.105,black)
beam('Stair handrail',(1.04,-.80,2.19),(1.04,3.28,5.20),.055,timber)
beam('Landing guard',(1.03,-.28,5.24),(1.03,2.96,5.24),.05,black)
for i in range(14): beam('Landing spindle',(1.03,-.28+i*.24,4.31),(1.03,-.28+i*.24,5.24),.023,black)

# Loft bedroom fully modelled behind the balcony doors.
active=upper
cube('Bedroom woven rug',(-.28,-.25,4.33),(2.46,3.4,.035),cream,.05)
cube('Oak bed frame',(-.30,.08,4.51),(1.85,2.35,.30),oak,.045)
cube('Mattress',(-.30,.01,4.79),(1.79,2.22,.27),cream,.13)
cube('Duvet',(-.30,-.33,4.95),(1.82,1.64,.19),cream,.12)
cube('Forest green bed throw',(-.30,-.79,5.05),(1.84,.62,.065),sage,.035)
cube('Timber headboard',(-.30,1.21,4.99),(1.96,.13,1.12),timber,.035)
for x in [-.76,.15]: cube('Bed pillow',(x,.73,5.015),(.73,.48,.17),cream,.1)
cylinder('Bedside table',(-1.59,.96,4.67),.29,.69,timber)
cylinder('Bedside ceramic lamp',(-1.59,.96,5.11),.12,.22,rust)
bpy.ops.mesh.primitive_cone_add(vertices=32,radius1=.22,radius2=.15,depth=.26,location=(-1.59,.96,5.33))
finish(bpy.context.object,'Linen lamp shade',cream)
cube('Bedroom rear storage',(-.5,3.59,4.81),(2.85,.53,1.03),oak,.025)

# Outdoor lounge chairs with slatted backs and a small table.
active=deck
def chair(x,y):
    for dx in [-.30,.30]:
        beam('Chair front leg',(x+dx,y-.26,1.08),(x+dx,y-.26,1.56),.045,black)
        beam('Chair back leg',(x+dx,y+.25,1.08),(x+dx,y+.25,1.56),.045,black)
    cube('Outdoor chair seat',(x,y,1.56),(.71,.69,.10),timber,.03)
    for i in range(5):
        o=cube('Slatted chair back',(x-.28+i*.14,y+.31,1.96),(.115,.07,.74),timber,.018); o.rotation_euler.x=-.17
    cube('Outdoor linen seat pad',(x,y-.01,1.64),(.60,.59,.09),cream,.035)
chair(-2.62,-5.34); chair(2.80,-5.38)
cylinder('Deck side table',(-3.47,-5.5,1.54),.32,.09,timber)
cylinder('Table pedestal',(-3.47,-5.5,1.29),.045,.45,black)

def plant(x,y,z,scale=1):
    cylinder('Terracotta planter',(x,y,z+.23*scale),.25*scale,.46*scale,rust)
    for i in range(11):
        a=random.random()*math.tau
        tip=(x+math.cos(a)*random.uniform(.2,.40)*scale,y+math.sin(a)*random.uniform(.2,.40)*scale,z+random.uniform(.65,1.1)*scale)
        beam('Plant stem',(x,y,z+.40*scale),tip,.015*scale,pine[2])
        sphere('Plant leaves',tip,(.10*scale,.15*scale,.23*scale),pine[i%4],1)
plant(3.65,-4.67,1.09,.9); plant(-1.46,-4.78,4.32,.55)

# Forest trees: layered, irregular silhouettes; clear front sightline to the cabin.
active=site
def tree(x,y,h,r):
    cylinder('Pine trunk',(x,y,h*.40),.13*h/7,h*.8,darkwood,12)
    for j in range(7):
        z=h*(.24+j*.091); rad=r*(1-j*.105); height=h*.32
        verts=[]; N=15
        for k in range(N):
            a=k*math.tau/N; rr=rad*random.uniform(.78,1.13)
            verts.append((x+math.cos(a)*rr,y+math.sin(a)*rr,z+random.uniform(-.17,.17)))
        verts.append((x+random.uniform(-.1,.1),y+random.uniform(-.1,.1),z+height))
        faces=[(k,(k+1)%N,N) for k in range(N)]; faces.append(tuple(reversed(range(N))))
        mesh('Pine needle crown',verts,faces,pine[(j+int(x*2))%4])
    for j in range(5):
        a=random.random()*math.tau; z=h*(.25+j*.095)
        beam('Pine branch',(x,y,z+.25),(x+math.cos(a)*r*.8,y+math.sin(a)*r*.8,z),.055,darkwood)
positions=[(-7,2,8.8,1.7),(-8,5,10.4,1.9),(-5.4,6.8,9.5,1.8),(-2.5,8.4,10.6,1.7),(1,8.8,9.3,1.9),(4.6,7.4,10.3,1.75),(7,5.8,9.0,1.75),(8.3,2.5,8.5,1.65),(-8,-1.8,7.6,1.65),(-9.3,-4.2,6.0,1.5),(9,0,6.4,1.4),(-5.8,3.7,7.3,1.35),(5.8,4.2,7.5,1.5),(-9,1.1,5.4,1.3),(6.5,8.0,6.5,1.3),(-4.1,9.2,7,1.3)]
for args in positions: tree(*args)

# Random mossy rocks, woodland tufts, and stepping stones.
for i in range(37):
    a=random.uniform(0,math.tau); r=random.uniform(8.5,11.6)
    x,y=math.cos(a)*r,.5+math.sin(a)*r*.87
    s=random.uniform(.16,.52)
    o=sphere('Weathered woodland stone',(x,y,s*.38),(s,s*.72,s*.60),stone,2); o.rotation_euler.z=a
for i in range(7):
    y=-8.22-i*.43; x=math.sin(i*.7)*.30
    o=cylinder('Stone path',(x,y,.065),.51,.13,stone,7); o.scale=(1,.56,1); o.rotation_euler.z=random.uniform(-.2,.2)
verts=[]; faces=[]; indices=[]
for i in range(1850):
    x=random.uniform(-11.9,11.9); y=random.uniform(-10.3,11.0)
    if x*x/12**2+(y-.5)**2/10.5**2>1: continue
    if abs(x)<4.65 and -7.0<y<4.7: continue
    if abs(x)<1.05 and y<-6: continue
    for j in range(3):
        a=random.random()*math.tau; w=random.uniform(.025,.055); h=random.uniform(.14,.40)
        dx,dy=math.cos(a)*w,math.sin(a)*w; k=len(verts)
        verts.extend([(x-dx,y-dy,.025),(x+dx,y+dy,.025),(x+math.cos(a+.9)*h*.35,y+math.sin(a+.9)*h*.35,h)])
        faces.append((k,k+1,k+2)); indices.append(random.randrange(3))
o=mesh('Wild forest grasses',verts,faces,None)
for m in grassmats: o.data.materials.append(m)
for p,idx in zip(o.data.polygons,indices): p.material_index=idx

# Path bollards and warm practical lighting.
for x,y in [(-1.9,-7.4),(1.6,-9.1)]:
    cube('Path light post',(x,y,.34),(.10,.10,.66),black,.015)
    cube('Path light lens',(x,y,.62),(.12,.12,.10),emission,.015)
    area('Path warm light',(x,y,.65),12,(1,.58,.27),.4,(x,y,0))
area('Living room warm pool',(0,-.9,3.80),220,(1,.69,.39),3.3,(0,-1.1,1.1))
area('Kitchen warm light',(-.6,2.9,3.75),95,(1,.77,.52),1.5,(-.6,3,1.2))
area('Bedroom warm light',(0,-.3,6.95),160,(1,.73,.45),2,(0,-.1,4.3))
area('Facade soft fill',(1,-10,7),650,(.72,.83,1),7,(0,-2,3))
area('Large softbox',(-7,-9,16),2200,(1,.86,.65),9,(0,0,0))
area('Forest rim',(1,8,15),2400,(1,.82,.56),7,(0,1,3))
for x in [-1.7,1.7]: beam('Warm underside balcony strip',(x,-5.37,4.065),(x,-4.17,4.065),.022,emission,col=deck)

# Neutral studio ground gives the woodland slice a clean presentation edge.
active=base
backdrop=material('Backdrop • mist',(.24,.30,.29),.93)
cube('Studio ground',(0,0,-.81),(200,200,.1),backdrop)
world=bpy.data.worlds.new('Soft blue forest daylight'); bpy.context.scene.world=world
world.use_nodes=True; world.node_tree.nodes.clear()
bg=world.node_tree.nodes.new('ShaderNodeBackground'); wo=world.node_tree.nodes.new('ShaderNodeOutputWorld')
world.node_tree.links.new(bg.outputs[0],wo.inputs[0])
bg.inputs[0].default_value=(.43,.56,.64,1)
bg.inputs[1].default_value=.42
sun_data=bpy.data.lights.new('Late afternoon sun','SUN'); sun_data.energy=1.6; sun_data.angle=.20; sun_data.color=(1,.86,.65)
sun=bpy.data.objects.new('Late afternoon sun',sun_data); lights.objects.link(sun); sun.rotation_euler=(.40,-.48,-.42)

def camera(name,loc,target,scale):
    d=bpy.data.cameras.new(name); o=bpy.data.objects.new(name,d); base.objects.link(o)
    o.location=loc; o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler()
    d.type='ORTHO'; d.ortho_scale=scale; d.lens=48
    return o
hero=camera('Camera • woodland exterior',(16,-24,15.0),(0,.1,3.4),27.2)
detail=camera('Camera • architecture',(10,-20,10.8),(0,-.5,3.9),16.9)
section=camera('Camera • interior cutaway',(11,-17,12),(0,-.05,3.6),15.5)
scene=bpy.context.scene; scene.camera=hero
scene.render.engine='CYCLES'; scene.cycles.samples=40; scene.cycles.use_denoising=True
scene.cycles.max_bounces=8; scene.cycles.transparent_max_bounces=12
scene.render.resolution_x=1500; scene.render.resolution_y=1400; scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG'
scene.view_settings.view_transform='AgX'
scene.render.film_transparent=False
scene.unit_settings.system='METRIC'; scene.unit_settings.length_unit='METERS'
scene['Design']='PINE / 02 — two-storey woodland A-frame cabin'
scene['Levels']='Ground floor +1.10 m; upper floor +4.30 m; ridge +8.53 m'
scene['Contents']='Living room, kitchenette, wood stove, 17-step staircase, loft bedroom, balcony, deck, woodland'
scene['Note']='Concept visualization. Collections are separated for editing; all materials are procedural and packed in this file.'
for screen in bpy.data.screens:
    for a in screen.areas:
        if a.type=='VIEW_3D':
            a.spaces.active.region_3d.view_perspective='CAMERA'
            a.spaces.active.shading.type='MATERIAL'
            a.spaces.active.overlay.show_overlays=False
bpy.ops.object.select_all(action='DESELECT')
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'林间三角屋.blend'))
scene.render.filepath=str(OUT/'林间三角屋_全景.png')
bpy.ops.render.render(write_still=True)
scene.camera=detail
scene.render.resolution_x=1500; scene.render.resolution_y=1500
scene.render.filepath=str(OUT/'林间三角屋_建筑特写.png')
bpy.ops.render.render(write_still=True)
# The cutaway is a separate view only; saved master retains all exterior elements.
for c in [roof,glasscol,site]: c.hide_render=True
for o in structure.objects:
    if 'Rear cedar' in o.name: o.hide_render=True
scene.camera=section
scene.render.filepath=str(OUT/'林间三角屋_两层剖视.png')
bpy.ops.render.render(write_still=True)
print('FINISHED: model and three rendered views written to',OUT)
