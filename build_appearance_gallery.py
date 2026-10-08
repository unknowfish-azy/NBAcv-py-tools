import json,argparse,hashlib
from pathlib import Path
import cv2,numpy as np
from video_identity_pipeline import visual_features
p=argparse.ArgumentParser();p.add_argument('reviewed_crops');p.add_argument('output');a=p.parse_args();rows=json.loads(Path(a.reviewed_crops).read_text(encoding='utf-8-sig'));gallery=[]
for r in rows:
 if r.get('confirmed') is not True or not r.get('reviewer') or not r.get('player_id'):raise ValueError('Confirmed identity and reviewer required')
 image=Path(r['image']);raw=image.read_bytes();img=cv2.imdecode(np.frombuffer(raw,np.uint8),cv2.IMREAD_COLOR)
 if img is None:raise ValueError('Unreadable image')
 x,y,x2,y2=map(int,r['bbox'])
 if not 0<=x<x2<=img.shape[1] or not 0<=y<y2<=img.shape[0]:raise ValueError('Invalid crop')
 gallery.append({'player_id':r['player_id'],'features':visual_features(img[y:y2,x:x2]),'source':str(image),'image_sha256':hashlib.sha256(raw).hexdigest(),'reviewer':r['reviewer']})
with Path(a.output).open('x',encoding='utf8') as f:json.dump(gallery,f,ensure_ascii=False,indent=2)
print('Gallery entries:',len(gallery))
