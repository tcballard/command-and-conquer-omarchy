#!/usr/bin/env python3
"""Compile the original atlases into complete OpenRA sprite/sequence sets.

Vehicle source is overhead: rotate in world space BEFORE foreshortening.
Infantry use eight independently authored views, never rotated paper figures.
All gameplay sequences are local; no stock body/turret/death frames are inherited.
"""
from pathlib import Path
from functools import lru_cache
from collections import deque
import json
import colorsys
import math
from PIL import Image, ImageDraw, ImageFont, ImageEnhance
import build_art
import build_skirmish_art as util
import skirmish_roster as roster

ROOT=Path(__file__).resolve().parent.parent
SOURCE=ROOT/'assets/source'
CONTRACT=json.loads((ROOT/'tools/sequence_contract.json').read_text())
BUILDINGS={
 'omarchy':'powr apwr proc silo tent weap dome fix atek pdox gap pbox hbox gun agun sbag fenc brik hpad mslo'.split(),
 'garden':'powr apwr proc silo barr weap dome fix stek kenn iron ftur sam afld mslo brik tsla hpad sbag fenc'.split(),
}
VEHICLES={
 'omarchy':'mcv 1tnk 2tnk arty jeep apc mnly ctnk mgg harv mrj heli tran mh60 turret-light turret-heavy'.split(),
 'garden':'mcv 3tnk 4tnk v2rl ftrk ttnk apc mnly harv mig yak hind badr turret-heavy turret-super turret-flak'.split(),
}
INFANTRY={
 'omarchy':'e1 e3 e6 medi mech spy thf e7'.split(),
 'garden':'e1 e2 e3 e4 shok e6 dog spy'.split(),
}
AIR={'heli','tran','mh60','mig','yak','hind','badr','u2'}
WALLS={'sbag','fenc','brik'}
TURRETS={'1tnk':'turret-light','2tnk':'turret-heavy','jeep':'turret-light','stnk':'turret-light',
         '3tnk':'turret-heavy','4tnk':'turret-super','ftrk':'turret-flak',
         'gun':'turret-heavy','agun':'turret-light','sam':'turret-flak'}
SIZES={'mcv':42,'harv':38,'1tnk':28,'2tnk':32,'3tnk':34,'4tnk':42,'jeep':24,'apc':32,
       'heli':44,'mh60':44,'tran':54,'mig':46,'yak':42,'hind':48,'badr':72,'u2':60,
       'v2rl':40,'arty':36,'truk':34,'stnk':30,'qtnk':38,'dtrk':36}
STRUCTURE_SIZES={'fact':(80,88),'powr':(46,62),'apwr':(70,76),'proc':(72,78),'silo':(24,32),
 'tent':(48,48),'barr':(48,58),'weap':(72,66),'dome':(48,62),'fix':(72,54),'atek':(48,64),
 'stek':(72,78),'pdox':(48,54),'iron':(48,54),'gap':(26,58),'pbox':(24,26),'hbox':(24,24),
 'gun':(26,22),'agun':(26,24),'sam':(46,28),'ftur':(24,40),'tsla':(26,66),'kenn':(24,28),
 'hpad':(48,48),'afld':(72,48),'mslo':(48,32),'sbag':(24,18),'fenc':(24,22),'brik':(24,24)}
REVERSE={'omarchy':{'mcv','jeep','ctnk','mgg','harv','mrj','tran'},'garden':{'mcv','harv','hind','badr'}}
ALIASES={'omarchy':{'truk':'mcv','stnk':'apc','u2':'tran'},
         'garden':{'truk':'mcv','qtnk':'ttnk','dtrk':'v2rl','thf':'spy','u2':'badr'}}


def kind(side,actor):
    base=ALIASES.get(side,{}).get(actor,actor)
    if base in INFANTRY[side]: return 'infantry'
    if base=='fact' or base in BUILDINGS[side]: return 'building'
    return 'vehicle'


@lru_cache(None)
def atlas(name):
    im=Image.open(SOURCE/f'{name}.png').convert('RGBA')
    if im.getchannel('A').getextrema()[0]!=0: raise ValueError(f'{name}: transparency required')
    return im


