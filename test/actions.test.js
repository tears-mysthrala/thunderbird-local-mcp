import test from 'node:test';
import assert from 'node:assert/strict';
import {Actions} from '../src/actions.js';
test('immutable plan approval binds hash; cancelled plan cannot execute',()=>{const store=new Actions(':memory:','p',()=>{}),p=store.plan({epoch:'e',kind:'update'});assert.equal(p.approved,false);assert.throws(()=>store.approve(p.id,'wrong'),/ACTION_BLOCKED/);store.approve(p.id,p.hash);assert.equal(store.get(p.id).approved,true);store.cancel(p.id);assert.equal(store.get(p.id).state,'cancelled');assert.throws(()=>store.approve(p.id,p.hash),/ACTION_BLOCKED/);store.db.close();});
test('execution refuses stale epoch before contacting apply_action',async()=>{let calls=0;const store=new Actions(':memory:','p',async()=>{calls++;return {epoch:'new'};}),p=store.plan({epoch:'old',kind:'update'});await assert.rejects(store.execute(p.id),/STALE_REFERENCE/);assert.equal(calls,1);store.db.close();});
