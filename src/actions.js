import {DatabaseSync} from 'node:sqlite';
import {randomUUID,createHash} from 'node:crypto';
export class Actions{
 constructor(file,profileId,call){this.db=new DatabaseSync(file);this.db.exec('PRAGMA journal_mode=WAL; PRAGMA busy_timeout=5000; CREATE TABLE IF NOT EXISTS actions(id TEXT PRIMARY KEY,profile TEXT NOT NULL,content TEXT NOT NULL,hash TEXT NOT NULL,state TEXT NOT NULL,until INTEGER,result TEXT)');this.profileId=profileId;this.call=call;}
 plan(action){const id=randomUUID(),content=JSON.stringify(action),hash=createHash('sha256').update(content).digest('hex');this.db.prepare("INSERT INTO actions(id,profile,content,hash,state) VALUES(?,?,?,?,'planned')").run(id,this.profileId,content,hash);return this.get(id);}
 get(id){const p=this.db.prepare('SELECT * FROM actions WHERE id=? AND profile=?').get(id,this.profileId);if(!p)throw Error('UNKNOWN_ACTION');return {id:p.id,hash:p.hash,action:JSON.parse(p.content),state:p.state,approved:p.until>Date.now(),result:p.result?JSON.parse(p.result):null};}
 approve(id,hash){if(!this.db.prepare("UPDATE actions SET until=? WHERE id=? AND profile=? AND hash=? AND state='planned'").run(Date.now()+600000,id,this.profileId,hash).changes)throw Error('ACTION_BLOCKED');}
 cancel(id){if(!this.db.prepare("UPDATE actions SET state='cancelled',until=NULL WHERE id=? AND profile=? AND state='planned'").run(id,this.profileId).changes)throw Error('ACTION_BLOCKED');return this.get(id);}
 async execute(id){const p=this.get(id),status=await this.call('status');if(status.epoch!==p.action.epoch)throw Error('STALE_REFERENCE');await this.call('apply_action',{id,hash:p.hash});return this.get(id);}
}
