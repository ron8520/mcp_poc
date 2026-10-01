"""Render the high-level workflows described by the internal review Markdown."""
from pathlib import Path
from xml.etree import ElementTree as ET
import argparse
from dataclasses import replace

from build_review_diagrams import Box, Edge, Page, COLORS, page_to_drawio, page_to_svg

HERE = Path(__file__).resolve().parent
C = COLORS


def _base_data_flow():
    p = Page('data-flow', 'Data flow and boundaries', 1600, 1000,
             'SharePoint MCP — data flow and security boundaries',
             'Employee access first · required boundaries shown · live validation pending',
             output='sharepoint-review-data-flow.svg')
    p.boxes = [
        Box('client_zone',30,310,290,500,'APPROVED CLIENT','',C['gray_fill'],C['line'],kind='zone'),
        Box('aws_zone',370,310,720,500,'AWS SERVICE BOUNDARY · SYDNEY','',C['blue_fill'],C['blue'],kind='zone'),
        Box('ms_zone',1150,310,420,500,'MICROSOFT 365 BOUNDARY','',C['orange_fill'],C['orange'],kind='zone'),
        Box('entra',780,130,270,100,'Microsoft Entra ID','Employee identity and consent\nSeparate service access tokens',C['purple_fill'],C['purple']),
        Box('client',55,390,240,140,'Employee / AI app','Request and returned content\nModel and storage destinations\nrequire separate approval'),
        Box('gateway',410,390,260,140,'AgentCore Gateway','Validate caller\nAuthorize operation\nRoute request'),
        Box('runtime',780,390,270,140,'SharePoint Runtime','Execute approved operation\nObtain employee Graph access\nProcess content temporarily'),
        Box('graph',1200,390,320,100,'Microsoft Graph','Permission-checked API access',C['white'],C['orange']),
        Box('sharepoint',1200,650,320,100,'SharePoint Online','Files, employee ACLs\nand document recovery',C['white'],C['orange']),
        Box('policy',410,650,260,100,'Policy Engine','Separate read / upload rights',C['white'],C['blue']),
        Box('relay',780,650,270,100,'AWS Lambda','Trusted credential handoff\nSupports Gateway request',C['white'],C['blue']),
        Box('support',370,845,720,110,'Supporting security and operations services','AWS IAM: service-to-service access · Secrets Manager: protected credentials\nCloudWatch / SIEM: safe audit metadata, alerts and incident evidence',C['gray_fill'],C['line']),
        Box('private',35,845,295,110,'Network boundary','Enterprise route + PrivateLink\nIdentity checks remain required',C['gray_fill'],C['line']),
        Box('download',1150,845,420,110,'PDF download path','Runtime downloads bytes from an approved\nMicrosoft file location; the temporary link\nis sensitive and must not reach client/logs.',C['orange_fill'],C['orange']),
    ]
    p.edges = [
        Edge('client','entra','Sign-in / caller token',color=C['purple'],source_anchor=(.5,0),target_anchor=(0,.5),points=((175,180),)),
        Edge('runtime','entra','Request Graph access',color=C['purple'],source_anchor=(.5,0),target_anchor=(.5,1)),
        Edge('client','gateway','Request',source_anchor=(1,.3),target_anchor=(0,.3)),
        Edge('gateway','runtime','Approved',label_offset=(-28,-8),source_anchor=(1,.3),target_anchor=(0,.3)),
        Edge('runtime','graph','Graph request',label_offset=(-42,-8),source_anchor=(1,.3),target_anchor=(0,.42)),
        Edge('graph','runtime','Result',dashed=True,source_anchor=(0,.85),target_anchor=(1,.607142857)),
        Edge('runtime','gateway','Result',dashed=True,source_anchor=(0,.78),target_anchor=(1,.78)),
        Edge('gateway','client','Result',dashed=True,source_anchor=(0,.78),target_anchor=(1,.78)),
        Edge('graph','sharepoint','Read / write',source_anchor=(.5,1),target_anchor=(.5,0)),
        Edge('gateway','policy','Permission check',label_offset=(-102,-5),source_anchor=(.5,1),target_anchor=(.5,0),arrow=False),
        Edge('gateway','relay','Credential handoff',source_anchor=(.8,1),target_anchor=(.5,0),points=((618,585),(915,585)),arrow=False),
    ]
    return p


