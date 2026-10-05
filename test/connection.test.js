import test from 'node:test';
import assert from 'node:assert/strict';
import {createConnection} from '../extension/connection.js';
function fixture(){
 const events=()=>({listeners:[],addListener(fn){this.listeners.push(fn);}});
 const ports=[],timers=new Map();let timerId=0,backends=0;
 const api={storage:{local:{set:async()=>{}}},alarms:{onAlarm:events(),create:()=>{}},runtime:{id:'addon',onStartup:events(),onInstalled:events(),onMessage:events(),getManifest:()=>({version:'test'}),connectNative:()=>{const port={onDisconnect:events(),onMessage:events(),sent:[],postMessage(m){this.sent.push(m);},disconnect(){for(const fn of this.onDisconnect.listeners)fn();}};ports.push(port);return port;}}};
 const clock={setTimeout(fn,ms){const id=++timerId;timers.set(id,{fn,ms});return id;},clearTimeout(id){timers.delete(id);}};
 const connection=createConnection(api,()=>{backends++;return {epoch:'epoch',dispatch:async()=>({ok:true})};},clock);
 const bootstrap=()=>ports.at(-1).onMessage.listeners[0]({type:'configuration',protocolVersion:1,profileId:'profile',accountIds:['a'],addressBookIds:[]});
 return {api,connection,ports,timers,bootstrap,backends:()=>backends};
}
test('bootstrap completes once and reconnect does not duplicate backend listeners',async()=>{const f=fixture();assert.equal(f.ports[0].sent[0].type,'bootstrap');await f.bootstrap();assert.equal(f.connection.getState().connected,true);f.connection.reconnect();assert.equal(f.ports.length,1);[...f.timers.values()].find(t=>t.ms===1000).fn();await f.bootstrap();assert.equal(f.backends(),1);assert.equal(f.ports.length,2);});
test('stalled bootstrap disconnects and alarm can wake reconnect after timer loss',()=>{const f=fixture(),timeout=[...f.timers.values()].find(t=>t.ms===10000);timeout.fn();assert.equal(f.connection.getState().code,'BOOTSTRAP_TIMEOUT');for(const [id,t] of f.timers)if(t.ms!==10000)f.timers.delete(id);f.api.alarms.onAlarm.listeners[0]({name:'native-reconnect'});assert.equal(f.ports.length,2);});
test('disconnect diagnostic excludes native error content and external messages cannot reconnect',async()=>{const f=fixture();await f.bootstrap();f.ports[0].disconnect();assert.equal(f.connection.getState().code,'NATIVE_DISCONNECTED');const handler=f.api.runtime.onMessage.listeners[0];assert.equal(handler({method:'reconnect'},{id:'foreign'}),undefined);assert.equal(f.ports.length,1);await handler({method:'reconnect'},{id:'addon'});assert.equal(f.ports.length,2);});
test('reject invalid scope without executing requests',async()=>{const f=fixture();await f.ports[0].onMessage.listeners[0]({type:'configuration',protocolVersion:1,profileId:'p',accountIds:[42]});assert.equal(f.connection.getState().code,'INVALID_CONFIGURATION');assert.equal(f.backends(),0);});
