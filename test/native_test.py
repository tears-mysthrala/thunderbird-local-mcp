import io, json, pathlib, sys, tempfile, threading, unittest, sqlite3, hashlib, time
sys.path.insert(0,str(pathlib.Path(__file__).parents[1]/'native'))
from framing import encode,receive
from host import Broker,security

class NativeTests(unittest.TestCase):
 def test_frames(self):
  packet=encode({'text':'á😀'})
  stream=io.BytesIO(packet)
  self.assertEqual(receive(lambda n:stream.read(min(n,2))),{'text':'á😀'})
  with self.assertRaises(ValueError): receive(io.BytesIO(b'\xff\xff\xff\xff').read)
 def test_bootstrap_only_returns_scope_not_paths(self):
  output=io.BytesIO()
  broker=Broker({'profileId':'p','accountIds':['a'],'database':'private-path','extensionId':'id'},output)
  broker.accept_native({'type':'bootstrap'})
  result=receive(io.BytesIO(output.getvalue()).read)
  self.assertEqual(result,{'type':'configuration','protocolVersion':1,'profileId':'p','accountIds':['a'],'addressBookIds':[]})
 def test_acl(self):
  attrs,sddl=security()
  self.assertIn('D:P(A;;GA;;;S-1-5-21-',sddl)
  self.assertTrue(sddl.endswith('(A;;GA;;;SY)'))
  self.assertNotIn(';;;WD)',sddl)
 def test_approval_boundary(self):
  with tempfile.TemporaryDirectory() as directory:
   path=str(pathlib.Path(directory)/'a.sqlite')
   db=sqlite3.connect(path);db.execute('CREATE TABLE actions(id TEXT PRIMARY KEY,profile TEXT,content TEXT,hash TEXT,state TEXT,until INTEGER,result TEXT)')
   content=json.dumps({'kind':'update','epoch':'e'});digest=hashlib.sha256(content.encode()).hexdigest()
   db.execute('INSERT INTO actions VALUES(?,?,?,?,?,?,?)',('a','p',content,digest,'planned',None,None));db.commit()
   output=io.BytesIO();broker=Broker({'profileId':'p','database':path},output);broker.accept_native({'type':'hello','profileId':'p','epoch':'e'})
   req={'profileId':'p','method':'apply_action','params':{'id':'a','hash':digest}}
   self.assertEqual(broker.request(dict(req,method='execute'))['error']['code'],'UNSUPPORTED_METHOD')
   self.assertEqual(broker.request(req)['error']['code'],'LOCAL_APPROVAL_REQUIRED')
   db.execute('UPDATE actions SET until=?',(int(time.time()*1000)+60000,));db.commit()
   def respond():
    for _ in range(100):
     raw=output.getvalue()
     if raw:
      message=receive(io.BytesIO(raw).read)
      self.assertEqual(message['method'],'execute')
      broker.accept_native({'id':message['id'],'result':{'ok':True}});return
     time.sleep(.01)
   worker=threading.Thread(target=respond);worker.start()
   self.assertTrue(broker.request(req)['result']['ok']);worker.join()
   self.assertEqual(db.execute('SELECT state FROM actions').fetchone()[0],'completed')
   self.assertEqual(broker.request(req)['error']['code'],'LOCAL_APPROVAL_REQUIRED')
   db.close()
if __name__=='__main__':unittest.main()