@lru_cache(None)
def cell(name,index,columns,rows):
    im=atlas(name); w,h=im.size; x,y=index%columns,index//columns
    tile=im.crop((x*w//columns,y*h//rows,(x+1)*w//columns,(y+1)*h//rows))
    # Atlas generation can leave fragments of a neighbour at cell boundaries.
    # Import only the largest connected silhouette (alpha >= 128).
    w,h=tile.size;mask=bytearray(1 if a>=128 else 0 for a in tile.getchannel('A').getdata())
    components=[]
    for seed in range(len(mask)):
        if not mask[seed]: continue
        queue=deque([seed]);mask[seed]=0;component=[]
        while queue:
            i=queue.popleft();component.append(i);x,y=i%w,i//w
            for j in (i-1 if x else -1,i+1 if x<w-1 else -1,i-w if y else -1,i+w if y<h-1 else -1):
                if j>=0 and mask[j]: mask[j]=0;queue.append(j)
        components.append(component)
    if not components: raise ValueError(f'Empty cell {name}/{index}')
    main=max(components,key=len);keep=bytearray(w*h)
    for i in main: keep[i]=255
    alpha=Image.frombytes('L',(w,h),bytes(keep));tile.putalpha(alpha)
    return tile.crop(alpha.getbbox())


def fit(im,size,canvas=None,bottom=False):
    scale=min(size[0]/im.width,size[1]/im.height)
    im=im.resize((max(1,round(im.width*scale)),max(1,round(im.height*scale))),Image.Resampling.LANCZOS)
    if canvas:
        result=Image.new('RGBA',canvas)
        result.alpha_composite(im,((canvas[0]-im.width)//2,canvas[1]-im.height-3 if bottom else (canvas[1]-im.height)//2))
        return result
    return im


@lru_cache(None)
def source(side,actor,facing=0):
    base=ALIASES.get(side,{}).get(actor,actor)
    if base=='fact': return util.yard_images()[0 if side=='omarchy' else 2]
    category=kind(side,actor)
    if category=='building': return cell(f'{side}-buildings',BUILDINGS[side].index(base),5,4)
    if category=='infantry': return cell(f'{side}-infantry',INFANTRY[side].index(base)*8+facing,8,8)
    im=cell(f'{side}-vehicles',VEHICLES[side].index(base),4,4)
    if base in REVERSE[side]: im=im.rotate(180)
    return im


def shifted(im,x=0,y=0):
    out=Image.new('RGBA',im.size);out.alpha_composite(im,(x,y));return out


def damage(im):
    out=ImageEnhance.Color(im).enhance(.28)
    out=ImageEnhance.Brightness(out).enhance(.53)
    d=ImageDraw.Draw(out)
    # Deterministic scars constrained to the original silhouette.
    scars=Image.new('RGBA',im.size);s=ImageDraw.Draw(scars)
    w,h=im.size
    for n in range(5):
        x=w//3+(n*13)%(max(1,w//3));y=h//3+(n*17)%(max(1,h//3))
        s.line((x,y,x+4,y+5),fill=(22,23,29,220),width=2)
    scars.putalpha(Image.composite(scars.getchannel('A'),Image.new('L',im.size),im.getchannel('A')))
    out.alpha_composite(scars);return out


def pulse(im,step):
    rgb=ImageEnhance.Brightness(im).enhance(1+.10*math.sin(step*math.pi/3))
    rgb.putalpha(im.getchannel('A'));return rgb


def projected(im,facing,size,canvas=(80,80),pivot=False):
    # Work at 2x final resolution; keep the turret pivot fixed independently of barrel length.
    plane=Image.new('RGBA',(160,160)); tile=fit(im,(size*2,size*2))
    py=round(tile.height*.73) if pivot else tile.height//2
    plane.alpha_composite(tile,(80-tile.width//2,80-py))
    plane=plane.rotate(facing*360/32,resample=Image.Resampling.BICUBIC)
    plane=plane.resize((80,56),Image.Resampling.LANCZOS)
    out=Image.new('RGBA',canvas);out.alpha_composite(plane,((canvas[0]-80)//2,(canvas[1]-56)//2))
    return out


@lru_cache(maxsize=2)
def quantizer(palette,team):
    indices=[i for i in range(1,256) if not team or not 80<=i<=95]
    indices += [indices[-1]]*(256-len(indices))
    im=Image.new('P',(1,1));im.putpalette([c for i in indices for c in palette[i]])
    return im,indices


@lru_cache(maxsize=131072)
def team_index(rgb):
    r,g,b=rgb
    hue,saturation,value=colorsys.rgb_to_hsv(r/255,g/255,b/255)
    if saturation>.3 and (.18<hue<.45 or hue>.9 or hue<.04):
        return 80+max(0,min(15,round((1-value)*17)))
    return None


def indexed(im,palette,team_colours=False):
    ref,indices=quantizer(tuple(palette),team_colours)
    im=im.convert('RGBA')
    quant=im.convert('RGB').quantize(palette=ref,dither=Image.Dither.NONE).tobytes()
    pixels=im.getdata()
    out=bytearray(len(quant))
    for i,(r,g,b,a) in enumerate(pixels):
        if a>=128:
            team=team_index((r,g,b)) if team_colours else None
            out[i]=team if team is not None else indices[quant[i]]
    return bytes(out)


class Sprite:
    def __init__(self,name,size,palette):
        self.name,self.size,self.palette=name,size,palette
        self.frames=[];self.sequences={};self.cache={};self.indexcache={}
    def add(self,name,frames,facings=1,**kwargs):
        converted=[]
        for im in frames:
            key=im.tobytes()
            if key not in self.indexcache: self.indexcache[key]=indexed(im,self.palette,team_colours=True)
            converted.append(self.indexcache[key])
        frames=converted
        key=tuple(frames)
        if key not in self.cache:
            self.cache[key]=len(self.frames);self.frames.extend(frames)
        self.sequences[name]={'Start':self.cache[key],'Length':len(frames)//facings,'Facings':facings,**kwargs}
    def alias(self,name,other,**kwargs): self.sequences[name]={**self.sequences[other],**kwargs}
    def write(self,out,icon=True):
        build_art.write_shp(out/f'{self.name}.shp',*self.size,self.frames)
        lines=[f'{self.name}:',f'\tDefaults:\n\t\tFilename: {self.name}.shp']
        for seq,fields in self.sequences.items():
            lines.append(f'\t{seq}:')
            lines.extend(f'\t\t{k}: {v}' for k,v in fields.items())
        if icon:
            for seq in ('icon','fake-icon'):
                lines += [f'\t{seq}:',f'\t\tFilename: {self.name}-icon.shp','\t\tOffset: 0,0']
        return '\n'.join(lines)+'\n'


def building(side,actor,palette):
    size=(96,96) if actor not in WALLS else (24,32)
    art=source(side,actor)
    healthy=fit(art,STRUCTURE_SIZES[actor],size)
    damaged=damage(healthy)
    if actor=='fact': damaged=util.yard_images()[1 if side=='omarchy' else 3]
    s=Sprite(f'{side}-{actor}',size,palette)
    s.add('idle',[healthy]);s.add('damaged-idle',[damaged])
    if actor in WALLS:
        # Engine adjacency mask: north=1, east=2, south=4, west=8.
        # The original wall panel supplies the texture, extruded along each connected arm.
        for seq,base in [('idle',healthy),('scratched-idle',pulse(damaged,1)),('damaged-idle',damaged)]:
            variants=[]
            for mask in range(16):
                tile=Image.new('RGBA',size)
                panel=fit(base,(12,18));tile.alpha_composite(panel,(6,8))
                for bit,(dx,dy) in enumerate([(0,-7),(7,0),(0,7),(-7,0)]):
                    if mask&(1<<bit): tile.alpha_composite(panel,(6+dx,8+dy))
                variants.append(tile)
            s.add(seq,variants)
        return s
    deploy=[]
    for n in range(12):
        frame=healthy.copy();mask=Image.new('L',size);ImageDraw.Draw(mask).rectangle((0,round(size[1]*(11-n)/12),size[0],size[1]),fill=255)
        frame.putalpha(Image.composite(frame.getchannel('A'),Image.new('L',size),mask));deploy.append(frame)
    s.add('make',deploy,Tick=80)
    for seq,base in [('build',healthy),('active',healthy),('damaged-build',damaged),('damaged-active',damaged)]:
        s.add(seq,[pulse(base,n) for n in range(6)],Tick=100)
    s.alias('place','idle')
    blank=Image.new('RGBA',size)
    # Refinery roof and factory door overlays occupy their own layer, not a duplicated full building.
    for seq,base in [('idle-top',healthy),('damaged-idle-top',damaged)]:
        overlay=base.copy();a=overlay.getchannel('A');ImageDraw.Draw(a).rectangle((0,56,96,96),fill=0);overlay.putalpha(a)
        s.add(seq,[overlay])
    for seq,base in [('build-top',healthy),('damaged-build-top',damaged)]:
        overlays=[]
        for n in range(6):
            overlay=Image.new('RGBA',size);d=ImageDraw.Draw(overlay)
            d.rectangle((37,57,58,57+round(13*(1-n/5))),fill=(*((66,73,62) if side=='omarchy' else (105,100,113)),255))
            overlays.append(overlay)
        s.add(seq,overlays,Tick=100)
    for seq,base in [('stages',healthy),('damaged-stages',damaged)]:
        levels=[]
        for n in range(9):
            frame=base.copy();d=ImageDraw.Draw(frame)
            d.rectangle((44,54-n*2,51,55),fill=(*util.GREEN,255));levels.append(frame)
        s.add(seq,levels)
    wreck=[]
    for n in range(8):
        frame=damaged.copy();alpha=frame.getchannel('A')
        alpha.putdata([a if (i*13+i//size[0]*7)%8>=n else 0 for i,a in enumerate(alpha.getdata())]);frame.putalpha(alpha);wreck.append(frame)
    s.add('dead',wreck,Tick=100)
    if actor in TURRETS:
        turret=source(side,TURRETS[actor]);length=26 if actor!='sam' else 32
        rotating=[projected(turret,f,length,size,pivot=True) for f in range(32)]
        s.add('turret',rotating,32)
        s.add('recoil',[shifted(im,0,1) for im in rotating],32)
        s.add('damaged-turret',[damage(im) for im in rotating],32)
        s.add('damaged-recoil',[shifted(damage(im),0,1) for im in rotating],32)
    add_muzzle(s)
    return s


def add_muzzle(s):
    flashes=[]
    for face in range(8):
        for n in range(3):
            im=Image.new('RGBA',s.size);d=ImageDraw.Draw(im);cx,cy=s.size[0]//2,s.size[1]//2
            r=4-n;d.polygon([(cx,cy-r*2),(cx+r,cy),(cx,cy+r),(cx-r,cy)],fill=(255,211,115,255));
            flashes.append(im.rotate(face*45))
    s.add('muzzle',flashes,8,Tick=40);s.alias('garrison-muzzle','muzzle')


def vehicle(side,actor,palette):
    s=Sprite(f'{side}-{actor}',(80,80),palette)
    length=SIZES.get(actor,32)
    views=[projected(source(side,actor),f,length) for f in range(32)]
    s.add('idle',views,32)
    if actor=='harv':
        for state,level in [('half',3),('empty',0)]:
            cargo=[]
            for im in views:
                frame=im.copy();d=ImageDraw.Draw(frame)
                d.rectangle((35,34,44,39),fill=(34,38,43,255))
                if level: d.rectangle((36,38-level,43,38),fill=(*util.GREEN,255))
                cargo.append(frame)
            s.add(f'{state}-load',cargo,32)
    s.add('wreck',[damage(im) for im in views],32)
    if actor in TURRETS:
        turret=[projected(source(side,TURRETS[actor]),f,22 if actor in ('1tnk','jeep','stnk') else 30,pivot=True) for f in range(32)]
        s.add('turret',turret,32)
        s.add('wreck-turret',[damage(im) for im in turret],32)
    # Standalone overlays pulse without doubling the hull. Hardware already belongs to body art.
    signal=[]
    for n in range(8):
        im=Image.new('RGBA',s.size);d=ImageDraw.Draw(im)
        d.ellipse((38-n%3,36-n%3,41+n%3,39+n%3),outline=(120,220,255,200));signal.append(im)
    s.add('spinner',signal,Tick=100);s.alias('spinner-idle','spinner',Length=1)
    s.add('piston',[shifted(signal[n],0,round(math.sin(n*math.pi/4)*2)) for f in range(8) for n in range(8)],8)
    for seq in ('rotor','rotor2','slow-rotor','slow-rotor2'):
        blades=[]
        for n in range(8):
            im=Image.new('RGBA',s.size);d=ImageDraw.Draw(im)
            for a in (n*math.pi/8,n*math.pi/8+math.pi/2):
                dx,dy=math.cos(a)*22,math.sin(a)*15
                d.line((40-dx,40-dy,40+dx,40+dy),fill=(125,137,151,205),width=2)
            blades.append(im)
        s.add(seq,blades,Tick=40 if seq.startswith('rotor') else 100)
    for seq in ('open','dock','dock-loop'):
        # Loading/transport ramp cycle, locked to stock docking orientation.
        base=views[24]
        ramps=[]
        for n in range(6):
            im=base.copy();d=ImageDraw.Draw(im);d.rectangle((36,46,44,47+n),fill=(84,91,101,255));ramps.append(im)
        s.add(seq,ramps,Tick=100)
    s.alias('unload','open',Length=1,Start=s.sequences['open']['Start']+5)
    s.add('harvest',[shifted(views[f*4],0,n%2) for f in range(8) for n in range(6)],8,Tick=100)
    # Launcher folds while reloading; real separate empty-body state.
    empty=[]
    for im in views:
        frame=damage(im) if actor=='v2rl' else im.copy();empty.append(frame)
    s.add('empty-idle',empty,32)
    add_muzzle(s)
    return s


def infantry(side,actor,palette):
    size=(40,40);s=Sprite(f'{side}-{actor}',size,palette)
    # Normalize the eight authored directions as a group so facing changes never alter scale.
    originals=[source(side,actor,f) for f in range(8)]
    maximum=max(im.height for im in originals);height=23 if actor!='dog' else 18
    bases=[]
    for im in originals:
        im=im.resize((max(1,round(im.width*height/maximum)),max(1,round(im.height*height/maximum))),Image.Resampling.LANCZOS)
        frame=Image.new('RGBA',size);frame.alpha_composite(im,((40-im.width)//2,31-im.height));bases.append(frame)
    s.add('stand',bases,8);s.alias('stand2','stand')
    run=[];attack=[];prone=[]
    for base in bases:
        for n in range(6):
            # Articulated lower-body stride around a fixed torso, not rotating a flat person.
            frame=Image.new('RGBA',size);frame.alpha_composite(base.crop((0,0,40,23)),(0,n%2))
            step=round(math.sin(n*math.pi/3)*2)
            frame.alpha_composite(base.crop((0,23,20,40)),(0,23+step))
            frame.alpha_composite(base.crop((20,23,40,40)),(20,23-step));run.append(frame)
            attack.append(shifted(base,0,1 if n in (1,2) else 0))
        compressed=base.resize((40,24),Image.Resampling.LANCZOS)
        frame=Image.new('RGBA',size);frame.alpha_composite(compressed,(0,10));prone.append(frame)
    s.add('run',run,8,Tick=100);s.alias('walk','run',Tick=140)
    for seq in ('shoot','throw','heal','repair','eat','jump','shoot-left','shoot-right'):
        s.add(seq,attack,8,Tick=80)
    s.add('prone-stand',prone,8);s.alias('prone-stand2','prone-stand')
    s.add('prone-run',[shifted(im,0,n%2) for im in prone for n in range(6)],8,Tick=100)
    for seq in ('prone-shoot','prone-throw','prone-shoot-left','prone-shoot-right'): s.alias(seq,'prone-run',Tick=80)
    s.add('liedown',[im for pair in zip(bases,prone) for im in pair],8)
    s.add('standup',[im for pair in zip(prone,bases) for im in pair],8)
    for seq in ('idle','idle1','idle2'): s.add(seq,[pulse(bases[4],n) for n in range(6)],Tick=160)
    s.add('parachute',[bases[4]])
    death=[]
    for n in range(8):
        fallen=damage(bases[4]).resize((40,max(6,40-n*4)),Image.Resampling.LANCZOS)
        frame=Image.new('RGBA',size);frame.alpha_composite(fallen,(min(n,4),31-fallen.height*31//40));death.append(frame)
    for n in range(1,7): s.add(f'die{n}',death,Tick=80)
    s.add('die-crushed',[death[-1]],Tick=1600)
    add_muzzle(s);return s


def icon_images():
    result={};font=ImageFont.load_default(size=8)
    for side,entries in roster.SIDES.items():
        accent=util.GREEN if side=='omarchy' else util.RED
        for actor,name,_,_ in entries:
            if actor in roster.SUPPORT: continue
            icon=Image.new('RGBA',(64,48),(26,27,38,255));d=ImageDraw.Draw(icon)
            portrait=fit(source(side,actor,4 if kind(side,actor)=='infantry' else 0),(48,28))
            icon.alpha_composite(portrait,((64-portrait.width)//2,1))
            words=name.split();lines=['']
            for word in words:
                candidate=(lines[-1]+' '+word).strip()
                if d.textlength(candidate,font=font)>60 and lines[-1]: lines.append(word)
                else: lines[-1]=candidate
            for n,line in enumerate(lines[:2]): d.text((2,29+n*9),line,font=font,fill=accent)
            d.rectangle((0,0,63,47),outline=accent);result[side,actor]=icon
    return result


def build(output):
    output.mkdir(parents=True,exist_ok=True)
    samples=[]
    for side,entries in roster.SIDES.items():
        for actor,*_ in entries: samples.append(fit(source(side,actor),(96,96)))
    icons=icon_images();palette_bytes,palette=util.make_palette(samples+list(icons.values()))
    (output/'omarchy-art.pal').write_bytes(palette_bytes)
    sequences=[];manifest={};previews=[]
    for side,entries in roster.SIDES.items():
        for actor,name,*_ in entries:
            category=kind(side,actor)
            sprite={'building':building,'vehicle':vehicle,'infantry':infantry}[category](side,actor,palette)
            sequences.append(sprite.write(output,actor not in roster.SUPPORT))
            if category=='vehicle':
                aliases=f'{sprite.name}-wreck:\n\tInherits: {sprite.name}\n\tidle:\n\t\tStart: {sprite.sequences["wreck"]["Start"]}\n'
                if 'wreck-turret' in sprite.sequences:
                    aliases+=f'\tturret:\n\t\tStart: {sprite.sequences["wreck-turret"]["Start"]}\n'
                sequences.append(aliases)
            if actor=='harv':
                for state in ('empty','half'):
                    sequences.append(f'{sprite.name}-{state}:\n\tInherits: {sprite.name}\n\tidle:\n\t\tStart: {sprite.sequences[state+"-load"]["Start"]}\n')
            required=set(CONTRACT.get(actor,[]))-{'icon','fake-icon','bib'}
            missing=required-set(sprite.sequences)
            if missing: raise ValueError(f'{side}/{actor}: missing sequences {missing}')
            manifest[sprite.name]={'actor':actor,'side':side,'kind':category,'size':sprite.size,'frames':len(sprite.frames),'sequences':sprite.sequences}
            preview_palette=palette[:]
            if side=='garden':
                for i in range(16): preview_palette[80+i]=tuple(min(255,round(c*(1.35-i*.065))) for c in util.RED)
            seq='stand' if category=='infantry' else 'idle';idx=sprite.sequences[seq]['Start']+(4 if category=='infantry' else 4 if category=='vehicle' else 0)
            frame=util.sprite_preview(sprite.frames[idx],preview_palette,sprite.size)
            if actor in TURRETS and category=='vehicle': frame.alpha_composite(util.sprite_preview(sprite.frames[sprite.sequences['turret']['Start']+4],preview_palette,sprite.size))
            previews.append((side,name,frame))
    for (side,actor),im in icons.items(): build_art.write_shp(output/f'{side}-{actor}-icon.shp',64,48,[indexed(im,palette)])
    # Existing engine harvester fullness images have no faction lookup: explicit conditional bodies in rules select these.
    (output/'sequences.yaml').write_text('\n'.join(sequences))
    (output/'art-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    sheet=Image.new('RGB',(768,128*((len(previews)+5)//6)),(26,27,38));d=ImageDraw.Draw(sheet);font=ImageFont.load_default(size=11)
    for i,(side,name,im) in enumerate(previews):
        x,y=i%6*128,i//6*128
        tile=Image.new('RGBA',(128,104));tile.alpha_composite(im,((128-im.width)//2,(104-im.height)//2))
        sheet.paste(tile,(x,y),tile);d.text((x+4,y+107),name[:20],font=font,fill=util.GREEN if side=='omarchy' else util.RED)
    sheet.save(output/'roster-preview.png')
    iconsheet=Image.new('RGB',(512,48*((len(icons)+7)//8)),(26,27,38))
    for i,im in enumerate(icons.values()): iconsheet.paste(im,(i%8*64,i//8*48))
    iconsheet.save(output/'icon-preview.png')
    return manifest


if __name__=='__main__': build(ROOT/'build/omarchy-skirmish')
