import {readFileSync} from 'node:fs';
import {dirname,join} from 'node:path';
import {fileURLToPath} from 'node:url';
import {config,configPath,rpc} from './client.js';
export async function diagnostics(){
 if(!config)return {configured:false,connected:false,code:'CONFIG_REQUIRED'};
 try{return {configured:true,connected:true,status:await rpc('status',{},5000)};}
 catch(error){let native=null;try{const value=JSON.parse(readFileSync(join(dirname(configPath instanceof URL?fileURLToPath(configPath):configPath),'native-status.json'),'utf8'));native={code:value.code,changedAt:value.changedAt};}catch{}
 return {configured:true,connected:false,code:error.code||'CONNECTION_FAILED',native,nextAction:'Consultar Preferencias del complemento > Reconectar; comprobar registro Native Messaging si persiste'};}
}
