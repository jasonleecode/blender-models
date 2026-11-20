"""Rebuild with Blender 5.1: blender -b -P create_scene.py"""
import bpy
import math
import random
from math import sin, cos, pi, exp, sqrt
from pathlib import Path
from mathutils import Vector, noise

ROOT = Path(__file__).resolve().parent
rng = random.Random(201120)
U = rng.uniform
V = Vector
Z = V((0,0,1))
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
def collection(name):
    c = bpy.data.collections.new(name)
    scene.collection.children.link(c)
    return c

house=collection('01 · 原木小屋 | Cabin')
roof=collection('02 · 木瓦与烟囱 | Roof')
deck=collection('03 · 门廊与柴垛 | Porch')
camp=collection('04 · 林间营地 | Camp')
land=collection('05 · 溪岸与落叶 | Clearing')
water=collection('06 · 溪水与卵石 | Brook')
woods=collection('07 · 秋林 | Woodland')
air=collection('08 · 烟与光 | Atmosphere')
def srgb(v):
    return ((v+.055)/1.055)**2.4 if v>.04045 else v/12.92
def rgb(h):
    return tuple(srgb(int(h[i:i+2],16)/255) for i in (0,2,4))
def material(name, h, rough=.72, metal=0, emit=0):
    m=bpy.data.materials.new(name)
    col=rgb(h); m.diffuse_color=(*col,1); m.use_nodes=True
    p=m.node_tree.nodes.get('Principled BSDF')
    p.inputs['Base Color'].default_value=(*col,1)
    p.inputs['Roughness'].default_value=rough
    p.inputs['Metallic'].default_value=metal
    if emit:
        p.inputs['Emission Color'].default_value=(*col,1)
        p.inputs['Emission Strength'].default_value=emit
    return m
def node(m,typ):
    return m.node_tree.nodes.new(typ)
def link(m,a,b):
    m.node_tree.links.new(a,b)
def ramp(m,entries):
    r=node(m,'ShaderNodeValToRGB')
    for i,(pos,h) in enumerate(entries):
        e=r.color_ramp.elements[i] if i<2 else r.color_ramp.elements.new(pos)
        e.position=pos; e.color=(*rgb(h),1)
    return r
def texture(m,vec,scale,detail=3,distort=0):
    n=node(m,'ShaderNodeTexNoise'); n.inputs['Scale'].default_value=scale
    n.inputs['Detail'].default_value=detail; n.inputs['Distortion'].default_value=distort
    link(m,vec,n.inputs['Vector'])
    return n.outputs['Fac']
def grain(name,h1,h2,stretch=(1,1,1),scale=3,rough=.75,bump=.035,coord='Object'):
    m=material(name,h1,rough); p=m.node_tree.nodes.get('Principled BSDF')
    t=node(m,'ShaderNodeTexCoord'); v=node(m,'ShaderNodeVectorMath');v.operation='MULTIPLY'
    link(m,t.outputs[coord],v.inputs[0]); v.inputs[1].default_value=stretch
    n=texture(m,v.outputs[0],scale,4,.25); r=ramp(m,[(.2,h1),(.8,h2)])
    link(m,n,r.inputs[0]);link(m,r.outputs[0],p.inputs['Base Color'])
    b=node(m,'ShaderNodeBump'); b.inputs['Strength'].default_value=.23;b.inputs['Distance'].default_value=bump
    link(m,n,b.inputs['Height']);link(m,b.outputs[0],p.inputs['Normal'])
    return m
# Batch small repeated elements into editable meshes by assembly.
class Geometry:
    def __init__(self):
        self.v=[]; self.f=[]; self.mi=[]; self.mats=[]; self.lookup={}
    def part(self,verts,faces,mat):
        if mat not in self.lookup:
            self.lookup[mat]=len(self.mats);self.mats.append(mat)
        start=len(self.v);idx=self.lookup[mat]; self.v.extend(verts)
        self.f.extend(tuple(start+i for i in face) for face in faces)
        self.mi.extend([idx]*len(faces))
    def box(self,center,size,mat,axes=None):
        x,y,z=(V((1,0,0)),V((0,1,0)),Z) if axes is None else axes
        x=x*size[0]/2;y=y*size[1]/2;z=z*size[2]/2;c=V(center)
        self.part([c-x-y-z,c+x-y-z,c+x+y-z,c-x+y-z,c-x-y+z,c+x-y+z,c+x+y+z,c-x+y+z],
                  [(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)],mat)
    def tube(self,a,b,r1,r2,mat,n=8,end=None):
        a=V(a); b=V(b);d=(b-a).normalized()
        side=(d.cross(Z) if abs(d.z)<.95 else d.cross(V((1,0,0)))).normalized()
        side2=d.cross(side)
        ring=[side*cos(i*2*pi/n)+side2*sin(i*2*pi/n) for i in range(n)]
        self.part([a+p*r1 for p in ring]+[b+p*r2 for p in ring],
                  [(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)],mat)
        self.part([a+p*r1 for p in ring],[tuple(reversed(range(n)))],end or mat)
        self.part([b+p*r2 for p in ring],[tuple(range(n))],end or mat)
    def obj(self,name,col,smooth=False):
        me=bpy.data.meshes.new(name); me.from_pydata(self.v,[],self.f);me.update()
        for m in self.mats: me.materials.append(m)
        me.polygons.foreach_set('material_index',self.mi)
        if smooth: me.polygons.foreach_set('use_smooth',[True]*len(self.f))
        o=bpy.data.objects.new(name,me);col.objects.link(o)
        return o
# Match portrait photograph, using image coordinates in a 963 by 1000 frame.
C=V((12.31825,-18.88160,5.934)); R=V((.837526,.546397,0)); F=V((-.546397,.837526,0))
pitch=.313166;FWD=F*cos(pitch)-Z*sin(pitch); UP=F*sin(pitch)+Z*cos(pitch)
foc=692.265; cx=497.56
def plane(px,py,z):
    ray=FWD+R*((px-cx)/foc)+UP*((500-py)/foc)
    return C+ray*((z-C.z)/ray.z)
def sd(x,y):
    dx=x-C.x;dy=y-C.y
    return dx*R.x+dy*R.y,dx*F.x+dy*F.y
def xy(s,d):
    return C+R*s+F*d
def project(x,y,z):
    v=V((x,y,z))-C
    return cx+foc*v.dot(R)/v.dot(FWD),500-foc*v.dot(UP)/v.dot(FWD)
def interpol(a,pts):
    for (x,y),(xx,yy) in zip(pts,pts[1:]):
        if a<xx:return y+(yy-y)*(a-x)/(xx-x)
    return pts[-1][1]+(a-pts[-1][0])*.5
def shore(s):
    return -.39+.30*ease((s-2)/5)+interpol(s,[(-20,-.5),(-5.37,5.5),(-2.3,7.07),(-.25,7.9),(1.8,8.55),(3.6,9),(4.9,9.6),(6.2,10.84),(10,13.28),(25,22)])+.15*sin(s*2)+.085*sin(4.3*s)
def sat(x):return max(0,min(1,x))
def ease(x):
    x=sat(x);return x*x*(3-2*x)
def nval(x,y):
    return noise.noise_vector((x,y,1.67)).x
def ground(x,y):
    s,d=sd(x,y);b=d-shore(s)
    bed=-1.49-.48*ease(-b*.65)+.10*nval(x*1.3,y*1.3)
    clearing=-.63+.65*ease((d-12)/9)+.08*sin(x*.9)*sin(y*.7)
    clearing+=.32*ease((abs(s)-5)/4)+max(0,d-28)*.074+max(0,d-41)*.40+.23*nval(x*.4,y*.4)
    return bed+(clearing-bed)*ease((b+.34)/2.35)+.047*nval(3*x,3*y)
