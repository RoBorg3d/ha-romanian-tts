import os
import torch
import torchaudio
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
import uvicorn
import traceback
import struct
import numpy as np
from urllib.parse import parse_qs

from TTS.tts.configs.xtts_config import XttsConfig
from TTS.tts.models.xtts import Xtts
from TTS.tts.layers.xtts.tokenizer import VoiceBpeTokenizer

# =====================================================================
# MONKEY PATCH (Trecem de bariera limbii 'ro')
# =====================================================================
original_preprocess = VoiceBpeTokenizer.preprocess_text

def bypass_preprocess(self, txt, lang):
    if lang == "ro":
        return original_preprocess(self, txt, "it")
    return original_preprocess(self, txt, lang)

VoiceBpeTokenizer.preprocess_text = bypass_preprocess
# =====================================================================

app = FastAPI()

CEDILLA_TO_COMMA = str.maketrans({"ş": "ș", "ţ": "ț", "Ş": "Ș", "Ţ": "Ț"})

MODEL_DIR = "/app/xtts_models/v2.0.2"
SPEAKERS_DIR = "/app/speakers"
OUTPUT_DIR = "/tmp"

# --- MEMORIA SERVERULUI ---
speaker_cache = {}
last_used_voice = "casandra.wav"  

print(f"Incarcam modelul XTTS din {MODEL_DIR}...")
config = XttsConfig()
config.load_json(os.path.join(MODEL_DIR, "config.json"))

if "ro" not in config.languages:
    config.languages.append("ro")

model = Xtts.init_from_config(config)
model.load_checkpoint(config, checkpoint_dir=MODEL_DIR, eval=True)
model.cuda()

print("Modelul a fost incarcat pe GPU! API-ul este gata.")

