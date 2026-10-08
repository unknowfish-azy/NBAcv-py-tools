"""CLI helpers for ZCode/CVAT; originals are never overwritten."""
import argparse, json
from pathlib import Path
from skeleton_labeler import normalize_file, detect_temporal_jumps
from player_identity_cv import resolve_identity, build_identity_report

def skeleton_cmd(inp,out,expected):
    src=Path(inp); files=[src] if src.is_file() else sorted(src.rglob('*.json')); rows=[]
    for p in files:
        try:
            result=normalize_file(p,expected); result['source_file']=str(p); rows.append(result)
        except Exception as e: rows.append({'source_file':str(p),'status':'invalid','error':str(e)})
    out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps({'schema':'nba.pose17.v1','files':rows},ensure_ascii=False,indent=2),encoding='utf8')
    return {'files':len(rows),'invalid':sum(x.get('status')=='invalid' for x in rows)}
def identity_cmd(tracks,roster,out):
    data=json.loads(Path(tracks).read_text(encoding='utf8-sig')); roster_data=json.loads(Path(roster).read_text(encoding='utf8-sig'))
    rows=data if isinstance(data,list) else data.get('tracks',data.get('rows',[])); roster_data=roster_data if isinstance(roster_data,list) else roster_data.get('players',[])
    resolved=[dict(r,**resolve_identity(r,roster_data)) for r in rows]
    result={'schema':'nba.identity.v1','rows':resolved,'report':build_identity_report(resolved),'unknown_queue':[r for r in resolved if r['identity']=='unknown']}
    out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8');return result['report']
def main():
    ap=argparse.ArgumentParser();sub=ap.add_subparsers(dest='cmd',required=True)
    s=sub.add_parser('skeleton');s.add_argument('input');s.add_argument('output',type=Path);s.add_argument('--expected-points',type=int,default=17)
    i=sub.add_parser('identity');i.add_argument('tracks');i.add_argument('roster');i.add_argument('output',type=Path)
    a=ap.parse_args();print(json.dumps(skeleton_cmd(a.input,a.output,a.expected_points) if a.cmd=='skeleton' else identity_cmd(a.tracks,a.roster,a.output),ensure_ascii=False))
if __name__=='__main__':main()
