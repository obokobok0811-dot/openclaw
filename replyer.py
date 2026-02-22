#!/usr/bin/env python3
import time, json, os, urllib.request, urllib.parse

# replyer: watches workspace/forwarded_messages.jsonl and replies using available bot credentials
FW='workspace/forwarded_messages.jsonl'
CRED_DIR='credentials'
LOG='logs/replyer.log'
CONFIG_PATH='config/model_fallback.json'

# load fallback configuration (if present)
fallback_conf = None
if os.path.exists(CONFIG_PATH):
    try:
        fallback_conf = json.load(open(CONFIG_PATH,encoding='utf-8'))
    except Exception:
        fallback_conf = None

# load credentials mapping: bot label lowercase -> token
creds = {}
for fn in os.listdir(CRED_DIR):
    if not fn.endswith('.json'):
        continue
    path=os.path.join(CRED_DIR,fn)
    try:
        d=json.load(open(path,encoding='utf-8'))
        token = d.get('token') or d.get('bot_token')
        name = d.get('botName') or d.get('username') or os.path.splitext(fn)[0]
        creds[name.lower()] = {'token':token, 'path':path}
    except Exception:
        continue

print('Loaded creds for bots:', list(creds.keys()))

from collections import deque
MAX_RECENT=1000
recent_global=deque([], maxlen=MAX_RECENT)
recent_set=set()

processed_marker = 'workspace/forwarded_processed.marker'
if not os.path.exists('logs'):
    os.makedirs('logs')

# Simple LLM call wrapper with fallback sequence read from config/model_fallback.json
# NOTE: This wrapper logs attempts and will try models listed in the config. Actual model calls
# require appropriate SDK/endpoint configuration (LLM_API_URLs/keys). At minimum this implements
# the control flow and logs fallback attempts.

def log(msg):
    with open(LOG,'a',encoding='utf-8') as lg:
        lg.write(msg + '\n')


def call_model_once(model_name, prompt, timeout=20):
    """Attempt to call a model by name. This implementation tries to use environment
    variables that follow the pattern LLM_API_URL_<MODEL> and LLM_API_KEY_<MODEL> (uppercased, dashes->underscores).
    If no endpoint is configured, it logs and returns None.
    """
    keyname = model_name.upper().replace('-', '_')
    api_url = os.environ.get(f'LLM_API_URL_{keyname}')
    api_key = os.environ.get(f'LLM_API_KEY_{keyname}')
    # As a convenience, also try generic LLM_API_URL and LLM_API_KEY if single provider
    if not api_url:
        api_url = os.environ.get('LLM_API_URL')
    if not api_key:
        api_key = os.environ.get('LLM_API_KEY')
    log(f'Attempting model {model_name} (url set: {bool(api_url)})')
    if not api_url:
        log(f'No API URL configured for model {model_name}; skipping')
        return None
    # make a simple HTTP POST to the configured API URL with minimal JSON payload
    try:
        import json as _json
        data = _json.dumps({'model': model_name, 'prompt': prompt}).encode('utf-8')
        req = urllib.request.Request(api_url, data=data, headers={'Content-Type':'application/json'})
        if api_key:
            req.add_header('Authorization', f'Bearer {api_key}')
        resp = urllib.request.urlopen(req, timeout=timeout)
        body = resp.read().decode('utf-8')
        # Attempt to parse JSON and extract text in common fields
        try:
            j = _json.loads(body)
            # common fields: 'text' or 'result' or 'output'
            for k in ('text','result','output','completion'):
                if k in j and isinstance(j[k], str) and j[k].strip():
                    return j[k].strip()
            # OpenAI-like: choices[0].text
            if 'choices' in j and isinstance(j['choices'], list) and len(j['choices'])>0:
                c = j['choices'][0]
                if isinstance(c, dict) and 'text' in c and isinstance(c['text'], str):
                    return c['text'].strip()
        except Exception:
            # not JSON or unexpected structure; return raw body if non-empty
            if body.strip():
                return body.strip()
        return None
    except Exception as e:
        log(f'model {model_name} call error: {e}')
        return None


def call_model_with_fallback(prompt, specified_model=None):
    """Call a model. If specified_model is provided, try it only. Otherwise use sequence from config.
    Returns text or None.
    """
    sequence = None
    timeout = 20
    if fallback_conf and fallback_conf.get('enabled'):
        sequence = fallback_conf.get('default_sequence')
        timeout = int(fallback_conf.get('per_call_timeout_sec', 20))
    if specified_model:
        sequence = [specified_model]
    if not sequence:
        # no fallback configured; nothing to do
        log('No model sequence configured; skipping LLM call')
        return None
    for model in sequence:
        txt = call_model_once(model, prompt, timeout=timeout)
        if txt and txt.strip():
            log(f'model {model} returned response (len {len(txt)})')
            if fallback_conf and fallback_conf.get('log_fallbacks_to'):
                with open(fallback_conf.get('log_fallbacks_to'), 'a', encoding='utf-8') as lf:
                    lf.write(f'fallback_used: model={model}\n')
            return txt
        else:
            log(f'model {model} returned empty or failed; trying next')
    return None