def m2m_data_flow():
    p = _base_data_flow()
    p.id = 'm2m-data-flow'
    p.name = 'M2M data flow and boundaries'
    p.title = 'SharePoint MCP — application-only data flow'
    p.subtitle = 'Staged M2M design · app-only ingress disabled · provider and site-access validation pending'
    p.output = 'sharepoint-review-m2m-data-flow.svg'
    updates = {
        'client_zone': dict(title='APPROVED APPLICATION'),
        'aws_zone': dict(y=110,h=700),
        'ms_zone': dict(y=110,h=700,title='MICROSOFT SERVICE BOUNDARY'),
        'client': dict(title='Background application', detail='No employee identity\nApproved business workflow\nApproved result destinations'),
        'entra': dict(x=1200, y=180, w=320, title='Microsoft Entra ID', detail='Caller application token\nSeparate Graph application token'),
        'runtime': dict(title='Application Runtime', detail='Verify caller + site + operation\nSelect approved Graph identity\nNo employee ACL assumption'),
        'gateway': dict(detail='Validate app-only caller\nEnforce application role\nRoute to application lane'),
        'sharepoint': dict(detail='Explicit selected-site grants\nfor downstream Graph application'),
        'policy': dict(detail='Application read / upload roles'),
        'relay': dict(detail='Trusted signed caller context\nNo credential selection'),
        'support': dict(detail='AWS IAM: Gateway invocation and approved credential-provider access\nAudit: caller application, downstream identity, operation and outcome'),
    }
    p.boxes = [replace(b, **updates.get(b.id, {})) for b in p.boxes]
    p.boxes.append(Box('identity',780,180,270,100,'AgentCore Identity',
                       'Approved M2M provider\nObtain Graph application token',C['purple_fill'],C['purple']))
    edges = []
    for e in p.edges:
        if e.source == 'client' and e.target == 'entra':
            e = replace(e,label='Application authentication',target_anchor=(.5,0),
                        points=((175,100),(1360,100)))
        elif e.source == 'runtime' and e.target == 'entra':
            e = replace(e,target='identity',label='Approved provider only')
        edges.append(e)
    edges.append(Edge('identity','entra','Token acquisition',color=C['purple'],
                      source_anchor=(1,.5),target_anchor=(0,.5),label_offset=(-50,-8)))
    p.edges = edges
    return p


def data_flow():
    p = m2m_data_flow()
    p.id = 'data-flow'
    p.name = 'Employee target data flow'
    p.title = 'SharePoint MCP — employee target data flow'
    p.subtitle = 'Employee target flow · Entra-issued tokens via AgentCore Identity · live validation pending'
    p.output = 'sharepoint-review-data-flow.svg'
    updates = {
        'client_zone': dict(title='APPROVED EMPLOYEE CLIENT'),
        'client': dict(title='Employee / AI app',detail='Sign in as employee\nGateway-audience token\nApproved result destinations'),
        'entra': dict(detail='Issues Gateway, Runtime and\nGraph tokens for the employee'),
        'identity': dict(detail='Broker both OBO exchanges\nPreserve employee identity'),
        'runtime': dict(title='Delegated Runtime',detail='Validate Runtime token\nRequest delegated Graph token\nPreserve employee identity'),
        'gateway': dict(detail='Validate caller and operation\nRequest Runtime OBO token\nInvoke delegated Runtime'),
        'policy': dict(detail='Employee read / upload roles'),
        'relay': dict(title='Separate receiving services',detail='Gateway token → Runtime token\nRuntime token → Graph token'),
        'sharepoint': dict(detail='Employee site and file ACLs\nDocument recovery controls'),
        'support': dict(detail='AWS IAM: only approved delegated credential providers\nAudit: employee, client, operation and outcome - no tokens or content'),
    }
    p.boxes = [replace(b, **updates.get(b.id, {})) for b in p.boxes]
    edges = []
    for e in p.edges:
        if e.target == 'relay':
            continue
        if e.source == 'client' and e.target == 'entra':
            e = replace(e,label='Employee sign-in for Gateway token')
        elif e.source == 'runtime' and e.target == 'identity':
            e = replace(e,label='Graph OBO token')
        elif e.source == 'gateway' and e.target == 'runtime':
            e = replace(e,label='Runtime token',label_offset=(-42,-8))
        edges.append(e)
    edges.append(Edge('gateway','identity','Runtime OBO token',color=C['purple'],
                      source_anchor=(.5,0),target_anchor=(0,.5),points=((540,230),),label_offset=(-95,-8)))
    p.edges = edges
    return p


