import test from 'node:test';
import assert from 'node:assert/strict';
import {Client} from '@modelcontextprotocol/sdk/client/index.js';
import {InMemoryTransport} from '@modelcontextprotocol/sdk/inMemory.js';
import {createServer} from '../src/server.js';
import {Actions} from '../src/actions.js';
test('MCP exposes 23 tools; schemas reject injection and there is no approval/send tool',async()=>{
 const call=async method=>method==='status'?{epoch:'00000000-0000-4000-8000-000000000001',sendingEnabled:false}:[];
 const store=new Actions(':memory:','p',call),server=createServer(call,{database:':memory:',profileId:'p'},store);
 const client=new Client({name:'test',version:'1'});const [a,b]=InMemoryTransport.createLinkedPair();await server.connect(a);await client.connect(b);
 try{const tools=(await client.listTools()).tools;assert.equal(tools.length,23);assert.ok(!tools.some(t=>/approve|send/.test(t.name)));const status=await client.callTool({name:'get_status',arguments:{}});assert.equal(JSON.parse(status.content[0].text).sendingEnabled,false);const draft=await client.callTool({name:'prepare_draft',arguments:{identityId:'id1',to:['a@example.org\r\nBcc:evil@example.org'],subject:'test',body:'test'}});assert.equal(draft.isError,true);const action=await client.callTool({name:'plan_action',arguments:{kind:'move'}});assert.equal(action.isError,true);}
 finally{await client.close();await server.close();store.db.close();}
});
