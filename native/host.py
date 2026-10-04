"""Native Messaging broker. stdout is exclusively framed protocol, never logs."""
import ctypes as C
from ctypes import wintypes as W
import json
import os
import pathlib
import struct
import sys
import threading
import time
import uuid
import sqlite3
import hashlib
from contextlib import contextmanager

@contextmanager
def connection(path,timeout=5):
    db=sqlite3.connect(path,timeout=timeout)
    try:
        with db:
            yield db
    finally:
        db.close()

from framing import encode, receive

K = C.WinDLL('kernel32', use_last_error=True)
A = C.WinDLL('advapi32', use_last_error=True)
INVALID = C.c_void_p(-1).value
K.GetCurrentProcess.restype = W.HANDLE
K.CreateNamedPipeW.argtypes = [W.LPCWSTR,W.DWORD,W.DWORD,W.DWORD,W.DWORD,W.DWORD,W.DWORD,C.c_void_p]
K.CreateNamedPipeW.restype = W.HANDLE
K.ConnectNamedPipe.argtypes = [W.HANDLE,C.c_void_p]
K.ReadFile.argtypes = [W.HANDLE,C.c_void_p,W.DWORD,C.POINTER(W.DWORD),C.c_void_p]
K.WriteFile.argtypes = [W.HANDLE,C.c_void_p,W.DWORD,C.POINTER(W.DWORD),C.c_void_p]
K.CloseHandle.argtypes = [W.HANDLE]
K.DisconnectNamedPipe.argtypes = [W.HANDLE]
K.FlushFileBuffers.argtypes = [W.HANDLE]
K.CreateMutexW.argtypes = [C.c_void_p,W.BOOL,W.LPCWSTR]
K.CreateMutexW.restype = W.HANDLE
A.OpenProcessToken.argtypes = [W.HANDLE,W.DWORD,C.POINTER(W.HANDLE)]
A.GetTokenInformation.argtypes = [W.HANDLE,C.c_int,C.c_void_p,W.DWORD,C.POINTER(W.DWORD)]
A.ConvertSidToStringSidW.argtypes = [C.c_void_p,C.POINTER(W.LPWSTR)]
A.ConvertStringSecurityDescriptorToSecurityDescriptorW.argtypes = [W.LPCWSTR,W.DWORD,C.POINTER(C.c_void_p),C.POINTER(W.DWORD)]
K.LocalFree.argtypes = [C.c_void_p]

class SECURITY_ATTRIBUTES(C.Structure):
    _fields_ = [('nLength',W.DWORD),('lpSecurityDescriptor',C.c_void_p),('bInheritHandle',W.BOOL)]

def security():
    token = W.HANDLE()
    if not A.OpenProcessToken(K.GetCurrentProcess(),8,C.byref(token)):
        raise OSError('TOKEN_FAILED')
    try:
        needed = W.DWORD()
        A.GetTokenInformation(token,1,None,0,C.byref(needed))
        buffer = C.create_string_buffer(needed.value)
        if not A.GetTokenInformation(token,1,buffer,needed,C.byref(needed)):
            raise OSError('TOKEN_FAILED')
        sid = C.cast(buffer,C.POINTER(C.c_void_p))[0]
        text = W.LPWSTR()
        if not A.ConvertSidToStringSidW(sid,C.byref(text)):
            raise OSError('SID_FAILED')
        try:
            sddl = 'D:P(A;;GA;;;%s)(A;;GA;;;SY)' % text.value
        finally:
            K.LocalFree(text)
        descriptor = C.c_void_p()
        if not A.ConvertStringSecurityDescriptorToSecurityDescriptorW(sddl,1,C.byref(descriptor),None):
            raise OSError('ACL_FAILED')
        return SECURITY_ATTRIBUTES(C.sizeof(SECURITY_ATTRIBUTES),descriptor,False), sddl
    finally:
        K.CloseHandle(token)

def pipe_read(handle,size):
    data = C.create_string_buffer(min(size,65536))
    count = W.DWORD()
    if not K.ReadFile(handle,data,len(data),C.byref(count),None):
        raise EOFError()
    return data.raw[:count.value]

def pipe_write(handle,data):
    offset = 0
    while offset < len(data):
        block = data[offset:offset+65536]
        count = W.DWORD()
        if not K.WriteFile(handle,block,len(block),C.byref(count),None) or not count.value:
            raise EOFError()
        offset += count.value

