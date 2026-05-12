#!/usr/bin/env python3
import time, json, os
WORKSPACE = os.path.join(os.path.dirname(__file__),'..','..','workspace')
TASK_QUEUE = os.path.join(WORKSPACE,'tasks.jsonl')

os.makedirs(WORKSPACE, exist_ok=True)

def poll():
    while True:
        if not os.path.exists(TASK_QUEUE):
            time.sleep(1); continue
        with open(TASK_QUEUE,'r',encoding='utf-8') as f:
            lines = f.readlines()
        remaining=[]
        for ln in lines:
            try:
                t=json.loads(ln)
            except:
                continue
            if t.get('status')=='queued' and t.get('to')=='worker_fetcher':
                print('handling',t['task_id'])
                # example: perform fetch (placeholder)
                result={'task_id':t['task_id'],'from':'worker_fetcher','status':'done','result':{'fetched':'ok'}}
                with open(os.path.join(WORKSPACE,'tasks_results.jsonl'),'a',encoding='utf-8') as rf:
                    rf.write(json.dumps(result,ensure_ascii=False)+'\n')
                t['status']='done'
                remaining.append(json.dumps(t,ensure_ascii=False)+'\n')
            else:
                remaining.append(json.dumps(t,ensure_ascii=False)+'\n')
        with open(TASK_QUEUE,'w',encoding='utf-8') as f:
            f.writelines(remaining)
        time.sleep(2)

if __name__=='__main__':
    poll()
