import {createBackend} from './core.js';
let connecting=false,delay=1000,backend=null,config=null;
function connect(){
 if(connecting)return;connecting=true;
 try{
  const port=browser.runtime.connectNative('mkdl.thunderbird.local');
  let initialized=false;
  port.onMessage.addListener(async request=>{
   if(request.type==='configuration'){
    if(initialized||request.protocolVersion!==1||typeof request.profileId!=='string'||!Array.isArray(request.accountIds)){port.disconnect();return;}
    const next={profileId:request.profileId,accountIds:request.accountIds,addressBookIds:request.addressBookIds||[]};
    if(!backend||JSON.stringify(next)!==JSON.stringify(config)){config=next;backend=createBackend(browser,config);}initialized=true;delay=1000;
    port.postMessage({type:'hello',profileId:config.profileId,epoch:backend.epoch});return;
   }
   let reply;
   try{
    if(!initialized)throw Object.assign(Error(),{code:'NOT_READY'});
    if(request.profileId!==config.profileId)throw Object.assign(Error(),{code:'PROFILE_MISMATCH'});
    reply={id:request.id,result:await backend.dispatch(request.method,request.params)};
   }catch(e){reply={id:request.id,error:{code:e.code||'API_ERROR',message:e.code||'Operacion Thunderbird fallida'}};}
   try{if(new TextEncoder().encode(JSON.stringify(reply)).length>1048576)throw Error();port.postMessage(reply);}
   catch{try{port.postMessage({id:request.id,error:{code:'FRAME_TOO_LARGE',message:'Respuesta demasiado grande'}});}catch{}}
  });
  port.onDisconnect.addListener(()=>{connecting=false;setTimeout(connect,delay);delay=Math.min(delay*2,30000);});
  port.postMessage({type:'bootstrap'});
 }catch{connecting=false;setTimeout(connect,delay);delay=Math.min(delay*2,30000);}
}
connect();