def at(px,py):
    ray=FWD+R*((px-cx)/foc)+UP*((500-py)/foc)
    lo=0.0;hi=.5
    while hi<125:
        p=C+ray*hi
        if p.z<=ground(p.x,p.y):break
        lo=hi;hi+=.5
    for _ in range(20):
        mid=(lo+hi)*.5;p=C+ray*mid
        if p.z>ground(p.x,p.y):lo=mid
        else:hi=mid
    p=C+ray*hi
    return V((p.x,p.y,ground(p.x,p.y)))
cam_data=bpy.data.cameras.new('Reference portrait');camera=bpy.data.objects.new('参考图机位',cam_data)
air.objects.link(camera);camera.location=C;camera.rotation_euler=FWD.to_track_quat('-Z','Y').to_euler()
cam_data.sensor_fit='HORIZONTAL';cam_data.lens=36*foc/963;cam_data.shift_x=(481.5-cx)/963
scene.camera=camera
# Timber textures follow the grain in each wall.
endwood=grain('Log ends · growth rings','7d563b','aa8053',(6,6,6),6)
logs={}
for axis,stretch in [('X',(.4,12,12)),('Y',(12,.4,12)),('Z',(11,11,.45))]:
    logs[axis]=[grain('Cedar '+axis+' '+str(j),a,b,stretch,2.2) for j,(a,b) in enumerate([
        ('412b24','956348'),('503428','a47250'),('422d29','84573d'),('604130','a9754f')])]
trim=grain('Oiled walnut trim','34251f','6f4b38',(3,3,6),2)
trimlight=grain('Weathered porch cedar','584338','a18a76',(2,10,3),3)
dark=material('Deep frame shadows','231e1b')
iron=material('Charcoal iron','303135',.46,.65)
glassdark=grain('Smoky reflected panes','302d30','7d6249',(1,1,2),2,.24,.001)
glow=[material('Window amber '+str(i),h,.35,0,e) for i,(h,e) in enumerate([('ffb45c',.8),('f4943f',.95),('ffd081',1.2),('bc7846',.32)])]
stone=[grain('Creek stone '+str(i),a,b,(1.4,1.1,1.8),4,.60,.04) for i,(a,b) in enumerate([
('4f5355','9ca5a9'),('777a7b','bbc2c2'),('76635a','b49b8b'),('685852','ab8078'),('475559','829393'),('5c5b4d','999780'),('715e59','c6a491'),('4d4842','827d71')])]
# Mixed mineral bands and sunlit ripple patterns on submerged stones.
for m in stone:
    p=m.node_tree.nodes.get('Principled BSDF');base=p.inputs['Base Color'].links[0].from_socket
    tc=node(m,'ShaderNodeTexCoord').outputs['Object']
    tex=texture(m,tc,9,4,.85);mineral=ramp(m,[(.27,'615960'),(.52,'bdac9c'),(.68,'e9d9c6')])
    link(m,tex,mineral.inputs[0]);mx=node(m,'ShaderNodeMixRGB');mx.blend_type='OVERLAY';mx.inputs[0].default_value=.47
    link(m,base,mx.inputs[1]);link(m,mineral.outputs[0],mx.inputs[2])
    geom=node(m,'ShaderNodeNewGeometry');sep=node(m,'ShaderNodeSeparateXYZ');link(m,geom.outputs['Position'],sep.inputs[0])
    wet=node(m,'ShaderNodeMath');wet.operation='LESS_THAN';wet.inputs[1].default_value=-1.38;link(m,sep.outputs['Z'],wet.inputs[0])
    rough=node(m,'ShaderNodeMath');rough.operation='MULTIPLY_ADD';rough.inputs[1].default_value=-.35;rough.inputs[2].default_value=.64
    link(m,wet.outputs[0],rough.inputs[0]);link(m,rough.outputs[0],p.inputs['Roughness'])
    distort=node(m,'ShaderNodeTexNoise');distort.inputs['Scale'].default_value=4;link(m,tc,distort.inputs['Vector'])
    add=node(m,'ShaderNodeVectorMath');add.operation='SCALE';add.inputs['Scale'].default_value=.19;link(m,distort.outputs['Color'],add.inputs[0])
    uv=node(m,'ShaderNodeVectorMath');uv.operation='ADD';link(m,add.outputs[0],uv.inputs[0]);link(m,tc,uv.inputs[1])
    vor=node(m,'ShaderNodeTexVoronoi');vor.feature='DISTANCE_TO_EDGE';vor.voronoi_dimensions='2D';vor.inputs['Scale'].default_value=5;link(m,uv.outputs[0],vor.inputs['Vector'])
    ca=ramp(m,[(.015,'ffde8c'),(.082,'504332')]);link(m,vor.outputs['Distance'],ca.inputs[0])
    tint=node(m,'ShaderNodeMixRGB');tint.blend_type='OVERLAY';strength=node(m,'ShaderNodeMath');strength.operation='MULTIPLY';strength.inputs[1].default_value=.23
    link(m,wet.outputs[0],strength.inputs[0]);link(m,strength.outputs[0],tint.inputs[0]);link(m,mx.outputs[0],tint.inputs[1]);link(m,ca.outputs[0],tint.inputs[2])
    link(m,tint.outputs[0],p.inputs['Base Color'])
def peb(g,c,sc,mat,rseed=0):
    c=V(c);rx,ry,rz=sc;ang=U(0,pi);ca,sa=cos(ang),sin(ang)
    verts=[c+V((0,0,-rz*.85))];n=9
    phase=U(0,.3)
    for j,(z,rad) in enumerate([(-.62,.73),(-.04,1),(.61,.79)]):
        for k in range(n):
            a=2*pi*k/n+phase+.11*(j%2);rr=rad*U(.85,1.12)
            x=cos(a)*rr*rx;y=sin(a)*rr*ry
            verts.append(c+V((ca*x-sa*y,sa*x+ca*y,(z+U(-.10,.10))*rz)))
    verts.append(c+V((rx*.06,-ry*.09,rz*.93)))
    faces=[(0,1+(i+1)%n,1+i) for i in range(n)]
    for j in range(2):
        faces.extend((1+j*n+i,1+j*n+(i+1)%n,1+(j+1)*n+(i+1)%n,1+(j+1)*n+i) for i in range(n))
    faces.extend((1+2*n+i,1+2*n+(i+1)%n,len(verts)-1) for i in range(n))
    g.part(verts,faces,mat)
g=Geometry()
for x in [-3,0,3]:
    for y in [0,3.4,6.9,10.2,-1.7]:
        for j in range(3):
            peb(g,(x+U(-.05,.05),y+U(-.06,.06),.13+j*.31),(.40,.38,.21),rng.choice(stone))
for i in range(37):
    y=-.12+i*.286;x=3.12+U(-.08,.08)
    for j in range(rng.choice([1,2,2,3])):
        peb(g,(x,y+U(-.09,.09),.14+j*.18),(.25,U(.19,.34),U(.13,.20)),rng.choice(stone))
g.obj('Dry-laid fieldstone piers',house,True)
g=Geometry();g.box((0,5.1,.93),(6.42,10.35,.25),trim);g.obj('Raised sill',house)
# Wall courses stop at the door and window openings.
frontwin=[(-2.45,-.97,1.56,2.88),(-.61,.40,1.04,2.94),(.74,2.5,1.53,2.9)]
sidewin=[(1.10,2.8,1.62,2.92),(8.85,9.75,1.65,2.85)]
def segments(lo,hi,openings,z):
    start=lo
    for a,b,z1,z2 in openings:
        if z1-.015<z<z2+.015:
            yield start,a;start=b
    yield start,hi
