// Run by the user in an independent interactive console. No automatic approval.
import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import {config,rpc} from '../src/client.js';
import {Actions} from '../src/actions.js';
if(!process.stdin.isTTY)throw Error('Consola humana independiente requerida');
const parentFolderId=process.argv[2];if(!parentFolderId)throw Error('Indica el ID exacto de una carpeta padre local');
const accounts=await rpc('accounts'),local=accounts.filter(a=>a.type==='local');
const folders=(await Promise.all(local.map(a=>rpc('folders',{accountId:a.id})))).flat();
if(!folders.some(f=>f.id===parentFolderId))throw Error('La carpeta padre debe pertenecer a Carpetas locales');
const store=new Actions(config.database,config.profileId,rpc);
async function step(action){const status=await rpc('status'),plan=store.plan({...action,epoch:status.epoch});console.log('Plan de prueba:',plan.id);const approval=spawnSync(process.execPath,[fileURLToPath(new URL('../src/approve.js',import.meta.url)),plan.id],{stdio:'inherit'});if(approval.status!==0){store.cancel(plan.id);throw Error('Prueba detenida sin aprobacion');}const result=await store.execute(plan.id);if(result.state!=='completed')throw Error('Reconciliar manualmente; no repetir: '+result.state);return result.result;}
try{const name='MCP-test-'+Date.now(),created=await step({kind:'create_folder',parentFolderId,name});console.log('Carpeta creada:',created.id);await step({kind:'rename_folder',folderId:created.id,name:name+'-renamed'});const renamed=(await rpc('folders',{accountId:created.accountId})).find(f=>f.name===name+'-renamed');if(!renamed)throw Error('No se localiza carpeta renombrada; revisar manualmente');await step({kind:'delete_folder',folderId:renamed.id});console.log('PASS: crear, renombrar y eliminar carpeta local vacia, con tres aprobaciones humanas.');}finally{store.db.close();}
