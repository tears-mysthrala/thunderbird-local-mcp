// Timers retry while awake; alarms wake the MV3 event page after suspension.
export function createConnection(api,makeBackend,clock=globalThis){
 let port=null,backend=null,scope=null,ready=false,delay=1000,retry=null,handshake=null;
 let state={connected:false,code:'STARTING',attempts:0,changedAt:Date.now()};
 const save=(code,connected=false)=>{state={...state,connected,code,changedAt:Date.now()};api.storage.local.set({connection:state}).catch(()=>{});};
 function schedule(){if(retry!==null)return;retry=clock.setTimeout(()=>{retry=null;connect();},delay);delay=Math.min(delay*2,30000);}
 function drop(current,code){if(port!==current)return;port=null;ready=false;if(handshake!==null)clock.clearTimeout(handshake);handshake=null;save(code);try{current.disconnect();}catch{}schedule();}
 function connect(){
  if(port)return;
  if(retry!==null){clock.clearTimeout(retry);retry=null;}
  state.attempts++;save('CONNECTING');
  let current;
  try{
   current=api.runtime.connectNative('mkdl.thunderbird.local');port=current;
   current.onDisconnect.addListener(()=>drop(current,'NATIVE_DISCONNECTED'));
   current.onMessage.addListener(async request=>{
    if(port!==current)return;
    if(request.type==='configuration'){
     if(ready||request.protocolVersion!==1||typeof request.profileId!=='string'||!Array.isArray(request.accountIds)||request.accountIds.some(id=>typeof id!=='string')||!Array.isArray(request.addressBookIds||[])||(request.addressBookIds||[]).some(id=>typeof id!=='string'))return drop(current,'INVALID_CONFIGURATION');
     const next={profileId:request.profileId,accountIds:request.accountIds,addressBookIds:request.addressBookIds||[]};
     if(!backend||JSON.stringify(next)!==JSON.stringify(scope)){backend?.dispose?.();scope=next;backend=makeBackend(api,scope);}
     clock.clearTimeout(handshake);handshake=null;ready=true;delay=1000;
     try{current.postMessage({type:'hello',profileId:scope.profileId,epoch:backend.epoch});save('CONNECTED',true);}catch{drop(current,'HELLO_FAILED');}
     return;
    }
    let reply;
    try{if(!ready)throw Object.assign(Error(),{code:'NOT_READY'});if(request.profileId!==scope.profileId)throw Object.assign(Error(),{code:'PROFILE_MISMATCH'});reply={id:request.id,result:await backend.dispatch(request.method,request.params)};}
    catch(error){reply={id:request.id,error:{code:error.code||'API_ERROR',message:error.code||'Operacion Thunderbird fallida'}};}
    try{if(new TextEncoder().encode(JSON.stringify(reply)).length>1048576)reply={id:request.id,error:{code:'FRAME_TOO_LARGE'}};if(port===current)current.postMessage(reply);}catch{drop(current,'RESPONSE_FAILED');}
   });
   handshake=clock.setTimeout(()=>drop(current,'BOOTSTRAP_TIMEOUT'),10000);
   current.postMessage({type:'bootstrap'});
  }catch{if(current)drop(current,'NATIVE_CONNECT_FAILED');else{save('NATIVE_CONNECT_FAILED');schedule();}}
 }
 // Let the old native process release its mutex before the bounded retry.
 function reconnect(){if(port)drop(port,'RECONNECT_REQUESTED');else connect();}
 // Register synchronously before connecting: these listeners wake the event page.
 api.runtime.onStartup.addListener(connect);
 api.runtime.onInstalled.addListener(connect);
 api.alarms.onAlarm.addListener(alarm=>{if(alarm.name==='native-reconnect')connect();});
 api.alarms.create('native-reconnect',{periodInMinutes:1});
 api.runtime.onMessage.addListener((message,sender)=>{
  if(sender.id!==api.runtime.id)return;
  if(message?.method==='diagnostics')return Promise.resolve({...state,addonVersion:api.runtime.getManifest().version});
  if(message?.method==='reconnect'){reconnect();return Promise.resolve({requested:true});}
 });
 connect();
 return {connect,reconnect,getState:()=>({...state})};
}
