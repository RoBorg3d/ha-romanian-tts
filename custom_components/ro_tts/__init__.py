from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from .const import DOMAIN

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Seteaza integrarea pe baza datelor din UI."""
    hass.data.setdefault(DOMAIN, {})
    
    # Trimitem comanda sa porneasca platforma de TTS cu datele salvate
    await hass.config_entries.async_forward_entry_setups(entry, ["tts"])
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Opreste integrarea cand e stearsa din UI."""
    return await hass.config_entries.async_unload_platforms(entry, ["tts"])
