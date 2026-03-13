#!/usr/bin/env python3
import json, urllib.request, datetime
API='http://127.0.0.1:3100'
COMPANY='52eb280e-3861-40d9-b59c-1a68731c536b'
AGENTS=[
 'bf4404a1-153d-4f82-988b-6a1b55b02f68', # CTO
 'd87cb15d-2076-4af2-ada9-1fd219738ab5', # Cursor Engineer
 'd732f918-ad4c-4a3a-8c06-78484d4234ca', # Project Shepherd
 '84991f28-5a3e-4b03-ae78-94bc744f4424', # Evidence Collector
 '9b709edc-4097-47b8-88b1-f8074a881a8f', # QA
]
PETCARE_PREFIX='Pet Care:'

def req(path,method='GET',data=None):
    r=urllib.request.Request(API+path,method=method,headers={'Content-Type':'application/json'})
    if data is not None:
        r.data=json.dumps(data).encode()
    return json.load(urllib.request.urlopen(r))

# periodic wake for autonomous loop
for aid in AGENTS:
    try:
        req(f'/api/agents/{aid}/wakeup','POST',{'source':'automation','triggerDetail':'system','reason':'petcare autonomy loop tick'})
    except Exception:
        pass

# unstuck check: nudge assignee if petcare issue in progress > 45m with no update
def parse_dt(s):
    try:
        return datetime.datetime.fromisoformat(s.replace('Z','+00:00'))
    except Exception:
        return None

now=datetime.datetime.now(datetime.timezone.utc)
try:
    issues=req(f'/api/companies/{COMPANY}/issues')
    for i in issues:
        title=i.get('title') or ''
        if not (title.startswith(PETCARE_PREFIX) or 'Pet Care' in title):
            continue
        if i.get('status')!='in_progress':
            continue
        upd=parse_dt(i.get('updatedAt') or '')
        if not upd:
            continue
        if (now-upd).total_seconds()>45*60 and i.get('assigneeAgentId'):
            aid=i['assigneeAgentId']
            req(f'/api/agents/{aid}/wakeup','POST',{'source':'automation','triggerDetail':'system','reason':f'stall recovery for {i.get("identifier")}'})
except Exception:
    pass

print('petcare autonomy tick ok')
