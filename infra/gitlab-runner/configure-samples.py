#!/usr/bin/env python3
"""Provision the local sample validation project and its isolated resources."""
import base64, copy, importlib.util, json, secrets, subprocess, sys
from pathlib import Path
from xml.sax.saxutils import escape
import configure as c
sys.path.insert(0,str(c.CI / 'infra/artifactory'))
import bootstrap as jfrog

state_path=c.PRIVATE/'samples-project.json'
if state_path.exists():
    project=json.loads(state_path.read_text())
else:
    project=c.api('/projects','POST',{'name':'CI samples','path':'ci-samples','visibility':'private',
        'initialize_with_readme':True,'default_branch':'main','description':'Runnable consumer examples and integration validation of CI modules'})
    c.save(state_path,json.dumps({'id':project['id'],'path_with_namespace':project['path_with_namespace']}))
pid=project['id']
# configure.py registers dedicated sample runners on the shared local manager.
variables=c.api(f'/projects/{c.PROJECT}/variables?per_page=100')
for key in ('JAVA_CI_IMAGE','HELM_CI_IMAGE','JAVA_RUNTIME_IMAGE','NODE_CI_IMAGE','BUILDKIT_CI_IMAGE','BROWSER_CI_IMAGE','NGINX_RUNTIME_IMAGE','DOCKER_AUTH_CONFIG'):
    v=next(v for v in variables if v['key']==key and v['environment_scope']=='*')
    c.variable(key,v['value'],masked=key=='DOCKER_AUTH_CONFIG',project=pid)

creds=json.loads((jfrog.PRIVATE/'credentials.json').read_text())
session=jfrog.ui_session(creds['admin'])
account_path=c.PRIVATE/'samples-registry.json'
if not account_path.exists():c.save(account_path,json.dumps({'username':'local-samples','password':secrets.token_urlsafe(32)}))
account=json.loads(account_path.read_text())
existing=jfrog.ui_api('/users/'+account['username'],session)
if existing[0]==404:
    jfrog.require_success(jfrog.ui_api('/users',session,'POST',{**account,'email':'local-samples@localhost.invalid','admin':False,'profileUpdatable':False,'disableUiAccess':True,'groups':[]}),'Create samples account')
else:jfrog.require_success(existing,'Read samples account')
for name,rights,patterns in [('local-samples-publisher',['READ','WRITE','ANNOTATE'],['root-ci-samples/**']),('local-samples-base-images',['READ'],['**'])]:
    expected={'name':name,'resources':{'artifact':{'actions':{'users':{account['username']:rights}},'targets':{'docker-local':{'include_patterns':patterns}}}}}
    existing=jfrog.ui_api('/permissions/'+name,session)
    if existing[0]==404:jfrog.require_success(jfrog.ui_api('/permissions',session,'POST',expected),name)
    else:
        jfrog.require_success(existing,name)
        actual=json.loads(existing[1])['resources']['artifact']
        assert set(actual['targets'])=={'docker-local'}
        assert actual['targets']['docker-local']['include_patterns']==patterns
        assert set(actual['actions']['users'][account['username']])==set(rights)
c.variable('ARTIFACTORY_USERNAME',account['username'],project=pid)
c.variable('ARTIFACTORY_PASSWORD_FILE',account['password'],file=True,masked=True,project=pid)
settings='<settings><servers>'+''.join(f'<server><id>{host}</id><username>{escape(account["username"])}</username><password>{escape(account["password"])}</password></server>' for host in ['localhost:8082','host.docker.internal:8082'])+'</servers></settings>'
c.variable('ARTIFACTORY_MAVEN_SETTINGS',settings,file=True,project=pid)

def kubectl(*args,input=None):
    return subprocess.check_output(['docker','exec','-i','desktop-control-plane','kubectl','--kubeconfig','/etc/kubernetes/admin.conf',*args],input=input,text=True)
namespace={'apiVersion':'v1','kind':'Namespace','metadata':{'name':'ci-samples'}}
print(kubectl('apply','-f','-',input=json.dumps(namespace)).strip())
rbac=(c.ROOT/'kubernetes.yaml').read_text().replace('namespace: hello-world','namespace: ci-samples')
print(kubectl('apply','-f','-',input=rbac).strip())
pull=json.loads(kubectl('-n','hello-world','get','secret','local-artifactory','-o','json'))
pull['metadata']={'name':'local-artifactory','namespace':'ci-samples'}
print(kubectl('apply','-f','-',input=json.dumps(pull)).strip())
secret=json.loads(kubectl('-n','ci-samples','get','secret','gitlab-deployer-token','-o','json'))
kube=json.loads((c.PRIVATE/'kubeconfig.json').read_text())
kube['users'][0]['user']={'token':base64.b64decode(secret['data']['token']).decode()}
kube['contexts'][0]['context']['namespace']='ci-samples'
c.save(c.PRIVATE/'samples-kubeconfig.json',json.dumps(kube))
c.variable('SAMPLE_KUBECONFIG',json.dumps(kube),file=True,project=pid)
print('Sample project ready',pid,project['path_with_namespace'])
