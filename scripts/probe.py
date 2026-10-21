import subprocess, sys, json
def load(path, w=1920, h=1080):
    out = subprocess.run(["ffmpeg","-v","error","-i",path,"-f","rawvideo","-pix_fmt","rgb24","-"],
                         capture_output=True).stdout
    return out, w, h
def rows(buf,w,h,x0,x1,thr=0.5,mode="dark"):
    res=[]
    for y in range(h):
        base=y*w*3
        cnt=0
        for x in range(x0,x1,2):
            i=base+x*3
            r,g,b=buf[i],buf[i+1],buf[i+2]
            lum=(r*0.299+g*0.587+b*0.114)/255
            if (mode=="dark" and lum<thr) or (mode=="light" and lum>thr): cnt+=1
        res.append(cnt)
    return res
if __name__=="__main__":
    path=sys.argv[1]; x0=int(sys.argv[2]); x1=int(sys.argv[3]); mode=sys.argv[4]; thr=float(sys.argv[5])
    buf,w,h=load(path)
    r=rows(buf,w,h,x0,x1,thr,mode)
    # print contiguous bands with >2 px ink
    bands=[];start=None
    for y,v in enumerate(r):
        if v>2 and start is None: start=y
        elif v<=2 and start is not None:
            bands.append((start,y-1)); start=None
    if start is not None: bands.append((start,h-1))
    for a,b in bands:
        if b-a>=3: print(f"y {a}..{b}  h={b-a+1}")

def cols(buf,w,y0,y1,x0,x1,mode="dark",thr=0.5):
    res=[]
    for x in range(x0,x1):
        cnt=0
        for y in range(y0,y1,2):
            i=(y*w+x)*3
            lum=(buf[i]*0.299+buf[i+1]*0.587+buf[i+2]*0.114)/255
            if (mode=="dark" and lum<thr) or (mode=="light" and lum>thr): cnt+=1
        res.append(cnt)
    bands=[];start=None
    for k,v in enumerate(res):
        if v>0 and start is None: start=k
        elif v==0 and start is not None:
            bands.append((start+x0,k-1+x0)); start=None
    if start is not None: bands.append((start+x0,x1-1))
    return bands
