#!/usr/bin/env python3
"""
Simple Flask webhook for Dialogflow fulfillment (short Q&A)
- Receives Dialogflow v1/v2 webhook JSON POST with queryText
- Calls local replyer.call_model_with_fallback via HTTP (or uses local python import if colocated)
- Synthesizes response via Google Cloud Text-to-Speech and returns audioContent (base64) in fulfillment

CONFIGURATION:
- Set GOOGLE_APPLICATION_CREDENTIALS to path to service account JSON
- Set REPLYER_LOCAL_URL to http://localhost:5000/llm_call if using a local HTTP adapter for call_model_with_fallback
- Or run webhook in same host and import call_model_with_fallback from replyer module
- Set BEARER_TOKEN to a shared secret for simple auth between Dialogflow and this webhook

Deploy with Cloud Run; see deploy.sh sample.
"""
from flask import Flask, request, jsonify, abort
import os, base64, json

app = Flask(__name__)

BEARER = os.environ.get('WEBHOOK_BEARER_TOKEN','changeme')
REPLYER_LOCAL_URL = os.environ.get('REPLYER_LOCAL_URL')

# Attempt to import call_model_with_fallback if in same workspace
CALL_LOCAL = False
try:
    from replyer import call_model_with_fallback
    CALL_LOCAL = True
except Exception:
    CALL_LOCAL = False

# Google Cloud TTS
try:
    from google.cloud import texttospeech
    GCP_TTS_AVAILABLE = True
except Exception:
    GCP_TTS_AVAILABLE = False


def simple_call_model(prompt):
    # try local import first
    if CALL_LOCAL:
        return call_model_with_fallback(prompt)
    # otherwise, try HTTP adapter
    if REPLYER_LOCAL_URL:
        import requests
        try:
            r = requests.post(REPLYER_LOCAL_URL, json={'prompt':prompt}, timeout=10)
            if r.status_code==200:
                j = r.json()
                return j.get('text') or j.get('result')
        except Exception:
            return None
    return None


def synthesize_text_gcp(text):
    if not GCP_TTS_AVAILABLE:
        return None
    client = texttospeech.TextToSpeechClient()
    synthesis_input = texttospeech.SynthesisInput(text=text)
    voice = texttospeech.VoiceSelectionParams(language_code='en-US', ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL)
    audio_config = texttospeech.AudioConfig(audio_encoding=texttospeech.AudioEncoding.MP3)
    response = client.synthesize_speech(input=synthesis_input, voice=voice, audio_config=audio_config)
    return base64.b64encode(response.audio_content).decode('ascii')


@app.route('/webhook', methods=['POST'])
def webhook():
    # simple bearer check
    auth = request.headers.get('Authorization','')
    if not auth.startswith('Bearer '):
        abort(401)
    token = auth.split(' ',1)[1]
    if token != BEARER:
        abort(403)
    data = request.get_json(silent=True)
    if not data:
        return jsonify({'fulfillmentText':'No data received'}), 400
    # Dialogflow v2: queryResult.queryText
    query = None
    try:
        if 'queryResult' in data:
            query = data['queryResult'].get('queryText') or data['queryResult'].get('text')
        elif 'query' in data:
            query = data['query']
        else:
            # v1 style
            query = data.get('queryText')
    except Exception:
        query = None
    if not query:
        return jsonify({'fulfillmentText':'질문을 이해하지 못했습니다.'}), 200
    # call model
    prompt = f"User asked: {query}"
    resp = simple_call_model(prompt) or '죄송합니다. 지금 응답을 생성할 수 없습니다.'
    # synthesize
    audio_b64 = synthesize_text_gcp(resp) if GCP_TTS_AVAILABLE else None
    # prepare Dialogflow response (prefer audioContent if available)
    if audio_b64:
        out = {
            'fulfillmentMessages': [
                {
                    'platform':'ACTIONS_ON_GOOGLE',
                    'simpleResponses':{
                        'simpleResponses':[{'displayText':resp,'textToSpeech':resp}]
                    }
                },
                {
                    'platform':'ACTIONS_ON_GOOGLE',
                    'mediaContent':[{'mediaType':'AUDIO','mediaObjects':[{'contentUrl':f"data:audio/mp3;base64,{audio_b64}", 'name':'response'}]}]
                }
            ],
            'fulfillmentText': resp
        }
        return jsonify(out)
    else:
        return jsonify({'fulfillmentText':resp})


if __name__=='__main__':
    app.run(host='0.0.0.0',port=int(os.environ.get('PORT',8080)))