def get_wav_header(sample_rate=24000, channels=1, bits_per_sample=16):
    header = b'RIFF' + struct.pack('<I', 0xFFFFFFFF) + b'WAVE'
    header += b'fmt ' + struct.pack('<I', 16) + struct.pack('<H', 1) + struct.pack('<H', channels)
    header += struct.pack('<I', sample_rate) + struct.pack('<I', sample_rate * channels * bits_per_sample // 8)
    header += struct.pack('<H', channels * bits_per_sample // 8) + struct.pack('<H', bits_per_sample)
    header += b'data' + struct.pack('<I', 0xFFFFFFFF)
    return header

# --- 0. ENDPOINT: LISTA VOCI (PENTRU HOME ASSISTANT UI) ---
@app.get("/voices/")
async def list_voices():
    try:
        voices = []
        for file in os.listdir(SPEAKERS_DIR):
            if file.endswith(".wav"):
                # Curatam numele: din 'casandra.wav' facem 'Casandra'
                name = file.replace(".wav", "").capitalize()
                voices.append({"voice_id": file, "name": name})
        return voices
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
# --- 1. ENDPOINT: STREAMING BROWSER / HA ---
@app.get("/tts_stream/")
async def tts_stream(text: str, voice: str = None, language: str = "ro"):
    global last_used_voice
    if voice:
        last_used_voice = voice
    else:
        voice = last_used_voice

    try:
        speaker_wav_path = os.path.join(SPEAKERS_DIR, voice)
        if not os.path.exists(speaker_wav_path):
            raise HTTPException(status_code=404, detail=f"Fisier audio lipsa: {voice}")
        clean_text = text.translate(CEDILLA_TO_COMMA)
        
        if voice not in speaker_cache:
            speaker_cache[voice] = model.get_conditioning_latents(audio_path=[speaker_wav_path])
        gpt_cond_latent, speaker_embedding = speaker_cache[voice]
        
        print(f"[STREAMING INCEPUT] Text: {clean_text[:30]}... | Voce: {voice}")

        def audio_generator():
            yield get_wav_header()
            chunks = model.inference_stream(clean_text, language, gpt_cond_latent, speaker_embedding, temperature=0.7)
            for chunk in chunks:
                audio_array = chunk.cpu().numpy()
                audio_array = (audio_array * 32767.0).astype(np.int16)
                yield audio_array.tobytes()
            print("[STREAMING FINALIZAT]")

        return StreamingResponse(audio_generator(), media_type="audio/wav")
    except Exception as e:
        print("EROARE STREAMING:", str(e))
        raise HTTPException(status_code=500, detail=str(e))

# --- 2. ENDPOINT: POWERSHELL / FISIER WAV CLASIC ---
@app.post("/tts_to_audio/")
async def generate_audio(request: Request):
    global last_used_voice
    try:
        data = await request.json()
        raw_text = data.get("text")
        language = data.get("language", "ro")
        
        req_voice = data.get("speaker_wav")
        if req_voice:
            last_used_voice = req_voice
        voice = last_used_voice

        if not raw_text:
            raise HTTPException(status_code=400, detail="Lipseste textul")

        speaker_wav_path = os.path.join(SPEAKERS_DIR, voice)
        if not os.path.exists(speaker_wav_path):
            raise HTTPException(status_code=404, detail=f"Nu gasesc fisierul audio: {voice}")

        text = raw_text.translate(CEDILLA_TO_COMMA)
        
        if voice not in speaker_cache:
            speaker_cache[voice] = model.get_conditioning_latents(audio_path=[speaker_wav_path])
            
        gpt_cond_latent, speaker_embedding = speaker_cache[voice]
        print(f"Generez audio pentru: {text} | Limba: {language} | Voce: {voice}")
        
        out = model.inference(text, language, gpt_cond_latent, speaker_embedding, temperature=0.7)
        
        output_path = os.path.join(OUTPUT_DIR, "generated.wav")
        wav_tensor = torch.tensor(out["wav"]).unsqueeze(0)
        torchaudio.save(output_path, wav_tensor, 24000)
        
        return FileResponse(output_path, media_type="audio/wav")
    except Exception as e:
        print("=== EROARE FATALA DETALIATA ===")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

# --- 3. ENDPOINT: MARYTTS (NATIV HOME ASSISTANT) ---
# Home Assistant trimite cererile prin metoda POST, așa că am deblocat ușa:
@app.post("/process")
async def ha_native_tts_post(request: Request):
    global last_used_voice
    
    try:
        # Home Assistant trimite datele ascunse, asa ca le despachetam:
        body = await request.body()
        parsed = parse_qs(body.decode('utf-8'))
        
        INPUT_TEXT = parsed.get("INPUT_TEXT", [""])[0]
        VOICE = parsed.get("VOICE", [None])[0]
        
        if not INPUT_TEXT:
            raise HTTPException(status_code=400, detail="Text lipsa")

        if VOICE:
            last_used_voice = VOICE
        else:
            VOICE = last_used_voice

        clean_text = INPUT_TEXT.translate(CEDILLA_TO_COMMA)
        
        speaker_wav_path = os.path.join(SPEAKERS_DIR, VOICE)
        if not os.path.exists(speaker_wav_path):
            raise HTTPException(status_code=404, detail=f"Fisier audio lipsa: {VOICE}")
            
        if VOICE not in speaker_cache:
            speaker_cache[VOICE] = model.get_conditioning_latents(audio_path=[speaker_wav_path])
            
        gpt_cond, speaker_emb = speaker_cache[VOICE]
        
        print(f"[MARYTTS POST] Text: {clean_text[:30]}... | Voce: {VOICE}")
        
        # Ignoram italiana ceruta de HA si fortam generarea in Romana!
        out = model.inference(clean_text, "ro", gpt_cond, speaker_emb, temperature=0.7)
        output_path = os.path.join(OUTPUT_DIR, "generated.wav")
        torchaudio.save(output_path, torch.tensor(out["wav"]).unsqueeze(0), 24000)
        
        return FileResponse(output_path, media_type="audio/wav")
    except Exception as e:
        print("EROARE HA POST:", str(e))
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8020)
