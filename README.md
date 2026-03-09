Documentație: Integrare Romanian TTS (Local Voice Cloning) pentru Home Assistant
Această integrare modernă (Generația 2 / Config Flow) conectează Home Assistant la un server local Docker care rulează modelul AI eduardem/xtts-v2-romanian. Permite clonarea vocală pe baza unui fisier wav exemplu cu vocea model și funcționează 100% offline, oferind control prin interfața vizuală nativă.

1. Arhitectura Sistemului
Backend (Docker): Un server Python/FastAPI care ține modelul XTTSv2 în memorie VRAM (accelerare GPU) pentru latență minimă.

Frontend (Home Assistant): O integrare custom cu instalare din interfața vizuală (UI), care interoghează serverul pentru lista de voci disponibile și creează o entitate TextToSpeechEntity dedicată pentru fiecare voce configurată.

2. Structura Fișierelor (custom_components/ro_tts/)
Plaintext
ro_tts/
 ├── translations/
 │    └── en.json        
 ├── __init__.py         
 ├── config_flow.py      
 ├── const.py            
 ├── manifest.json       
 └── tts.py              

3. Instalare și Utilizare
Copiați structura de mai sus în folderul custom_components/ro_tts al instanței Home Assistant.

Restartați Home Assistant.

Ștergeți memoria cache a browserului (Ctrl+F5).

Navigați la Settings -> Devices & Services -> Add Integration.

Căutați Romanian TTS și urmați pașii din interfața vizuală pentru a vă conecta la Docker și a alege vocea.

Pentru voci multiple, repetați procesul de instalare. Fiecare voce va apărea distinct în meniul Voice Assistants.

4. Limitări Cunoscute
Viteza și Latența: Spre deosebire de serviciile cloud comerciale care generează răspunsuri instantanee, motorul XTTS rulează local. Latența depinde direct de puterea GPU-ului alocat containerului Docker.

Halucinații AI: Modelele autoregresive locale pot genera ocazional defecte audio (repetiții, sunete de fundal, schimbări de intonație). Calitatea generării este strict dependentă de calitatea fișierului de referință .wav (necesită zgomot de fundal zero și o claritate vocală perfectă).
