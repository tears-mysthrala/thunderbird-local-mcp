import {createInterface} from 'node:readline/promises';
import {config,rpc} from './client.js';
import {Actions} from './actions.js';
if(!process.stdin.isTTY)throw Error('Consola interactiva independiente requerida');
const store=new Actions(config.database,config.profileId,rpc);
try{const p=store.get(process.argv[2]),status=await rpc('status');if(status.epoch!==p.action.epoch)throw Error('STALE_REFERENCE');console.log(JSON.stringify(p,null,2));const rl=createInterface({input:process.stdin,output:process.stdout});try{const answer=await rl.question(`Aplicar exactamente este plan durante 10 minutos: escribe APLICAR ${p.id} ${p.hash.slice(0,12)}: `);if(answer!==`APLICAR ${p.id} ${p.hash.slice(0,12)}`)throw Error('No aprobado');store.approve(p.id,p.hash);}finally{rl.close();}}finally{store.db.close();}