class Broker:
    def __init__(self, config, output):
        self.config = config
        self.output = output
        self.lock = threading.Lock()
        self.pending = {}
        self.pending_lock = threading.Lock()
        self.ready = False
        self.epoch = None
        self.stopped = threading.Event()

    def accept_native(self,message):
        if message.get('type') == 'bootstrap':
            with self.lock:
                self.output.write(encode({'type':'configuration','protocolVersion':1,'profileId':self.config['profileId'],'accountIds':self.config['accountIds'],'addressBookIds':self.config.get('addressBookIds',[])}))
                self.output.flush()
            return
        if message.get('type') == 'hello':
            if message.get('profileId') != self.config['profileId']:
                self.stopped.set()
                return
            self.ready = True
            self.epoch = message.get('epoch')
            return
        with self.pending_lock:
            waiter = self.pending.get(message.get('id'))
            if waiter:
                waiter['result'] = message
                waiter['event'].set()

    def request(self,request):
        if not self.ready or self.stopped.is_set():
            return {'error': {'code':'TB_CLOSED','message':'Thunderbird no conectado'}}
        if request.get('profileId') != self.config['profileId']:
            return {'error': {'code':'PROFILE_MISMATCH','message':'Perfil distinto'}}
        allowed = {'status','accounts','folders','folder_status','search','next','cancel_search','read','headers','attachment','export','books','contacts','tags','events','apply_action'}
        if request.get('method') not in allowed:
            return {'error': {'code':'UNSUPPORTED_METHOD','message':'Metodo no permitido'}}
        with self.pending_lock:
            if len(self.pending) >= 8:
                return {'error': {'code':'BUSY','message':'Limite de solicitudes'}}
        action_id = None
        if request.get('method') == 'apply_action':
            params = request.get('params',{})
            with connection(self.config['database'],timeout=5) as db:
                # BEGIN IMMEDIATE serializes approval read/check/claim across all connections.
                db.execute('BEGIN IMMEDIATE')
                row = db.execute('SELECT content,hash,state,until FROM actions WHERE id=? AND profile=?',(params.get('id'),self.config['profileId'])).fetchone()
                if not row or row[2]!='planned' or not row[3] or row[3] <= int(time.time()*1000) or row[1]!=params.get('hash'):
                    return {'error': {'code':'LOCAL_APPROVAL_REQUIRED','message':'Sin aprobacion local'}}
                action = json.loads(row[0])
                if action.get('epoch')!=self.epoch or hashlib.sha256(row[0].encode()).hexdigest()!=row[1]:
                    return {'error': {'code':'STALE_REFERENCE','message':'Operacion obsoleta'}}
                claimed=db.execute("UPDATE actions SET state='executing',until=NULL WHERE id=? AND state='planned' AND hash=?",(params['id'],row[1])).rowcount
                if claimed!=1:
                    return {'error': {'code':'LOCAL_APPROVAL_REQUIRED','message':'Plan consumido'}}
                action_id = params['id']
                request = dict(request,method='execute',params={'action':action})
        identifier = str(uuid.uuid4())
        waiter = {'event':threading.Event()}
        with self.pending_lock:
            if len(self.pending) >= 8:
                if action_id:
                    with connection(self.config['database'],timeout=5) as db:
                        db.execute("UPDATE actions SET state='uncertain' WHERE id=?",(action_id,))
                return {'error': {'code':'BUSY','message':'Limite de solicitudes'}}
            self.pending[identifier] = waiter
        try:
            request = dict(request, id=identifier)
            with self.lock:
                self.output.write(encode(request))
                self.output.flush()
            if not waiter['event'].wait(45):
                response = {'error': {'code':'UNCERTAIN' if action_id else 'TIMEOUT','message':'Sin confirmacion; no repetir escrituras'}}
            else:
                response = waiter['result']
            if action_id:
                with connection(self.config['database'],timeout=5) as db:
                    db.execute('UPDATE actions SET state=?,result=? WHERE id=?',('uncertain' if response.get('error') else 'completed',json.dumps(response.get('result')),action_id))
            return response
        except Exception:
            if action_id:
                with connection(self.config['database'],timeout=5) as db:
                    db.execute("UPDATE actions SET state='uncertain' WHERE id=?",(action_id,))
            raise
        finally:
            with self.pending_lock:
                self.pending.pop(identifier,None)

    def client(self,handle):
        try:
            request = receive(lambda n:pipe_read(handle,n))
            pipe_write(handle,encode(self.request(request)))
            K.FlushFileBuffers(handle)
        except Exception:
            pass
        finally:
            K.DisconnectNamedPipe(handle)
            K.CloseHandle(handle)

def main():
    if os.name != 'nt':
        raise RuntimeError('WINDOWS_ONLY')
    import msvcrt
    msvcrt.setmode(sys.stdin.fileno(), os.O_BINARY)
    msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)
    config_path=pathlib.Path(os.environ.get('THUNDERBIRD_MCP_CONFIG',str(pathlib.Path(__file__).parents[1]/'runtime/config.json')))
    config = json.loads(config_path.read_text(encoding='utf-8-sig'))
    # Mozilla passes manifest path and extension ID. Reject unrelated invocations.
    if len(sys.argv)<3 or sys.argv[-1] != config['extensionId']:
        raise RuntimeError('EXTENSION_MISMATCH')
    attrs, sddl = security()
    mutex = K.CreateMutexW(C.byref(attrs),False,'Local\\ThunderbirdMCP-'+config['profileId'])
    if not mutex or C.get_last_error() == 183:
        raise RuntimeError('BROKER_ALREADY_RUNNING')
    broker = Broker(config,sys.stdout.buffer)
    def reader():
        try:
            while True:
                broker.accept_native(receive(sys.stdin.buffer.read))
        except (EOFError,ValueError):
            broker.stopped.set()
            os._exit(0) # All pipe handles close; outstanding writes remain uncertain in MCP store.
    threading.Thread(target=reader,daemon=True).start()
    while not broker.stopped.is_set():
        handle = K.CreateNamedPipeW(config['pipe'],3,8,8,1048576,1048576,0,C.byref(attrs))
        if handle == INVALID:
            if C.get_last_error()==231:
                time.sleep(.05)
                continue
            raise OSError('PIPE_FAILED')
        if K.ConnectNamedPipe(handle,None) or C.get_last_error()==535:
            threading.Thread(target=broker.client,args=(handle,),daemon=True).start()
        else:
            K.CloseHandle(handle)

if __name__ == '__main__':
    try:
        main()
    except Exception:
        # Never include native messages, usernames, credentials or mail in diagnostics.
        sys.stderr.write('Thunderbird MCP native host failed\n')
        sys.exit(1)