def phase_one_overview():
    p = Page('phase-one','Phase-one services',1600,1000,
             'Phase one — SharePoint and CRM behind one Gateway',
             'Target service boundaries · CRM summary update implemented locally, not yet enabled',
             output='phase-one-review-overview.svg')
    p.boxes = [
        Box('clients',20,260,285,560,'APPROVED CALLERS','',C['gray_fill'],C['line'],kind='zone'),
        Box('aws',350,110,760,850,'AWS PLATFORM','',C['blue_fill'],C['blue'],kind='zone'),
        Box('systems',1190,110,390,710,'DOWNSTREAM SYSTEMS','',C['orange_fill'],C['orange'],kind='zone'),
        Box('employee',45,310,235,120,'Employee / AI client','Delegated SharePoint access'),
        Box('app',45,580,235,140,'Approved application','SharePoint and/or CRM\nExplicit operation grants'),
        Box('entra',30,130,275,100,'Microsoft Entra ID','Caller tokens for Gateway',C['purple_fill'],C['purple']),
        Box('gateway',385,430,270,140,'Shared AgentCore Gateway','Caller validation + policy\nSelect authorized service/lane'),
        Box('sp_user',780,200,280,100,'SharePoint delegated','Employee identity and ACLs'),
        Box('sp_app',780,360,280,100,'SharePoint application','Approved application/site grants'),
        Box('crm',780,600,280,130,'CRM application Runtime','Separate CRM MCP server\nUpdate case summary only\nNo delegated CRM lane'),
        Box('sharepoint',1230,200,315,260,'Graph / SharePoint','List metadata\nRead PDF text\nUpload / replace text file',C['white'],C['orange']),
        Box('crm_api',1230,600,315,130,'Dynamics 365 / Dataverse','Native case and field permissions\nSummary column configured at deployment',C['white'],C['orange']),
        Box('identity',350,850,760,105,'AgentCore Identity — separate providers and AWS IAM boundaries','SharePoint: delegated OBO and M2M through Entra\nCRM: M2M through separate Entra app - live validation pending',C['purple_fill'],C['purple']),
        Box('audit',1190,850,390,105,'Independent operations','Separate images, credentials and rollback\nSafe audit + per-service disable',C['gray_fill'],C['line']),
    ]
    p.edges = [
        Edge('employee','gateway',source_anchor=(1,.5),target_anchor=(0,.25),points=((325,370),(325,465))),
        Edge('app','gateway',source_anchor=(1,.5),target_anchor=(0,.75),points=((325,650),(325,535))),
        Edge('entra','gateway','Validate token',source_anchor=(1,.5),target_anchor=(.5,0),points=((520,180),),arrow=False),
        Edge('gateway','sp_user',source_anchor=(1,.5),target_anchor=(0,.5),points=((710,500),(710,250))),
        Edge('gateway','sp_app',source_anchor=(1,.5),target_anchor=(0,.5),points=((710,500),(710,410))),
        Edge('gateway','crm',source_anchor=(1,.5),target_anchor=(0,.5),points=((710,500),(710,665))),
        Edge('sp_user','sharepoint',source_anchor=(1,.5),target_anchor=(0,50/260)),
        Edge('sp_app','sharepoint',source_anchor=(1,.5),target_anchor=(0,210/260)),
        Edge('crm','crm_api',source_anchor=(1,.5),target_anchor=(0,.5)),
    ]
    return p


def operations():
    p = Page('operations','Deployment and recovery',1600,680,
             'Phase-one MCP services — release, operate and recover',
             'Per-service delivery target · current SharePoint procedure · CRM live deployment pending',
             output='sharepoint-review-operations.svg')
    titles=[('source','CodeCommit','Reviewed source change\nRelease owner records version'),
            ('build','EC2 build → ECR','Build the service image\nRetain exact image version'),
            ('deploy','AgentCore Console','Deploy service + configuration\nApply reviewed permissions'),
            ('verify','Validate pilot access','Prove allowed and denied calls\nCheck data handling + recovery'),
            ('operate','Controlled operation','Approved cohort and limits\nMonitoring and on-call owner')]
    for i,(key,title,detail) in enumerate(titles):
        p.boxes.append(Box(key,30+i*320,170,260,120,title,detail))
    for a,b in zip(titles,titles[1:]):
        p.edges.append(Edge(a[0],b[0]))
    p.boxes.extend([
        Box('contain',1310,430,260,120,'Contain an incident','Disable affected caller,\noperation or target',C['red_fill'],C['red']),
        Box('restore',670,430,580,120,'Recover and verify','Restore a compatible service / configuration version\nRe-test permissions before reopening access',C['green_fill'],C['green']),
        Box('content',30,430,580,120,'Business-data recovery','SharePoint owner restores files - CRM owner corrects case data\nApplication rollback does not reverse downstream writes',C['orange_fill'],C['orange']),
    ])
    p.edges.extend([
        Edge('operate','contain','Failure or security incident',label_offset=(-205,0),color=C['red']),
        Edge('contain','restore',color=C['green']),
    ])
    return p


def render():
    pages=[phase_one_overview(),data_flow(),m2m_data_flow(),operations()]
    root=ET.Element('mxfile',host='app.diagrams.net',compressed='false',pages=str(len(pages)))
    outputs={}
    for p in pages:
        root.append(page_to_drawio(p))
        outputs[HERE/p.output]=page_to_svg(p)
    ET.indent(root,space='  ')
    outputs[HERE/'sharepoint-review-workflows.drawio']=ET.tostring(root,encoding='unicode')+'\n'
    return outputs


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--check',action='store_true')
    args=parser.parse_args()
    outputs=render()
    if args.check:
        stale=[p.name for p,s in outputs.items() if not p.exists() or p.read_text()!=s]
        if stale:
            raise SystemExit('Stale diagrams: '+', '.join(stale))
        print('SharePoint review diagrams are current')
    else:
        for p,s in outputs.items():
            p.write_text(s)
            print(p.name)
