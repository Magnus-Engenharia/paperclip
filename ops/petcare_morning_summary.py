#!/usr/bin/env python3
import json, urllib.request, datetime
API='http://127.0.0.1:3100'
COMPANY='52eb280e-3861-40d9-b59c-1a68731c536b'
EPIC_IDENT='ENG-43'

def req(path, method='GET', data=None):
    r=urllib.request.Request(API+path, method=method, headers={'Content-Type':'application/json'})
    if data is not None:
        r.data=json.dumps(data).encode()
    return json.load(urllib.request.urlopen(r, timeout=15))

issues=req(f'/api/companies/{COMPANY}/issues')
by={i.get('identifier'):i for i in issues}
epic=by.get(EPIC_IDENT)
if not epic:
    print('epic not found'); raise SystemExit(0)
children=[i for i in issues if i.get('parentId')==epic.get('id')]
counts={s:sum(1 for i in children if i.get('status')==s) for s in ['todo','in_progress','done','blocked']}
lines=[
 f"Morning project summary ({datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}):",
 f"EPIC {EPIC_IDENT}: {epic.get('status')}",
 f"Children -> todo:{counts['todo']} in_progress:{counts['in_progress']} done:{counts['done']} blocked:{counts['blocked']}",
]
for i in sorted(children,key=lambda x:x.get('identifier') or ''):
    lines.append(f"- {i.get('identifier')} {i.get('status')} — {i.get('title')}")
body='\n'.join(lines)
req(f"/api/issues/{epic['id']}/comments",'POST',{'body':body})
print('posted epic morning summary')
