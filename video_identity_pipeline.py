import argparse,json,subprocess,hashlib,time,collections
from pathlib import Path
import cv2,numpy as np

def color(a):
 hsv=cv2.cvtColor(a,cv2.COLOR_BGR2HSV);h,s,v=np.median(hsv.reshape(-1,3),axis=0)
 if v<55:return 'black'
 if s<45:return 'white' if v>180 else 'gray'
 return 'red' if h<12 or h>168 else 'orange' if h<25 else 'yellow' if h<38 else 'green' if h<85 else 'blue' if h<135 else 'purple'
def visual_features(crop):
 h,w=crop.shape[:2]
 if h<32 or w<12:return {'status':'insufficient_pixels'}
 torso=crop[int(h*.2):int(h*.6),int(w*.2):int(w*.8)];shoe=crop[int(h*.88):,int(w*.1):int(w*.9)]
 hist=cv2.calcHist([cv2.cvtColor(torso,cv2.COLOR_BGR2HSV)],[0,1],None,[12,4],[0,180,0,256]).flatten();hist/=max(float(hist.sum()),1)
 shoe_hist=cv2.calcHist([cv2.cvtColor(shoe,cv2.COLOR_BGR2HSV)],[0,1],None,[12,4],[0,180,0,256]).flatten();shoe_hist/=max(float(shoe_hist.sum()),1)
 return {'jersey_histogram':hist.tolist(),'shoe_histogram':shoe_hist.tolist() if h>=100 else [],'status':'measured_proxy','jersey_color':color(torso),'shoe_color':color(shoe) if h>=100 else None,'appearance_histogram':hist.tolist(),'height_width_ratio':h/w,'shoe_region_quality':'bbox_proxy_not_segmented','real_height_cm':None}
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--video',required=True);ap.add_argument('--model',required=True);ap.add_argument('--out',required=True);ap.add_argument('--start',type=float,default=0);ap.add_argument('--seconds',type=float,default=10);ap.add_argument('--fps',type=float,default=5);ap.add_argument('--width',type=int,default=960);ap.add_argument('--ocr',action='store_true');ap.add_argument('--roster');ap.add_argument('--gallery');ap.add_argument('--team-map');ap.add_argument('--substitutions');ap.add_argument('--ffmpeg',default='E:/ffmpeg/bin/ffmpeg.exe');a=ap.parse_args()
 if a.seconds<=0 or a.fps<=0 or a.width<64:raise ValueError('invalid bounds')
 out=Path(a.out);out.mkdir(parents=True,exist_ok=False)
 from ultralytics import YOLO
 model=YOLO(a.model);roster=json.loads(Path(a.roster).read_text(encoding='utf-8-sig')) if a.roster else []
 reader=None
 if a.ocr:
  import easyocr
  reader=easyocr.Reader(['en'],gpu=False,download_enabled=False)
 probe=subprocess.run([str(Path(a.ffmpeg).with_name('ffprobe.exe')),'-v','error','-select_streams','v:0','-show_entries','stream=width,height','-of','json',a.video],capture_output=True,text=True,check=True)
 meta=json.loads(probe.stdout)['streams'][0];w=a.width;h=round(meta['height']*w/meta['width']/2)*2
 cmd=[a.ffmpeg,'-v','error','-ss',str(a.start),'-i',a.video,'-t',str(a.seconds),'-vf',f'scale={w}:{h},fps={a.fps}','-f','rawvideo','-pix_fmt','bgr24','pipe:1']
 log=(out/'decode.log').open('wb');proc=subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=log);prev=None;shot=0;count=0;detections=0;started=time.monotonic()
 from identity_evidence import IdentityResolver
 resolver=IdentityResolver(gallery=json.loads(Path(a.gallery).read_text(encoding='utf-8-sig')) if a.gallery else []);team_map=json.loads(Path(a.team_map).read_text(encoding='utf-8-sig')) if a.team_map else {};subs=json.loads(Path(a.substitutions).read_text(encoding='utf-8-sig')) if a.substitutions else [];trajectories=collections.defaultdict(list)
 try:
  with (out/'evidence.jsonl').open('w',encoding='utf8') as ef,(out/'review_queue.jsonl').open('w',encoding='utf8') as rf,(out/'presence.jsonl').open('w',encoding='utf8') as pf:
   while count<int(a.seconds*a.fps):
    buf=bytearray()
    while len(buf)<w*h*3:
     chunk=proc.stdout.read(w*h*3-len(buf))
     if not chunk:break
     buf.extend(chunk)
    if len(buf)!=w*h*3:break
    frame=np.frombuffer(buf,dtype=np.uint8).reshape(h,w,3).copy();gray=cv2.resize(cv2.cvtColor(frame,cv2.COLOR_BGR2GRAY),(64,36));cut=prev is not None and float(np.mean(np.abs(gray.astype(float)-prev)))>45
    if cut:
     shot+=1
     if getattr(model.predictor,'trackers',None):
      for tracker in model.predictor.trackers:tracker.reset()
    prev=gray
    result=model.track(frame,persist=True,tracker='bytetrack.yaml',verbose=False,conf=.3)[0];visible=[];timestamp=a.start+count/a.fps
    for bi,box in enumerate(result.boxes):
     cls=int(box.cls.item());label=str(result.names[cls]).lower()
     if not any(x in label for x in ['person','player']):continue
     xy=box.xyxy[0].cpu().numpy();x1,y1,x2,y2=map(int,xy);x1=max(0,x1);y1=max(0,y1);x2=min(w,x2);y2=min(h,y2)
     if x2<=x1 or y2<=y1:continue
     tid=int(box.id.item()) if box.id is not None else None;crop=frame[y1:y2,x1:x2];features=visual_features(crop);number=None;score=0.;ocr=[]
     if result.keypoints is not None:
      kp=result.keypoints.data[bi].cpu().numpy();features['pose_keypoints']=kp.tolist()
      if len(kp)==17 and kp.shape[1]>=3 and all(kp[j,2]>.5 for j in [5,6,11,12]):
       shoulder=float(np.linalg.norm(kp[5,:2]-kp[6,:2]));hip=float(np.linalg.norm(kp[11,:2]-kp[12,:2]));features['shoulder_hip_ratio']=shoulder/max(hip,1.)
     if reader and count%max(1,round(a.fps))==0 and crop.shape[0]>=64:
      roi=crop[int(len(crop)*.18):int(len(crop)*.65)]
      for poly,text,conf in reader.readtext(roi,allowlist='0123456789',detail=1):
       if text.isdigit() and len(text)<=2:ocr.append({'text':text,'score':float(conf)})
      if ocr:number,score=max(((x['text'],x['score']) for x in ocr),key=lambda x:x[1])
     row={'frame':count,'timestamp':timestamp,'timestamp_s':timestamp,'shot_id':shot,'track_id':tid,'bbox':list(map(int,[x1,y1,x2,y2])),'detector_score':float(box.conf.item()),'features':features,'team':None,'team_score':0.,'jersey_number':number,'jersey_score':score,'ocr_candidates':ocr,'evidence_source':'easyocr' if ocr else 'visual_only'}
     mapping=team_map.get(features.get('jersey_color'),{});row['team']=mapping.get('team');row['team_score']=mapping.get('score',0.);row['team_evidence']=mapping;row['identity_result']=resolver.update(row,roster) if tid is not None else {'identity':'unknown','review_reasons':['untracked_detection']};trajectories[f'{shot}:{tid}'].append({'timestamp_s':timestamp,'foot_pixel':[(x1+x2)/2,y2],'body_ratio':features.get('height_width_ratio')});ef.write(json.dumps(row,ensure_ascii=False)+'\n');rf.write(json.dumps({'frame':count,'track_id':tid,'reason':'identity_and_features_require_review'})+'\n');visible.append(tid);detections+=1
     cv2.rectangle(frame,(x1,y1),(x2,y2),(0,220,0),1);cv2.putText(frame,f'T{tid} #{number if number is not None else "?"}',(x1,max(15,y1)),cv2.FONT_HERSHEY_SIMPLEX,.4,(0,255,255),1)
    pf.write(json.dumps({'timestamp_s':timestamp,'shot_id':shot,'visible_tracks':visible,'players':resolver.presence(timestamp,visible,shot_id=shot,substitution_events=subs),'absence_semantics':'off_screen_or_occluded; no substitution evidence unless supplied'})+'\n')
    if count<5:cv2.imencode('.jpg',frame)[1].tofile(str(out/f'review_{count:04}.jpg'))
    count+=1
    if count%10==0:print(f'frames={count} detections={detections}',flush=True)
 finally:
  proc.stdout.close()
  try:rc=proc.wait(timeout=10)
  except subprocess.TimeoutExpired:proc.terminate();rc=proc.wait(timeout=10)
  log.close()
 manifest={'video':str(Path(a.video).resolve()),'model':str(Path(a.model).resolve()),'model_sha256':hashlib.sha256(Path(a.model).read_bytes()).hexdigest(),'video_stat':{'size':Path(a.video).stat().st_size,'mtime_ns':Path(a.video).stat().st_mtime_ns},'video_sha256':None,'frames':count,'detections':detections,'elapsed_s':time.monotonic()-started,'sample_fps':a.fps,'start':a.start,'width':w,'height':h,'ocr_enabled':a.ocr,'status':'ENGINEERING_ONLY','accuracy':'NOT_EVALUATED','ffmpeg_exit':rc,'notes':['color/body proportions are uncalibrated proxies','not detecting faces or true height','shot cut threshold is heuristic','missing player is not confirmed off court']}
 (out/'trajectories.json').write_text(json.dumps(dict(trajectories),ensure_ascii=False),encoding='utf8');(out/'run_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf8');print(json.dumps(manifest,ensure_ascii=False))
if __name__=='__main__':main()
