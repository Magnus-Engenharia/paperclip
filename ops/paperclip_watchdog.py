#!/usr/bin/env python3
import json, urllib.request, urllib.error, subprocess, datetime, time

API='http://127.0.0.1:3100'
COMPANY='52eb280e-3861-40d9-b59c-1a68731c536b'
PETCARE_PROJECT='02fa3069-ff7b-4a41-860b-28efed82fda2'
PRIMARY_ENGINEER='d87cb15d-2076-4af2-ada9-1fd219738ab5'
BACKUP_ENGINEER='4e462c03-d19c-4055-bb3a-1da36e5cde0e'
AGENTS={
  'CTO':'bf4404a1-153d-4f82-988b-6a1b55b02f68',
  'Cursor Engineer':'d87cb15d-2076-4af2-ada9-1fd219738ab5',
  'Project Shepherd':'d732f918-ad4c-4a3a-8c06-78484d4234ca',
  'Evidence Collector':'84991f28-5a3e-4b03-ae78-94bc744f4424',
  'QA Reality Checker':'9b709edc-4097-47b8-88b1-f8074a881a8f',
}


def req(path, method='GET', data=None, timeout=15):
    r=urllib.request.Request(API+path, method=method, headers={'Content-Type':'application/json'})
    if data is not None:
        r.data=json.dumps(data).encode()
    return json.load(urllib.request.urlopen(r, timeout=timeout))


def ensure_api():
    try:
        urllib.request.urlopen(API+'/api/health', timeout=5).read()
        return True
    except Exception:
        # self-heal: restart service
        subprocess.run(['launchctl','kickstart','-k',f'gui/{subprocess.check_output(["id","-u"], text=True).strip()}/com.magnus.paperclip'], check=False)
        for _ in range(20):
            time.sleep(1)
            try:
                urllib.request.urlopen(API+'/api/health', timeout=5).read()
                return True
            except Exception:
                pass
        return False


def latest_run(company, agent_id):
    runs=req(f'/api/companies/{company}/heartbeat-runs')
    for r in runs:
        if r.get('agentId')==agent_id:
            return r
    return None

def list_comments(issue_id):
    try:
        return req(f'/api/issues/{issue_id}/comments')
    except Exception:
        return []

def parse_dt(s):
    try:
        return datetime.datetime.fromisoformat((s or '').replace('Z','+00:00'))
    except Exception:
        return None

def enforce_progress_sla(summary):
    issues=req(f'/api/companies/{COMPANY}/issues')
    now=datetime.datetime.now(datetime.timezone.utc)
    pet=[i for i in issues if i.get('projectId')==PETCARE_PROJECT and i.get('status')=='in_progress']
    for i in pet:
        upd=parse_dt(i.get('updatedAt'))
        if not upd: continue
        mins=(now-upd).total_seconds()/60.0
        if mins < 60: continue
        comments=list_comments(i['id'])
        if len(comments)==0:
            # invalid cycle: no evidence/comment progress
            body=(
                f"AUTO-SLA: issue stale for {int(mins)}m with no progress comment/evidence. "
                f"Marking blocked and reassigning to backup engineer for continuity."
            )
            try:
                req(f"/api/issues/{i['id']}/comments",'POST',{'body':body})
            except Exception:
                pass
            # reassign engineer lanes only
            assignee=i.get('assigneeAgentId')
            if assignee==PRIMARY_ENGINEER:
                req(f"/api/issues/{i['id']}",'PATCH',{'status':'blocked','assigneeAgentId':BACKUP_ENGINEER})
                try: req(f'/api/agents/{BACKUP_ENGINEER}/wakeup','POST',{'source':'automation','triggerDetail':'system','reason':f'SLA escalation for {i.get("identifier")}'} )
                except Exception: pass
                summary.append(f"- SLA escalation: {i.get('identifier')} -> backup engineer")
            elif assignee==BACKUP_ENGINEER:
                req(f"/api/issues/{i['id']}",'PATCH',{'status':'blocked','assigneeAgentId':PRIMARY_ENGINEER})
                try: req(f'/api/agents/{PRIMARY_ENGINEER}/wakeup','POST',{'source':'automation','triggerDetail':'system','reason':f'SLA escalation for {i.get("identifier")}'} )
                except Exception: pass
                summary.append(f"- SLA escalation: {i.get('identifier')} -> primary engineer")
            else:
                req(f"/api/issues/{i['id']}",'PATCH',{'status':'blocked'})
                summary.append(f"- SLA blocked (non-engineer assignee): {i.get('identifier')}")


