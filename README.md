Documentație: Integrare Romanian TTS (Local Voice Cloning) pentru Home Assistant
Această integrare modernă (Generația 2 / Config Flow) conectează Home Assistant la un server local Docker care rulează modelul AI eduardem/xtts-v2-romanian. Permite clonarea vocală (Inna, Casandra etc.) și funcționează 100% offline, oferind control prin interfața vizuală nativă.

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
3. Codul Sursă (Fișierele Integrării)
manifest.json

JSON
{
  "domain": "ro_tts",
  "name": "Romanian TTS",
  "version": "2.0.0",
  "documentation": "https://github.com/...",
  "dependencies": [],
  "codeowners": [],
  "config_flow": true,
  "iot_class": "local_push"
}
const.py

Python
DOMAIN = "ro_tts"
CONF_URL = "url"
CONF_VOICE = "voice"
translations/en.json

JSON
{
  "config": {
    "step": {
      "user": {
        "title": "Conectare Server TTS Local",
        "description": "Introdu URL-ul de bază al serverului Docker (ex: http://192.168.1.X:8020)",
        "data": {
          "url": "Adresa Serverului (URL)"
        }
      },
      "select_voice": {
        "title": "Alege Vocea Implicită",
        "description": "Succes! Am găsit vocile pe server. Selectează vocea principală din meniu.",
        "data": {
          "voice": "Vocea Asistentului"
        }
      }
    },
    "error": {
      "cannot_connect": "Nu m-am putut conecta la server. Verifică IP-ul și portul."
    }
  }
}
__init__.py

Python
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from .const import DOMAIN

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hass.data.setdefault(DOMAIN, {})
    await hass.config_entries.async_forward_entry_setups(entry, ["tts"])
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, ["tts"])
config_flow.py

Python
import voluptuous as vol
import urllib.parse
from homeassistant import config_entries
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import logging

from .const import DOMAIN, CONF_URL, CONF_VOICE

_LOGGER = logging.getLogger(__name__)

class RoTTSConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self):
        self.url = None
        self.voices_dict = {}

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            self.url = user_input[CONF_URL]
            session = async_get_clientsession(self.hass)
            try:
                parsed_url = urllib.parse.urlparse(self.url)
                base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
                
                async with session.get(f"{base_url}/voices/", timeout=5) as response:
                    if response.status == 200:
                        data = await response.json()
                        self.voices_dict = {v["voice_id"]: v["name"] for v in data}
                        return await self.async_step_select_voice()
                    else:
                        errors["base"] = "cannot_connect"
            except Exception as e:
                _LOGGER.error("Eroare Config Flow conexiune: %s", str(e))
                errors["base"] = "cannot_connect"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_URL, default="http://192.168."): str
            }),
            errors=errors,
        )

    async def async_step_select_voice(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(
                title="Romanian TTS",
                data={
                    CONF_URL: self.url,
                    CONF_VOICE: user_input[CONF_VOICE]
                }
            )

        return self.async_show_form(
            step_id="select_voice",
            data_schema=vol.Schema({
                vol.Required(CONF_VOICE): vol.In(self.voices_dict)
            })
        )
tts.py

Python
import logging
import urllib.parse
from homeassistant.components.tts import TextToSpeechEntity, Voice
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN, CONF_URL, CONF_VOICE

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities):
    session = async_get_clientsession(hass)
    url = config_entry.data[CONF_URL]
    default_voice = config_entry.data[CONF_VOICE]
    voices_list = []

    try:
        parsed_url = urllib.parse.urlparse(url)
        base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
        
        async with session.get(f"{base_url}/voices/", timeout=5) as response:
            if response.status == 200:
                data = await response.json()
                voices_list = [Voice(v["voice_id"], v["name"]) for v in data]
    except Exception as e:
        _LOGGER.error(">>> [RO_TTS] Eroare citire voci la setup: %s", str(e))

    if not voices_list:
        voices_list = [Voice(default_voice, default_voice.replace(".wav", "").capitalize())]

    async_add_entities([RoTTSEntity(hass, config_entry, url, default_voice, voices_list)])


class RoTTSEntity(TextToSpeechEntity):
    def __init__(self, hass, config_entry, url, default_voice, voices):
        self.hass = hass
        self._url = url
        self._default_voice = default_voice
        self._voices = voices
        
        # Auto-denumire inteligenta a entitatii pe baza vocii selectate
        voice_clean_name = default_voice.replace(".wav", "").capitalize()
        self._attr_name = f"Romanian TTS ({voice_clean_name})"
        self._attr_unique_id = f"ro_tts_{config_entry.entry_id}" 

    @property
    def default_language(self):
        return "ro"

    @property
    def supported_languages(self):
        return ["ro"]

    @property
    def supported_options(self):
        return ["voice"]

    @property
    def default_options(self):
        return {"voice": self._default_voice}

    def get_supported_voices(self, language: str):
        return self._voices

    async def async_get_tts_audio(self, message, language, options):
        session = async_get_clientsession(self.hass)
        selected_voice = options.get("voice", self._default_voice) if options else self._default_voice
        
        parsed_url = urllib.parse.urlparse(self._url)
        base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
        endpoint_url = f"{base_url}/tts_to_audio/"
        
        try:
            payload = {
                "text": message,
                "language": "ro",
                "speaker_wav": selected_voice
            }
            async with session.post(endpoint_url, json=payload) as response:
                if response.status == 200:
                    data = await response.read()
                    return ("wav", data)
                else:
                    _LOGGER.error("Eroare server Ro TTS: %s", response.status)
        except Exception as e:
            _LOGGER.error("Eroare conexiune Ro TTS: %s", str(e))
            
        return (None, None)
4. Instalare și Utilizare
Copiați structura de mai sus în folderul custom_components/ro_tts al instanței Home Assistant.

Restartați Home Assistant.

Ștergeți memoria cache a browserului (Ctrl+F5).

Navigați la Settings -> Devices & Services -> Add Integration.

Căutați Romanian TTS și urmați pașii din interfața vizuală pentru a vă conecta la Docker și a alege vocea.

Pentru voci multiple, repetați procesul de instalare. Fiecare voce va apărea distinct în meniul Voice Assistants.

5. Limitări Cunoscute
Viteza și Latența: Spre deosebire de serviciile cloud comerciale care generează răspunsuri instantanee, motorul XTTS rulează local. Latența depinde direct de puterea GPU-ului alocat containerului Docker.

Halucinații AI: Modelele autoregresive locale pot genera ocazional defecte audio (repetiții, sunete de fundal, schimbări de intonație). Calitatea generării este strict dependentă de calitatea fișierului de referință .wav (necesită zgomot de fundal zero și o claritate vocală perfectă).