for typ in ['Front','Back','East','West']:
    g=Geometry()
    for j in range(12):
        z=1.1+j*.200; over=.13+.085*(j%2)
        if typ in ['Front','Back']:
            y=0 if typ=='Front' else 10.25
            for a,b in segments(-3.2-over,3.2+over,frontwin if typ=='Front' else [],z):
                g.tube((a,y,z),(b,y,z),.146,.148,rng.choice(logs['X']),14,endwood)
        else:
            x=3.2 if typ=='East' else -3.2
            for a,b in segments(-over,10.25+over,sidewin if typ=='East' else [],z):
                g.tube((x,a,z+.045),(x,b,z+.045),.145,.145,rng.choice(logs['Y']),14,endwood)
    g.obj(typ+' · scribed round log courses',house)
peak=6.31;eave=3.27;span=3.65;slope=(peak-eave)/span
g=Geometry()
for y in [0,10.25]:
    for i in range(34):
        x=-3.2+(i+.5)*6.4/34
        h=peak-abs(x)*slope-3.28
        if h>0:g.box((x,y,3.28+h/2),(.186,.18,h),rng.choice(logs['Z']))
    g.box((0,y-.11,3.34),(6.5,.21,.15),trim)
g.obj('Boarded gables and tie beams',house)
def opening(g,base,u,v,width,height,matgrid,divs=2,rows=1):
    base=V(base);u=V(u);v=V(v);out=u.cross(v);axes=(u,-out,v)
    def board(x,z,w,h,t,off,mat):
        g.box(base+u*x+v*z+out*off,(w,t,h),mat,axes)
    board(0,height/2,width+.11,height+.12,.08,.01,dark)
    for i in range(divs):
        for j in range(rows):
            board(-width/2+(i+.5)*width/divs,(j+.5)*height/rows,width/divs-.054,height/rows-.044,.02,.064,matgrid[(i+j*divs)%len(matgrid)])
    for z in [0,height]:board(0,z,width+.20,.088,.13,.098,trim)
    for x in [-width/2,width/2]:board(x,height/2,.09,height,.14,.098,trim)
    board(0,-.045,width+.22,.055,.22,.11,trimlight)
g=Geometry()
opening(g,(-1.71,-.135,1.57),(1,0,0),Z,1.48,1.29,[glow[0],glow[2],glow[1]],3)
opening(g,(1.62,-.135,1.55),(1,0,0),Z,1.75,1.33,[glassdark,glassdark,glassdark],3)
opening(g,(.63,-.112,4.18),(1,0,0),Z,.54,.92,[glow[3],glassdark],1,2)
opening(g,(3.33,1.95,1.64),(0,1,0),Z,1.70,1.27,[glow[3],glow[0],glow[1]],3)
opening(g,(3.33,9.3,1.64),(0,1,0),Z,.9,1.19,[glassdark],2)
g.box((-.105,-.095,1.99),(1.02,.12,1.93),trimlight)
opening(g,(-.105,-.175,1.90),(1,0,0),Z,.78,.85,[glassdark,glow[3]],2)
for x in [-.41,.19]:g.box((x,-.175,1.44),(.18,.035,.46),logs['Z'][1])
g.tube((.25,-.25,1.83),(.25,-.31,1.83),.042,.044,iron)
# Fine sash bars, a shaded valance and pleated amber curtains catch the lamplight.
for x in [-2.18,-1.20]:
    for j in range(5):
        curtain=[glow[0],glow[1],glow[0],glow[2],glow[0]][j]
        g.box((x+j*.022,-.211,2.24),(.022,.009,1.18-.035*abs(j-2)),curtain)
g.box((-1.71,-.217,2.74),(1.44,.025,.037),trim)
g.box((3.419,1.95,2.72),(.031,1.67,.039),trim)
g.box((-.10,-.21,1.47),(.83,.022,.53),logs['Z'][1])
for x in [.56,-.80]:
    g.box((x,-.235,2.61),(.104,.081,.163),iron)
    g.box((x,-.287,2.61),(.069,.044,.095),glow[2])
reflection=grain('Window reflections · tree silhouettes','323438','84705c',(5,1,.7),2.2,.16,.001)
for i in range(3):
    g.box((1.62+(i-1)*.56,-.208,2.20),(.53,.009,1.22),reflection)
g.box((1.62,-.229,1.64),(1.70,.032,.058),trimlight)
doorpanel=grain('Honey-coloured entry door','8e5730','c18445',(10,8,.7),3)
g.box((-.106,-.254,1.44),(.88,.018,.69),doorpanel)
# A reflection glaze, backed by the room colour, preserves the visible muntins.
for m in [*glow,reflection]:
    bs=m.node_tree.nodes.get('Principled BSDF')
    bs.inputs['Coat Weight'].default_value=.37;bs.inputs['Coat Roughness'].default_value=.12
g.obj('Casements, glazing and entry door',house)
# Individually staggered courses of weathered grey shingles.
slates=[grain('Split shake '+str(i),a,b,(6,3,4),4,.85,.016) for i,(a,b) in enumerate([('3b505e','697f89'),('506772','81919b'),('4e626f','778e98'),('455864','70828d'),('536b77','8799a3'),('485e6e','708993')])]
def pitched(g,ctr,run,slopeval,length,axis,step=.23):
    c=V(ctr);along=V(axis);side=along.cross(Z).normalized()
    for sign in [-1,1]:
        edge=side*sign;up=(-edge+Z*slopeval).normalized();normal=(Z+edge*slopeval).normalized()
        axes=(along,up,normal)
        L=run*sqrt(1+slopeval**2)
        g.box(c+edge*run*.5-Z*(run*slopeval*.5),(length,L,.11),trim,axes)
        nr=math.ceil(L/step);step2=L/nr
        for j in range(nr):
            pos=-length/2
            while pos<length/2-.001:
                wid=min(U(.22,.41) if pos>-length/2 or j%2==0 else .14,length/2-pos)
                g.box(c+edge*run-Z*run*slopeval+up*((j+.5)*step2)+along*(pos+wid/2)+normal*(.068+U(-.003,.004)),(max(wid-.012,.001),step2-.021,.042),rng.choice(slates),axes)
                pos+=wid
        for t in [-1,1]:
            g.box(c+edge*run/2-Z*run*slopeval/2+along*t*length*.5,(.16,L+.12,.205),logs['X'][0],axes)
        g.box(c+edge*run-Z*(run*slopeval+.03),(length+.16,.15,.16),trim,axes)
g=Geometry();pitched(g,(0,5.14,peak),3.67,slope,11.35,(0,1,0))
g.obj('Main roof · overlapping split shakes and bargeboards',roof)
# Cross gable looking over the stream.
g=Geometry()
for i in range(18):
    y=6.75+(i-8.5)*.15;top=5.65-abs(y-6.75)*.92
    g.box((3.44,y,(top+3.16)/2),(.15,.145,top-3.16),rng.choice(logs['Z']))
for side in [-1,1]:
    y=6.75+side*1.36
    g.part([(1.9,y,3.85),(3.3,y,3.85),(3.3,y,3.22)],[(0,1,2)],trim)
pitched(g,(2.13,6.75,5.66),1.56,.92,3.18,(-1,0,0),.20)
opening(g,(3.54,6.75,3.92),(0,1,0),Z,.96,.99,[glow[3],glassdark],2)
g.obj('Creek-side dormer and sash',roof)
g=Geometry();copper=grain('Weathered chimney flashing','575c5d','aba29c',(4,4,1),4,.46)
g.box((.61,3.63,5.85),(.56,.55,.14),iron)
g.tube((.61,3.63,5.76),(.61,3.63,7.33),.13,.135,copper,20)
g.tube((.61,3.63,7.22),(.61,3.63,7.49),.166,.166,iron,20)
g.tube((.61,3.63,7.49),(.61,3.63,7.55),.193,.095,iron,20)
g.obj('Capped stove pipe',roof)
g=Geometry()
for i in range(12):g.box((0,-.09-i*.159,1.02),(6.65,.155,.105),rng.choice([trimlight,*logs['X']]))
for x in [-3.23,-1.03,.98,3.23]:
    for y in ([-1.85,-.12] if abs(x)>2 else [-1.85]):
        g.box((x,y,1.04),(.165,.165,2.08),trimlight)
        g.box((x,y,2.095),(.19,.19,.065),trim)