def heal_failed_agent(agent_id, reason):
    req(f'/api/agents/{agent_id}/runtime-state/reset-session', 'POST', {'reason': reason})
    req(f'/api/agents/{agent_id}/wakeup', 'POST', {'source':'automation','triggerDetail':'system','reason':reason})


def fix_cursor_known_flags():
    aid=AGENTS['Cursor Engineer']
    a=req(f'/api/agents/{aid}')
    cfg=a.get('adapterConfig') or {}
    args=cfg.get('args') or []
    if len(args)<2 or not isinstance(args[1], str):
        return False
    s=args[1]
    ns=s.replace(' --cwd "$PWD"','').replace('--cwd "$PWD" ','').replace(' --format quiet','').replace('--format quiet ','')
    if ns!=s:
        req(f'/api/agents/{aid}','PATCH',{'adapterConfig':{**cfg,'args':[args[0],ns]}})
        return True
    return False


def code_first_nudge():
    # keep nudging CTO/Engineer towards ENG-45 implementation
    for aid in [AGENTS['CTO'], AGENTS['Cursor Engineer'], AGENTS['Project Shepherd']]:
        req(f'/api/agents/{aid}/wakeup','POST',{
            'source':'automation','triggerDetail':'system',
            'reason':'PRIORITY: deliver code for ENG-45; docs-only work not sufficient'
        })


def post_watchdog_comment(summary_lines):
    issues=req(f'/api/companies/{COMPANY}/issues')
    epic=next((i for i in issues if i.get('identifier')=='ENG-43'), None)
    if not epic:
        return
    body='\n'.join(['Watchdog tick ('+datetime.datetime.now().strftime('%Y-%m-%d %H:%M')+')']+summary_lines)
    req(f"/api/issues/{epic['id']}/comments",'POST',{'body':body})


def main():
    summary=[]
    if not ensure_api():
        print('watchdog: API still down after restart attempt')
        return

    # known quick fix
    if fix_cursor_known_flags():
        summary.append('- Cursor flags auto-patched (--cwd/--format removed)')

    for name,aid in AGENTS.items():
        r=latest_run(COMPANY, aid)
        if not r:
            heal_failed_agent(aid, f'watchdog: no runs for {name}')
            summary.append(f'- {name}: no run found -> reset+wake')
            continue
        status=r.get('status')
        err=(r.get('error') or '').lower()
        if status=='failed' or 'unknown option' in err or 'connection refused' in err:
            heal_failed_agent(aid, f'watchdog auto-heal for {name}: {r.get("error") or "failed run"}')
            summary.append(f'- {name}: auto-healed failed run')

    enforce_progress_sla(summary)

    code_first_nudge()
    summary.append('- code-first nudges sent (ENG-45 priority)')

    # lightweight project progress snapshot
    issues=req(f'/api/companies/{COMPANY}/issues')
    p=[i for i in issues if i.get('projectId')==PETCARE_PROJECT]
    counts={s:sum(1 for i in p if i.get('status')==s) for s in ['todo','in_progress','done','blocked']}
    summary.append(f"- Pet Care counts: todo={counts['todo']} in_progress={counts['in_progress']} done={counts['done']} blocked={counts['blocked']}")

    post_watchdog_comment(summary)
    print('watchdog: ok')

if __name__=='__main__':
    main()
