import voluptuous as vol
import urllib.parse
from homeassistant import config_entries
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import logging

from .const import DOMAIN, CONF_URL, CONF_VOICE

_LOGGER = logging.getLogger(__name__)

class RoTTSConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Regizorul ferestrelor de instalare UI."""
    VERSION = 1

    def __init__(self):
        self.url = None
        self.voices_dict = {}

    async def async_step_user(self, user_input=None):
        """Pasul 1: Cerem URL-ul serverului."""
        errors = {}

        if user_input is not None:
            self.url = user_input[CONF_URL]
            # Incercam sa ne conectam si sa luam vocile
            session = async_get_clientsession(self.hass)
            try:
                parsed_url = urllib.parse.urlparse(self.url)
                base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
                
                async with session.get(f"{base_url}/voices/", timeout=5) as response:
                    if response.status == 200:
                        data = await response.json()
                        # Construim dictionarul pentru Dropdown (ID: Nume)
                        self.voices_dict = {v["voice_id"]: v["name"] for v in data}
                        
                        # Daca a mers, trecem automat la ecranul 2!
                        return await self.async_step_select_voice()
                    else:
                        errors["base"] = "cannot_connect"
            except Exception as e:
                _LOGGER.error("Eroare Config Flow conexiune: %s", str(e))
                errors["base"] = "cannot_connect"

        # Afisam fereastra 1 (cerem URL-ul)
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_URL, default="http://192.168."): str
            }),
            errors=errors,
        )

    async def async_step_select_voice(self, user_input=None):
        """Pasul 2: Selectam vocea din Dropdown-ul generat dinamic."""
        if user_input is not None:
            # Salvam configuratia definitiv!
            return self.async_create_entry(
                title="Romanian TTS",
                data={
                    CONF_URL: self.url,
                    CONF_VOICE: user_input[CONF_VOICE]
                }
            )

        # Afisam fereastra 2 cu Dropdown-ul (vol.In creaza Dropdown-ul nativ)
        return self.async_show_form(
            step_id="select_voice",
            data_schema=vol.Schema({
                vol.Required(CONF_VOICE): vol.In(self.voices_dict)
            })
        )
