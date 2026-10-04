"""Real Windows named pipe and native framing, synthetic addon, no mail access."""
import json,pathlib,subprocess,sys,time,threading,ctypes,tempfile,uuid,os
root=pathlib.Path(__file__).parents[1]
sys.path.insert(0,str(root/'native'))
from framing import encode,receive
from host import K,W,INVALID,pipe_read,pipe_write
temporary=tempfile.TemporaryDirectory()
binding=str(uuid.uuid4())
config={'profileId':binding,'accountIds':['synthetic-account'],'addressBookIds':[],'extensionId':'synthetic@local','pipe':r'\\.\pipe\thunderbird-test-'+binding,'database':str(pathlib.Path(temporary.name)/'test.sqlite')}
config_file=pathlib.Path(temporary.name)/'config.json'
config_file.write_text(json.dumps(config),encoding='utf-8')
K.CreateFileW.argtypes=[W.LPCWSTR,W.DWORD,W.DWORD,ctypes.c_void_p,W.DWORD,W.DWORD,W.HANDLE]
K.CreateFileW.restype=W.HANDLE
process=subprocess.Popen([sys.executable,'-u',str(root/'native/host.py'),'manifest',config['extensionId']],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=dict(os.environ,THUNDERBIRD_MCP_CONFIG=str(config_file)))
try:
 process.stdin.write(encode({'type':'bootstrap'}));process.stdin.flush()
 bootstrap=receive(process.stdout.read)
 assert bootstrap['type']=='configuration' and bootstrap['profileId']==binding and 'database' not in bootstrap
 process.stdin.write(encode({'type':'hello','profileId':config['profileId'],'epoch':'synthetic'}));process.stdin.flush()
 def addon():
  request=receive(process.stdout.read)
  assert request['method']=='status'
  process.stdin.write(encode({'id':request['id'],'result':{'synthetic':True,'epoch':'synthetic'}}));process.stdin.flush()
 worker=threading.Thread(target=addon);worker.start()
 for attempt in range(100):
  handle=K.CreateFileW(config['pipe'],0xC0000000,0,None,3,0,None)
  if handle!=INVALID:break
  time.sleep(.02)
 else:raise RuntimeError('PIPE_NOT_AVAILABLE')
 pipe_write(handle,encode({'profileId':config['profileId'],'method':'status','params':{}}))
 response=receive(lambda n:pipe_read(handle,n));K.CloseHandle(handle)
 assert response['result']['synthetic'] is True
 worker.join(5);assert not worker.is_alive()
 print('PASS: real named pipe -> native stdout -> synthetic addon -> framed response')
finally:
 process.stdin.close()
 try:process.wait(timeout=5)
 except subprocess.TimeoutExpired:process.kill();process.wait()
 assert process.returncode==0,process.stderr.read().decode()
 temporary.cleanup()
