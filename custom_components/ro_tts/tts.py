import logging
import urllib.parse
from homeassistant.components.tts import TextToSpeechEntity, Voice
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN, CONF_URL, CONF_VOICE

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities):
    """Seteaza entitatea TTS folosind datele din Config Flow."""
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
    """Reprezentarea moderna a motorului TTS."""

    def __init__(self, hass, config_entry, url, default_voice, voices):
        self.hass = hass
        self._url = url
        self._default_voice = default_voice
        self._voices = voices
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
        
        # CORECtIA AICI: Ne asiguram ca indiferent ce ai introdus in UI, 
        # textul este trimis exact catre endpoint-ul de generare audio.
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