for a,b in [(-3.23,-1.03),(.98,3.23)]:
    for z in [1.31,1.61,1.91]:g.box(((a+b)/2,-1.85,z),(b-a,.105,.094),trimlight)
for x in [-3.23,3.23]:
    for z in [1.31,1.61,1.91]:g.box((x,-.99,z),(.09,1.73,.1),trimlight)
for x in [-.83,.84]:
    g.tube((x,-3.98,-.01),(x,-1.81,.92),.076,.085,trim,8)
for j in range(6):g.box((-.025,-3.88+j*.368,.075+j*.166),(2.04,.39,.106),trimlight)
g.box((0,-1.89,.88),(6.62,.15,.21),logs['X'][1])
g.obj('Front porch · rails, planks and six stair treads',deck)
split=grain('Split firewood · heartwood','9e714c','d6b287',(3,5,3),4)
bark=grain('Rough flaking firewood bark','322c29','655342',(3,6,6),4)
g=Geometry()
for side in [-1,1]:
    for row,count in enumerate([13,12,10,8,6]):
        for i in range(count):
            x=side*2.16+(i-(count-1)/2)*.135+U(-.04,.04);y=U(-2.98,-2.51)
            a=V((x,y,.11+.115*row));b=a+V((U(-.31,.31),U(.57,.94),U(.00,.16)))
            g.tube(a,b,U(.071,.106),U(.068,.097),rng.choice([bark,bark,split]),rng.choice([5,6,8]),split)
g.obj('Stacked split firewood either side of steps',deck)
# A fine gravel margin follows the meander. Terrain vertex colour places moss,
# exposed sand and leaf litter, while two noise scales supply grain.
soil=material('Forest floor · painted moss and soil','79684d',.98)
p=soil.node_tree.nodes.get('Principled BSDF')
t=node(soil,'ShaderNodeTexCoord').outputs['Object']
col=node(soil,'ShaderNodeVertexColor');col.layer_name='Ground cover'
coarse=texture(soil,t,3.6,5);fine=texture(soil,t,64,2)
r=ramp(soil,[(.21,'63574a'),(.78,'fff4d9')]);link(soil,coarse,r.inputs[0])
mix=node(soil,'ShaderNodeMixRGB');mix.blend_type='MULTIPLY';mix.inputs[0].default_value=.69
link(soil,col.outputs[0],mix.inputs[1]);link(soil,r.outputs[0],mix.inputs[2])
link(soil,mix.outputs[0],p.inputs['Base Color'])
b=node(soil,'ShaderNodeBump');b.inputs['Distance'].default_value=.044;b.inputs['Strength'].default_value=.37
link(soil,fine,b.inputs['Height']);link(soil,b.outputs[0],p.inputs['Normal'])
def blend(a,b,k):return tuple(x+(y-x)*k for x,y in zip(a,b))
moss1=rgb('667342');moss2=rgb('889455');bare=rgb('90766b');litter=rgb('896445');gravel=rgb('858790')
def cover(x,y):
    s,d=sd(x,y);bank=d-shore(s);v=nval(x*.65,y*.65)
    px,py=project(x,y,ground(x,y))
    path=interpol(py,[(450,480),(540,472),(610,454),(680,393),(755,256),(823,166),(970,35)])
    trail=exp(-((px-path)/(38+max(0,py-480)*.077))**2)
    patch=exp(-((px-421)/168)**2-((py-619)/47)**2)
    around=exp(-((px-514)/155)**2-((py-477)/64)**2)
    moss=sat(.78+.67*v-1.28*max(trail,patch,around))
    forest=sat((abs(s+1)-6)*.17)+ease((d-20)/4)
    moss*=1-.87*sat(forest)
    return moss,sat(forest),sat((1.45-bank)*.90+.28*v)
ss=[-44+i*.235 for i in range(378)]
ds=[-4+i*.223 for i in range(324)]
verts=[];faces=[];colors=[]
for j,d in enumerate(ds):
    for i,s in enumerate(ss):
        q=xy(s,d);z=ground(q.x,q.y);verts.append((q.x,q.y,z))
        mo,fo,gr=cover(q.x,q.y)
        cc=blend(blend(bare,litter,fo),blend(moss1,moss2,sat(.5+.8*nval(q.x*.44,q.y*.44))),mo)
        cc=blend(cc,gravel,gr)
        bedtone=blend(rgb('423921'),rgb('a38a45'),sat(.50+1.70*nval(q.x*.8,q.y*.8)))
        cc=blend(cc,bedtone,ease((shore(s)-d+.16)/.70))
        colors.extend((*cc,1))
        if i and j:
            a=j*len(ss)+i;faces.append((a-len(ss)-1,a-len(ss),a,a-1))
g=Geometry();g.part(verts,faces,soil);o=g.obj('Undulating moss, earth paths and submerged riverbed',land,True)
attr=o.data.color_attributes.new(name='Ground cover',type='FLOAT_COLOR',domain='POINT')
attr.data.foreach_set('color',colors)
del verts,faces,colors,g
# Transparent shallow surface, with low-amplitude current ripples.
stream=material('Clear brook · ripple normal and Fresnel reflections','c4d8c6',.065)
p=stream.node_tree.nodes.get('Principled BSDF')
p.inputs['Transmission Weight'].default_value=1;p.inputs['IOR'].default_value=1.333
p.inputs['Base Color'].default_value=(.97,.98,.95,1)
refl=node(stream,'ShaderNodeBsdfGlossy');refl.inputs['Roughness'].default_value=.075
surface_mix=node(stream,'ShaderNodeMixShader');surface_mix.inputs[0].default_value=.082
link(stream,p.outputs[0],surface_mix.inputs[1]);link(stream,refl.outputs[0],surface_mix.inputs[2])
link(stream,surface_mix.outputs[0],stream.node_tree.nodes.get('Material Output').inputs['Surface'])
t=node(stream,'ShaderNodeTexCoord'); v=node(stream,'ShaderNodeVectorMath');v.operation='MULTIPLY'
v.inputs[1].default_value=(1.9,5.1,1);link(stream,t.outputs['Object'],v.inputs[0])
n=texture(stream,v.outputs[0],2.3,3.7,.98)
b=node(stream,'ShaderNodeBump');b.inputs['Strength'].default_value=.22;b.inputs['Distance'].default_value=.068
link(stream,n,b.inputs['Height']);link(stream,b.outputs[0],p.inputs['Normal']);link(stream,b.outputs[0],refl.inputs['Normal'])
g=Geometry();vv=[];ff=[];ns=206;nd=81
for j in range(nd):
    for i in range(ns):
        s=-14+i*.14;d=shore(s)+.92-(nd-1-j)*.12
        a=xy(s,d);vv.append((a.x,a.y,-1.39+.012*nval(a.x*2,a.y*3)+.003*sin(12*a.y+3*a.x)))
        k=j*ns+i
        if i and j:ff.append((k-ns-1,k-ns,k,k-1))
