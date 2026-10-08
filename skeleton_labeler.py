"""Read-only skeleton annotation normalizer and quality gate."""
import json, math
from pathlib import Path

COCO17 = ["nose","left_eye","right_eye","left_ear","right_ear","left_shoulder","right_shoulder","left_elbow","right_elbow","left_wrist","right_wrist","left_hip","right_hip","left_knee","right_knee","left_ankle","right_ankle"]
def validate_pose(keypoints, width, height):
    invalid=0; normalized=[]
    if not isinstance(keypoints,list): return {"invalid":1,"keypoints":[]}
    for p in keypoints:
        if not isinstance(p,(list,tuple)) or len(p) not in (2,3): invalid+=1; normalized.append([None,None,0]); continue
        x,y=p[:2];v=p[2] if len(p)==3 else 2
        ok=isinstance(x,(int,float)) and isinstance(y,(int,float)) and math.isfinite(x) and math.isfinite(y) and 0<=x<=width and 0<=y<=height and v in (0,1,2)
        if not ok: invalid+=1; normalized.append([None,None,0])
        else: normalized.append([float(x),float(y),int(v)])
    return {"invalid":invalid,"keypoints":normalized}
def parse_labelme(data, expected_points=17):
    w,h=data.get("imageWidth"),data.get("imageHeight");people=[]
    for shape in data.get("shapes") or []:
        pts=shape.get("points") if isinstance(shape,dict) else None
        if not isinstance(pts,list): people.append({"label":"unknown","status":"invalid","keypoints":[]});continue
        kp=[[p[0],p[1],2] for p in pts if isinstance(p,(list,tuple)) and len(p)>=2]
        checked=validate_pose(kp,w,h) if isinstance(w,(int,float)) and isinstance(h,(int,float)) else {"invalid":1,"keypoints":kp}
        status="human_verified" if data.get("checked") is True and data.get("reviewer") else "human_pending"
        if len(kp)!=expected_points or checked["invalid"]:status="invalid"
        people.append({"label":shape.get("label","unknown"),"status":status,"keypoints":checked["keypoints"]})
    return {"schema":"nba.pose17.v1","status":"human_pending","image_width":w,"image_height":h,"people":people}
def detect_temporal_jumps(rows,max_displacement=50):
    prior={};out=[]
    for row in sorted(rows,key=lambda x:x.get("frame",0)):
        cur=[];review=False
        for p in row.get("keypoints") or []:
            if isinstance(p,(list,tuple)) and len(p)>=2 and p[0] is not None:cur.append(p)
        old=prior.get(row.get("track_id"))
        if old and cur and sum(math.hypot(a[0]-b[0],a[1]-b[1]) for a,b in zip(old,cur))/min(len(old),len(cur))>max_displacement:review=True
        item=dict(row);item["status"]="review" if review else row.get("status","ok");out.append(item)
        if cur:prior[row.get("track_id")]=cur
    return out
def normalize_file(path,expected_points=17):
    data=json.loads(Path(path).read_text(encoding="utf-8-sig"))
    if isinstance(data,dict) and data and all(isinstance(v,list) for v in data.values()) and any(isinstance(v,list) and v and isinstance(v[0],dict) and 'kpts' in v[0] for v in data.values()):
        frames=[]
        for frame,people in data.items():
            out=[]
            for i,p in enumerate(people):
                kp=p.get('kpts',[]);scores=p.get('scores',[])
                if len(kp)!=expected_points:status='invalid'
                else:status='human_pending'
                points=[]
                for j,pt in enumerate(kp):
                    score=float(scores[j]) if j<len(scores) else 0.0
                    points.append([float(pt[0]),float(pt[1]),2 if score>=0.3 else 1 if score>0 else 0] if isinstance(pt,(list,tuple)) and len(pt)>=2 else [None,None,0])
                out.append({'person_index':i,'status':status,'keypoints':points,'scores':scores})
            frames.append({'frame':frame,'people':out})
        return {'schema':'nba.pose17.v1','status':'human_pending','source_format':'pose17','frames':frames}
    return parse_labelme(data,expected_points)