while True:
    try:
        if not os.path.exists(FW):
            time.sleep(1)
            continue
        with open(FW,'r',encoding='utf-8') as f:
            lines = f.read().splitlines()
        # track processed via marker file storing count
        last = 0
        if os.path.exists(processed_marker):
            try:
                last = int(open(processed_marker).read().strip())
            except:
                last = 0
        new = lines[last:]
        if not new:
            time.sleep(1)
            continue
        # simple in-memory dedupe: remember recent (bot,chat_id,text) to avoid duplicate replies
        recent = set()
        for i,l in enumerate(new, start=last):
            try:
                payload=json.loads(l)
            except Exception:
                with open(LOG,'a',encoding='utf-8') as lg:
                    lg.write('malformed line skip\n')
                continue
            bot_label = payload.get('bot','').lower()
            text = payload.get('text','')
            chat_id = payload.get('chat_id')
            from_id = payload.get('from_id')
            key = (bot_label, str(chat_id), text.strip())
            # global dedupe: skip if we've recently processed the same (bot,chat,text)
            if key in recent_set:
                with open(LOG,'a',encoding='utf-8') as lg:
                    lg.write(f'skipping global duplicate for {key}\n')
                last = i+1
                open(processed_marker,'w').write(str(last))
                continue
            if key in recent:
                # skip duplicate entry in this batch
                with open(LOG,'a',encoding='utf-8') as lg:
                    lg.write(f'skipping duplicate in batch for {key}\n')
                last = i+1
                open(processed_marker,'w').write(str(last))
                continue
            recent.add(key)
            # push to global recent cache
            recent_global.append(key)
            recent_set.add(key)
            # choose token
            token=None
            if bot_label in creds and creds[bot_label].get('token'):
                token=creds[bot_label]['token']
            else:
                for k,v in creds.items():
                    if k in bot_label or bot_label in k:
                        token=v.get('token')
                        break
            if not token:
                with open(LOG,'a',encoding='utf-8') as lg:
                    lg.write(f'No token for bot {bot_label}\n')
                continue
            # generate reply
            lt = text.lower()
            reply = None
            # If this is obok, answer only the question concisely with no extra phrases
            if 'obok' in bot_label:
                # remove question marks and whitespace
                t_clean = text.strip().replace('?', '').replace('？','').strip()
                # heuristics: if short, answer directly by echoing concise content or doing simple transformations
                # This is placeholder: for many questions we'll echo a concise affirmative or trimmed content
                if len(t_clean) == 0:
                    reply = ''
                elif len(t_clean.split()) <= 6:
                    # reply with concise form (no prefixes)
                    reply = t_clean
                else:
                    # for longer inputs, preserve up to 4000 characters
                    if len(t_clean) > 4000:
                        reply = t_clean[:4000].rstrip()
                    else:
                        reply = t_clean
            else:
                # shin-like rules
                if any(w in lt for w in ['안녕','hi','hello','hey']):
                    reply = '안녕하세요! 무엇을 도와드릴까요?'
                elif any(w in lt for w in ['고마','감사']):
                    reply = '천만에요 — 도움이 되어 기쁩니다.'
                elif any(w in lt for w in ['시간','몇시','언제']):
                    import datetime
                    reply = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                elif any(w in lt for w in ['재설정','초기화','다시 시작']):
                    reply = '요청하신 작업을 진행하려면 자세히 알려주세요. 어떤 걸 다시 시작할까요?'
                else:
                    short = text.strip()
                    # preserve up to 4000 chars for shin replies as well
                    if len(short) > 4000:
                        short = short[:4000].rstrip()
                    # avoid echoing user's text back; if it looks like a question, try a short canned answer
                    qwords = ['시간','몇시','언제','어디','얼마','몇','무엇','왜','어떻게']
                    # if it's a greeting, reply politely even if short
                    greetings = ['안녕','hi','hello','hey','하이']
                    if any(g in lt for g in greetings):
                        reply = '안녕하세요'
                    elif short == text.strip():
                        if any(w in lt for w in qwords):
                            if any(w in lt for w in ['시간','몇시','언제']):
                                import datetime
                                reply = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                            else:
                                # generic short acknowledgement for question-type (no echo)
                                reply = '알겠습니다.'
                        else:
                            # try LLM fallback when available
                            prompt = f"Reply concisely to: {text.strip()}"
                            llm_resp = call_model_with_fallback(prompt)
                            if llm_resp and llm_resp.strip():
                                reply = llm_resp.strip()
                            else:
                                reply = None
                    else:
                        reply = short
            # ensure reply is not empty
            # If reply is empty or would repeat the user's exact text, skip sending anything
            if reply is None or reply == '' or reply.strip() == text.strip():
                last = i+1
                open(processed_marker,'w').write(str(last))
                with open(LOG,'a',encoding='utf-8') as lg:
                    lg.write(f'skipped sending empty/duplicate reply for {key}\n')
                continue
            # send reply
            data = urllib.parse.urlencode({'chat_id':chat_id,'text':reply}).encode()
            try:
                req = urllib.request.urlopen(f'https://api.telegram.org/bot{token}/sendMessage', data=data, timeout=15)
                with open(LOG,'a',encoding='utf-8') as lg:
                    lg.write(f'sent reply to {chat_id} via {bot_label} status {req.getcode()}\n')
            except Exception as e:
                with open(LOG,'a',encoding='utf-8') as lg:
                    lg.write(f'failed send to {chat_id} via {bot_label}: {e}\n')
            last = i+1
            open(processed_marker,'w').write(str(last))
        time.sleep(0.5)
    except Exception as e:
        with open(LOG,'a',encoding='utf-8') as lg:
            lg.write('error loop: '+str(e)+'\n')
        time.sleep(2)