g.part(vv,ff,stream);g.obj('Shallow water surface',water,True)
g=Geometry()
for i in range(11500):
    s=U(-12,13); offset=U(-6.4,1.6) if i<5100 else rng.gauss(.15,.46)
    d=shore(s)+offset;q=xy(s,d);z=ground(q.x,q.y)
    radius=U(.022,.095) if i%7 else U(.084,.18)
    if offset<-.6:radius*=1.12
    if s<1.3 and offset>-.5:radius*=.36+.62*ease((s+1.5)/3.2)
    if s<1.3 and offset<-.5:radius*=.68
    peb(g,(q.x,q.y,z+radius*.14),(radius,radius*U(.57,1.13),radius*U(.43,.83)),rng.choice(stone))
    if i%2300==2299:
        g.obj('Shingle and underwater cobbles '+str(i//2300+1),water,True);g=Geometry()
g=Geometry()
for px,py,size in [(550,755,.49),(600,738,.30),(608,760,.28),(658,752,.35),(723,741,.40),(716,710,.35),(691,820,.61),(531,868,.32),(453,829,.37),(690,919,.68),(806,952,.45),(854,809,.29),(905,822,.31),(934,784,.25),(585,874,.20),(810,787,.26),(331,797,.16),(665,638,.19),(601,614,.12),(680,649,.18),(709,651,.19)]:
    # Fix the image-space centre even for boulders that project above water.
    p=at(px,py)
    for _ in range(8):
        h=ground(p.x,p.y)+size*.54
        p=p.lerp(plane(px,py,h),.55)
    base=ground(p.x,p.y)
    if py>790:
        base=max(base,-1.39-size*.5)
    shade={550:stone[4],691:stone[0],690:stone[6],453:stone[1],531:stone[3]}.get(px,rng.choice(stone[:7]))
    stretch=1.33 if px==690 else 1.0
    peb(g,(p.x,p.y,base+size*.59),(size*U(.91,1.19)*stretch,size*U(.74,1.04),size*U(.7,.98)),shade)
rock_group=g.obj('Glacial boulders · main shoreline group',water,True)
m=rock_group.modifiers.new('Rounded water-worn edges','SUBSURF');m.levels=1;m.render_levels=1
g=Geometry()
for i in range(7):
    p=at(755+i*5,700+i*1.9);q=at(822+i*2,717+i*1.4)
    g.tube(p+Z*.1,q+Z*.13,U(.055,.091),.057,bark,9,endwood)
g.obj('Driftwood at the bend',water)
leafm=[material('Fallen leaves '+str(i),h) for i,h in enumerate(['a36e3d','be9653','caad67','8c5231','bbb077','75513b','d3a360'])]
grasses=[material('Woodland sedges '+str(i),h) for i,h in enumerate(['616639','767c3e','96964e','a59a58','555b30'])]
g=Geometry();gg=Geometry()
for i in range(76000):
    s=U(-15,17);d=U(5,37);q=xy(s,d)
    if d<shore(s)+.60:continue
    z=ground(q.x,q.y);mo,fo,gr=cover(q.x,q.y)
    if rng.random()>.27+.65*fo+.12*mo:continue
    a=U(0,2*pi);rad=U(.013,.048);dx=V((cos(a),sin(a),0))*rad;dy=V((-sin(a),cos(a),0))*rad*U(.34,.64)
    p=V((q.x,q.y,z+.016));g.part([p-dx,p+dy,p+dx,p-dy,p+Z*rad*.17],[(0,1,4),(1,2,4),(2,3,4),(3,0,4)],rng.choice(leafm))
    if mo>.38 and rng.random()<mo*.79:
        for _ in range(rng.randint(5,15)):
            x=q.x+U(-.13,.13);y=q.y+U(-.13,.13);a=U(0,2*pi);w=U(.004,.014);h=U(.043,.18)
            side=V((cos(a),sin(a),0));p=V((x,y,ground(x,y)-.01))
            gg.part([p-side*w,p+side*w,p+Z*h+V((-side.y,side.x,0))*h*.54],[(0,1,2)],rng.choice(grasses))
g.obj('Fallen maple and birch leaves',land)
gg.obj('Individual grass blades in moss patches',land)
# Folding canvas chairs with crossed steel legs, arm pads and stitched fabric.
navy=material('Indigo camp canvas','15436b',.94);teal=material('Petrol camp canvas','125056',.93)
canvastrim=material('Canvas binding','21323a');steel=material('Tubular chair frames','41494a',.43,.72)
def chair(name,p,angle,cloth,sc=1,col=camp):
    g=Geometry();p=V(p);right=V((cos(angle),sin(angle),0));forward=V((-sin(angle),cos(angle),0))
    def L(x,y,z):return p+sc*(x*right+y*forward+z*Z)
    for x in [-.28,.28]:
        for a,b in [((x,-.29,.025),(x,.24,.61)),((x,.30,.025),(x,-.26,.65)),((x,-.18,.41),(x,-.36,1.0))]:
            g.tube(L(*a),L(*b),.015*sc,.014*sc,steel,8)
        g.tube(L(x,-.22,.67),L(x,.24,.64),.034*sc,.026*sc,trimlight,9)
    for y in [-.22,.24]:
        for a in [-1,1]:
            g.tube(L(a*.28,y,.04),L(-a*.26,y,.43),.013*sc,.014*sc,steel,7)
    pts=[L(-.29,-.245,.49),L(.29,-.245,.49),L(-.29,.23,.47),L(.29,.23,.47),L(0,-.025,.40),
         L(-.34,-.385,.99),L(.34,-.385,.99),L(0,-.345,.94),L(0,-.30,.66)]
    g.part(pts,[(0,2,4),(2,3,4),(3,1,4),(1,0,4),(0,8,1),(0,5,8),(5,7,8),(7,6,8),(6,1,8)],cloth)
    for a,b in [(0,5),(5,7),(7,6),(6,1),(2,3)]:g.tube(pts[a],pts[b],.012,.012,canvastrim,6)
    return g.obj(name,col)
firepos=at(461,636)
for name,px,py,mat in [('Navy folding chair',288,623,navy),('Teal folding chair',435,602,teal)]:
    p=at(px,py);angle=math.atan2(firepos.y-p.y,firepos.x-p.x)-pi/2
    chair(name,p,angle+(0.48 if px>400 else -.24),mat,1.08)
chair('Porch reading chair',(-1.13,-.95,1.08),pi*.9,teal,.85,deck)
chair('Porch stool chair',(-2.45,-1.02,1.08),pi*.93,navy,.72,deck)
g=Geometry();table=at(361,618);rt=(R*.97+F*.24).normalized();ft=V((-rt.y,rt.x,0))
def T(x,y,z):return table+rt*x+ft*y+Z*z
alloy=material('Brushed aluminium','bec2b9',.44,.52)
g.box(T(0,0,.76),(1.43,.65,.055),alloy,(rt,ft,Z))
for i in range(12):
    g.box(T((i-5.5)*.117,0,.795),(.112,.62,.025),trimlight,(rt,ft,Z))
for x in [-.60,.60]:
    for y in [-.23,.23]:
        g.tube(T(x*1.03,y*1.16,.02),T(x,y,.75),.019,.019,alloy,8)
g.obj('Slatted folding picnic table',camp)
g=Geometry()
enamel=material('Ivory enamelware','e2d6ba'); blue=material('Turquoise enamel','3e949d')
red=material('Berry jam jar','9d4834'); amber=material('Cider glass','9e682c',.23)
for x,y in [(-.46,.03),(.34,-.11),(.47,.14)]:
    g.tube(T(x,y,.813),T(x,y,.829),.094,.113,enamel,20)
for x,y,m in [(-.23,-.18,blue),(.08,.14,enamel),(-.57,-.12,red)]:
    g.tube(T(x,y,.81),T(x,y,.924),.046,.054,m,14)
    g.tube(T(x,y,.925),T(x,y,.93),.043,.044,dark,14)
for x,y,h,m in [(-.52,.22,.31,alloy),(-.33,.19,.24,amber),(.21,.16,.16,red)]:
    g.tube(T(x,y,.81),T(x,y,.81+h*.76),.044,.048,m,12)
    g.tube(T(x,y,.81+h*.76),T(x,y,.81+h),.035,.021,m,12)
g.obj('Enamel mugs, plates and bottles',camp)
g=Geometry();st=at(358,627)
for x in [-.2,.2]:
    for y in [-.14,.14]:g.tube(st+rt*x+ft*y,st-rt*x+ft*y+Z*.29,.014,.014,alloy)
g.box(st+Z*.29,(.47,.33,.06),blue,(rt,ft,Z));g.obj('Low turquoise folding stool',camp)
g=Geometry()
for i in range(11):
    a=2*pi*i/11+U(-.08,.08);q=firepos+V((cos(a)*.4,sin(a)*.4,0));q.z=ground(q.x,q.y)+.11
    peb(g,q,(U(.13,.19),U(.12,.17),U(.11,.17)),rng.choice(stone))
g.obj('Fire ring · individual stones',camp,True)
g=Geometry();g.tube(firepos+Z*.13,firepos+Z*.24,.27,.32,iron,24)
ember=material('Live embers','ff7222',.75,0,2.4)
for i in range(9):
    a=U(0,2*pi);dr=V((cos(a),sin(a),0))
    g.tube(firepos+dr*.26+Z*.24,firepos-dr*.16+Z*U(.29,.41),.047,.043,bark,7)
    peb(g,firepos+dr*U(.01,.18)+Z*.26,(.03,.045,.021),ember)
g.obj('Blackened brazier, charred sticks and embers',camp)
flame=[material('Flame '+str(i),h,.5,0,e) for i,(h,e) in enumerate([('ff6618',2.2),('ffac28',2.8),('ffdc67',3.8)])]
g=Geometry()
for i in range(15):
    a=U(0,2*pi);d=V((cos(a),sin(a),0));p=firepos+d*U(.015,.14)+Z*.26
    h=U(.18,.58);w=U(.029,.060);points=[]
    for z,r,shift in [(0,.56,0),(.25,1,.02),(.55,.48,-.013),(1,.012,.063)]:
        for k in range(6):
            ag=2*pi*k/6;points.append(p+V((w*r*cos(ag)+shift,w*r*sin(ag),h*z)))
    g.part(points,[(6*j+k,6*j+(k+1)%6,6*j+(k+1)%6+6,6*j+k+6) for j in range(3) for k in range(6)],flame[i%3])
g.obj('Wind-bent flame tongues',camp,True)
# Trees are complete branching meshes. Instances share the crown of their
# species while retaining individual position, scale and rotation.
treebarks=[grain('Bark '+s,a,b,(9,9,.85),2.4,.89,.07) for s,a,b in [('fir','383936','796e5f'),('pine','423f3a','8a796b'),('maple','584e42','988b74'),('birch','8e8576','cdc4a7')]]
needle=[material('Pine needle '+str(i),h,.86) for i,h in enumerate(['3c594c','46634c','507455','597b60','769269','648372','829064'])]
def foliage_mat(name,h):
    m=material(name,h,.77);tree=m.node_tree;p=tree.nodes.get('Principled BSDF')
    p.inputs['Emission Color'].default_value=(*rgb(h),1);p.inputs['Emission Strength'].default_value=.105
    tr=node(m,'ShaderNodeBsdfTranslucent');tr.inputs['Color'].default_value=(*rgb(h),1)
    mix=node(m,'ShaderNodeMixShader');mix.inputs[0].default_value=.24
    link(m,p.outputs[0],mix.inputs[1]);link(m,tr.outputs[0],mix.inputs[2])
    link(m,mix.outputs[0],tree.nodes.get('Material Output').inputs['Surface'])
    return m
palettes=[[foliage_mat(name+' '+str(i),h) for i,h in enumerate(colors)] for name,colors in [
('Sugar maple · amber',['e6b742','f4cb50','ecc03a','c79a41','ffda68','b9993a']),
('Birch · gold',['dbb640','edc64c','d4ac36','d6bb54','ecd670','ab943a']),
('Red maple · copper',['bf693c','dd8650','dc8b43','c17538','e9a15d','b85839']),
('Aspen · chartreuse',['ada94f','c7bc58','c7bd65','a7a04a','cfc574','989944'])]]
templates=bpy.data.collections.new('Tree prototypes');protos=[]
def saveproto(g,name):
    o=g.obj(name,templates);protos.append(o)
    return o
def limb(g,points,r0,r1,mat,n=6):
    # Joined rings preserve curved tapered trunks without seams.
    verts=[];faces=[]
    ref=V((1,0,0)) if abs((points[-1]-points[0]).normalized().x)<.82 else V((0,1,0))
    for j,p in enumerate(points):
        d=(points[min(j+1,len(points)-1)]-points[max(0,j-1)]).normalized()
        v=d.cross(ref).normalized();w=d.cross(v);r=r0+(r1-r0)*j/(len(points)-1)
        for k in range(n):
            a=2*pi*k/n;verts.append(p+(v*cos(a)+w*sin(a))*r*(1+.043*sin(k*27.1)))
            if j:faces.append(((j-1)*n+k,(j-1)*n+(k+1)%n,j*n+(k+1)%n,j*n+k))
    g.part(verts,faces,mat)
def leaves(g,origin,direc,length,pal,dominant):
    # Paired, slightly folded leaves along short, outward growing shoots.
    a=math.atan2(direc.y,direc.x); side=V((-sin(a),cos(a),0));d=direc.normalized()
    for j in [0,1,3,5,6,8]:
        sign=1 if j%2 else -1
        p=origin+d*length*(j+.2)/9+side*U(-.055,.055)+Z*U(-.045,.045)
        ang=a+sign*U(.57,1.72);l=U(.11,.212);wid=l*U(.36,.55)
        vec=V((cos(ang),sin(ang),U(-.76,.68))).normalized()*l;w=V((-sin(ang),cos(ang),U(-.53,.53)))*wid
        g.part([p,p+vec*.39+w*.70,p+vec*.53+w,p+vec,p+vec*.48-w,p+vec*.46+Z*.019],[(0,1,2,5),(2,3,5),(3,4,5),(4,0,5)],dominant if rng.random()<.58 else rng.choice(pal))
def broadleaf(idx):
    g=Geometry();pal=palettes[idx%4];bm=treebarks[3 if idx%4==1 else 2]
    H=U(11.7,15.9); rad=U(.16,.29);trunk=[V((0,0,0))]
    for j in range(1,12):
        trunk.append(V((.18*sin(j*.41+idx)-.18*sin(idx)+j*j*.002,.22*sin(j*.57),H*j/11)))
    limb(g,trunk,rad,.028,bm,10)
    for i in range(30):
        t=(i+U(.1,.9))/30; h=H*(.28+.68*t);j=min(10,int(h/H*11))
        start=trunk[j].lerp(trunk[j+1],h/H*11-j)
        a=i*2.40+U(-.52,.52);radius=(1.25+2.48*sin(pi*(.15+.85*t)))*U(.77,1.18)
        d=V((cos(a),sin(a),0));side=V((-d.y,d.x,0))
        rise=U(1.35,3.15)*(1-.51*t)
        pts=[start,start+d*radius*.32+Z*rise*.22,start+d*radius*.70+side*U(-.35,.35)+Z*rise*.51,start+d*radius+Z*rise]
        limb(g,pts,rad*(.37-.16*t),.021,bm,7)
        for k in range(7):
            u=.19+.81*k/7;seg=min(2,int(u*3));base=pts[seg].lerp(pts[seg+1],u*3-seg)
            ang=a+(1 if k%2 else -1)*U(.35,1.43)
            dr=V((cos(ang),sin(ang),0));L=U(.88,1.82)*(1-.28*t)
            mid=base+dr*L*.58+Z*U(.25,.65);tip=base+dr*L+Z*U(.75,1.55)
            limb(g,[base,mid,tip],.028,.008,bm,5)
            dom=rng.choice(pal)
            for k2 in range(7):
                u2=.23+.77*k2/7;orig=base.lerp(mid,u2*2) if u2<.5 else mid.lerp(tip,u2*2-1)
                a2=ang+(1 if k2%2 else -1)*U(.39,1.49)
                dv=V((cos(a2),sin(a2),U(.2,1.3))).normalized()
                l=U(.48,.92);pend=orig+dv*l
                if k2%2==0:limb(g,[orig,pend],.011,.003,bm,4)
                leaves(g,orig,dv,l,pal,dom)
                for k3 in range(3):
                    a3=a2+(1 if k3%2 else -1)*U(.55,1.78)
                    dv3=V((cos(a3),sin(a3),U(-.65,.85))).normalized()
                    leaves(g,orig+dv*l*(k3+.5)/3,dv3,U(.26,.54),pal,dom)
    return saveproto(g,'Broadleaf crown '+str(idx+1))
def evergreen(idx):
    g=Geometry();bm=treebarks[idx%2];H=U(13.5,15.5);rad=U(.23,.33)
    def trunk(t):return V((.19*sin(t*4+idx)-.19*sin(idx)+.32*t*t,.24*sin(t*5),H*t))
    limb(g,[trunk(i/15) for i in range(16)],rad,.019,bm,13)
    for i in range(81):
        t=.17+.822*(i+U(.05,.95))/81
        a=i*2.40+U(-.62,.62);dr=V((cos(a),sin(a),0));sdv=V((-dr.y,dr.x,0));p=trunk(t)
        L=(.32+3.85*(1-t)**.66)*U(.60,1.24)
        if t<.27 and i%3==0:L*=.5
        drop=L*U(.11,.30);sw=U(-.45,.45)
        pts=[p,p+dr*L*.30-Z*drop*.62,p+dr*L*.67+sdv*sw*.5-Z*drop,p+dr*L+sdv*sw-Z*drop*.68]
        limb(g,pts,.069*(1-t*.72),.011,bm,7)
        if t<.26 and i%3:continue
        for j in range(12):
            u=.15+.84*(j+U(.03,.98))/12;seg=min(2,int(u*3));base=pts[seg].lerp(pts[seg+1],u*3-seg)
            sign=1 if j%2 else -1;da=a+sign*U(.48,1.35);v=V((cos(da),sin(da),U(-.26,.11))).normalized()
            length=L*(.12+.20*(1-u))*U(.75,1.3)+.13
            pend=base+v*length+Z*U(.03,.18)
            if j%2==0:limb(g,[base,pend],.018,.004,bm,4)
            dom=rng.choice(needle[:6])
            for k in range(9):
                v2ang=da+(1 if k%2 else -1)*U(.37,1.24)
                v2=V((cos(v2ang),sin(v2ang),U(-.48,.49))).normalized()
                sprig=base.lerp(pend,(k+.3)/9);length2=U(.24,.46)*(1-.27*t)
                sideways=V((-v2.y,v2.x,0)).normalized()
                # Needle fascicles on each twig create porous, feathery edges.
                vv=[];ff=[]
                for n in range(17):
                    e=sprig+v2*length2*(n/17);sg=1 if n%2 else -1
                    tip=e+v2*U(.065,.15)+sideways*sg*U(.055,.15)+Z*U(-.09,.10)
                    width=U(.014,.025)
                    v3=len(vv);vv.extend([e-sideways*width,e+sideways*width,tip]);ff.append((v3,v3+1,v3+2))
                g.part(vv,ff,dom if k%3 else rng.choice(needle))
    return saveproto(g,'White pine '+str(idx+1))
print('Generating tree meshes',flush=True)
pines=[evergreen(i) for i in range(3)]
broad=[broadleaf(i) for i in range(5)]
def plant(proto,pos,scale,angle,lean=(0,0)):
    o=bpy.data.objects.new(proto.name,proto.data);woods.objects.link(o);o.location=pos
    o.rotation_euler=(lean[0],lean[1],angle);o.scale=(scale*U(.88,1.10),scale*U(.89,1.10),scale)
    return o
def tree(px,py,proto,scale,angle=0,lean=(0,0)):
    p=at(px,py)
    while -6.6<p.x<6.3 and -4<p.y<14:
        p+=(p-C).to_2d().normalized().to_3d()*.50
    p.z=ground(p.x,p.y)
    return plant(proto,p,scale,angle,lean)
tree(170,532,pines[0],1.02,1.6,(.045,-.09))
tree(832,640,pines[1],1.10,0,(-.125,.19))
tree(267,442,pines[2],.67,2.72,(.15,-.09))
tree(990,521,pines[0],1.01,2.13)
tree(-40,487,broad[0],.92,1.8)
# Lower crowns lead from the golden left margin into the darker forest floor.
for px,py,idx,scale in [(48,443,1,.46),(106,435,0,.49),(179,434,0,.46),
                         (224,419,1,.51),(314,399,0,.54),(348,397,1,.46),
                         (380,385,0,.56),(727,386,2,.51),(799,419,3,.49),
                         (862,450,1,.47),(932,472,0,.44),(1030,466,1,.58)]:
    tree(px,py,broad[idx],scale,U(0,2*pi))
tree(876,475,pines[2],.79,1.34)
tree(986,486,broad[3],.87,.76)
# Ground contact locations keep the forest out of the central clearing.
for x,y,idx,sc in [(73,450,1,.84),(223,415,0,.83),(306,404,2,.91),(355,397,1,.80),(377,379,3,.77),
                    (190,389,0,1.05),(30,383,2,.93),(593,342,2,.91),(763,388,2,.71),(816,408,1,.89),
                    (907,388,0,.82),(948,400,3,1.01),(802,366,3,.86),(560,345,0,.91)]:
    tree(x,y,broad[idx],sc,U(0,2*pi))
for px,py,sc in [(497,347,1.06),(684,353,1.18),(724,358,.97),(437,351,.98),(96,369,.94)]:
    tree(px,py,rng.choice(pines),sc,U(0,2*pi))
for j in range(115):
    s=U(-32,35);d=U(29,65);q=xy(s,d);x,y=q.x,q.y
    if -6.2<x<6.7 and -4<y<14:continue
    if d<36 and -10<s<10 and y<13:continue
    proto=rng.choice(pines) if rng.random()<.27 else rng.choice(broad)
    if -10<x<2 and 10<y<17 and proto in broad:
        proto=pines[j%len(pines)]
    plant(proto,(x,y,ground(x,y)),U(.72,1.31),U(0,2*pi))
# Slender evergreen spires behind the ridge separate the ochre crowns.
for x,y,idx,sc in [(-6.1,9.1,1,.96),(-1.7,11.7,2,1.15)]:
    o=plant(pines[idx],(x,y,ground(x,y)),sc,U(0,2*pi))
    o.scale.x*=.65;o.scale.y*=.65
# Mixed saplings and understory follow the margins, with small shrubs by the shore.
for i in range(96):
    s=U(-19,21);d=U(12.8,40);q=xy(s,d)
    if abs(s)<9.1 and d<33:continue
    if -5.6<q.x<5.8 and -4<q.y<14:continue
    plant(rng.choice(broad+pines),(q.x,q.y,ground(q.x,q.y)),U(.12,.42),U(0,2*pi))
scrubm=[foliage_mat('Creekside bilberry '+str(i),h) for i,h in enumerate(
    ['72793e','98954d','999d4d','a0873b','8e6740','686f36','bb9c4e'])]
def bush(g,base,radius):
    for _ in range(rng.randint(24,43)):
        ang=U(0,2*pi);v=V((cos(ang),sin(ang),0))
        root=base+v*radius*U(.03,.29)
        reach=U(.28,1.05)*radius;h=U(.25,.91)*radius
        mid=root+v*reach*.45+Z*h*.53;end=root+v*reach+Z*h
        limb(g,[root,mid,end],radius*.014,.004,treebarks[2],5)
        color=rng.choice(scrubm)
        for j in range(5):
            pos=root.lerp(end,.30+j*.135)
            a2=ang+(1 if j%2 else -1)*U(.45,1.18)
            dv=V((cos(a2),sin(a2),U(.22,.86))).normalized()
            for k in range(6):
                p=pos+dv*(k/6)*radius*.39
                a3=a2+(1 if k%2 else -1)*U(.5,1.35)
                blade=V((cos(a3),sin(a3),U(-.30,.55)))*U(.055,.128)
                w=V((-blade.y,blade.x,U(-.02,.02)))*.41
                g.part([p,p+blade*.44+w,p+blade,p+blade*.44-w],[(0,1,2),(0,2,3)],color)
g=Geometry()
for px,py,sc in [(811,632,.58),(776,624,.49),(689,680,.28),(642,711,.29),
                  (355,753,.29),(742,696,.39),(934,624,.58),(40,749,.32),
                  (719,666,.31),(599,733,.34),(910,614,.44),(306,779,.23),
                  (167,804,.24),(782,587,.46),(809,549,.61),(835,528,.66)]:
    bush(g,at(px,py),sc)
for i in range(130):
    px=U(741,1060);py=U(410,677)
    pos=at(px,py)
    if sd(pos.x,pos.y)[1]>shore(sd(pos.x,pos.y)[0])+1.1:
        bush(g,pos,U(.19,.59))
g.obj('Bilberry scrub and low creek bank thickets',land)
# Gravel in the path catches light between the fallen leaves.
g=Geometry()
for j in range(9600):
    ss=U(-9,11);dd=U(5.8,23);pos=xy(ss,dd);edge=dd-shore(ss)
    if edge<.6:continue
    radius=U(.009,.032)*(1.3 if edge<2.2 else 1)
    if edge>2.1 and rng.random()>.35:continue
    z=ground(pos.x,pos.y)+.01;dx=V((radius,0,0));dy=V((0,radius*.63,0));pt=V((pos.x,pos.y,z))
    g.part([pt-dx,pt+dy,pt+dx,pt-dy,pt+Z*radius*.52],[(0,1,4),(1,2,4),(2,3,4),(3,0,4)],rng.choice(stone))
g.obj('Fine path gravel and sand',land)
g=Geometry()
for k in range(74):
    ps=U(-7,8.8);pd=shore(ps)+U(.8,2.5)
    q=xy(ps,pd);rad=U(.14,.62)
    for j in range(80):
        x=q.x+rng.gauss(0,rad*.45);y=q.y+rng.gauss(0,rad*.37);pt=V((x,y,ground(x,y)+.01))
        h=U(.026,.13);a=U(0,2*pi);side=V((cos(a),sin(a),0))
        g.part([pt-side*.015,pt+side*.014,pt+side*h*.73+Z*h],[(0,1,2)],rng.choice(grasses))
g.obj('Tufts on the eroded bank',land)
# Wisps use a continuous density field with a soft boundary and turbulence.
def smoke(name,origin,drift,height,width,density):
    g=Geometry();m=bpy.data.materials.new(name);m.use_nodes=True;m.node_tree.nodes.clear()
    out=node(m,'ShaderNodeOutputMaterial');vol=node(m,'ShaderNodeVolumePrincipled')
    vol.inputs['Color'].default_value=(.65,.73,.82,1);vol.inputs['Anisotropy'].default_value=.23
    link(m,vol.outputs['Volume'],out.inputs['Volume'])
    tc=node(m,'ShaderNodeTexCoord').outputs['Generated']
    sep=node(m,'ShaderNodeSeparateXYZ');link(m,tc,sep.inputs[0]);zz=sep.outputs['Z']
    def op(code,a,b):
        nn=node(m,'ShaderNodeMath');nn.operation=code
        for inp,val in zip(nn.inputs,(a,b)):
            if isinstance(val,(int,float)):inp.default_value=val
            else:link(m,val,inp)
        return nn.outputs[0]
    no=texture(m,tc,3.8,4,.68)
    dx=op('SUBTRACT',sep.outputs['X'],op('ADD',.5,op('MULTIPLY',op('SUBTRACT',no,.5),.34)))
    dy=op('SUBTRACT',sep.outputs['Y'],.5)
    radial=op('SQRT',op('ADD',op('MULTIPLY',dx,dx),op('MULTIPLY',dy,dy)),0)
    profile=op('MAXIMUM',0,op('SUBTRACT',1,op('DIVIDE',radial,op('ADD',.065,op('MULTIPLY',zz,.43)))))
    billow=op('MAXIMUM',0,op('SUBTRACT',no,.28))
    den=op('MULTIPLY',op('MULTIPLY',profile,billow),op('MULTIPLY',density,op('SUBTRACT',1,zz)))
    link(m,den,vol.inputs['Density'])
    vol.inputs['Emission Color'].default_value=(.33,.53,.76,1)
    link(m,op('MULTIPLY',den,.34),vol.inputs['Emission Strength'])
    g.box((0,0,.5),(1,1,1),m);o=g.obj(name,air)
    axis=V(drift)+Z*height;o.location=origin
    o.rotation_euler=axis.to_track_quat('Z','Y').to_euler();o.scale=(width,width,axis.length)
smoke('Woodstove smoke',V((.61,3.63,7.53)),-R*2.05+F*.42,3.85,3.15,4.2)
smoke('Campfire smoke',firepos+Z*.64,R*.42+F*.11,2.28,1.01,1.55)
def light(name,kind,pos,color,energy):
    data=bpy.data.lights.new(name,kind);data.color=color;data.energy=energy
    o=bpy.data.objects.new(name,data);air.objects.link(o);o.location=pos;return o
sun=light('Late afternoon sun through canopy','SUN',(0,0,18),(1,.89,.75),3.4)
sun.rotation_euler=V((-.63,-.22,-.89)).to_track_quat('-Z','Y').to_euler();sun.data.angle=.12
firelight=light('Firelight','POINT',firepos+Z*.57,(1,.34,.06),26);firelight.data.shadow_soft_size=.25
world=bpy.data.worlds.new('Open sky · woodland fill');scene.world=world;world.use_nodes=True
bg=world.node_tree.nodes.get('Background');bg.inputs[0].default_value=(.64,.77,1,1);bg.inputs[1].default_value=.78
# A bluer expanse of sky is visible in the water between reflected treetops.
lp=world.node_tree.nodes.new('ShaderNodeLightPath')
sky=world.node_tree.nodes.new('ShaderNodeBackground');sky.inputs[0].default_value=(.21,.40,.71,1);sky.inputs[1].default_value=1.45
wm=world.node_tree.nodes.new('ShaderNodeMixShader')
wl=world.node_tree.links;wl.new(lp.outputs['Is Glossy Ray'],wm.inputs[0]);wl.new(bg.outputs[0],wm.inputs[1]);wl.new(sky.outputs[0],wm.inputs[2]);wl.new(wm.outputs[0],world.node_tree.nodes.get('World Output').inputs[0])
scene.unit_settings.system='METRIC'
scene.render.engine='CYCLES';scene.cycles.samples=48;scene.cycles.use_denoising=True
scene.cycles.max_bounces=7;scene.cycles.diffuse_bounces=3;scene.cycles.transmission_bounces=5
scene.render.resolution_x=1440;scene.render.resolution_y=1496;scene.render.resolution_percentage=100
scene.view_settings.view_transform='AgX';scene.view_settings.exposure=.44
scene.render.image_settings.file_format='PNG';scene.render.filepath='//秋林溪畔.png'
scene.render.film_transparent=False
for screen in bpy.data.screens:
    for a in screen.areas:
        if a.type=='VIEW_3D':
            a.spaces.active.region_3d.view_perspective='CAMERA';a.spaces.active.overlay.show_overlays=False
            a.spaces.active.shading.color_type='MATERIAL'
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'秋林溪畔.blend'),compress=True)
