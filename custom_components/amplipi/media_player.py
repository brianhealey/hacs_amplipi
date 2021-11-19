"""Support for interfacing with the AmpliPi Multizone home audio controller."""
import logging
from typing import List

from homeassistant.components.media_player import MediaPlayerEntity, BrowseMedia, SUPPORT_VOLUME_MUTE, \
    SUPPORT_VOLUME_SET, SUPPORT_VOLUME_STEP, SUPPORT_SELECT_SOURCE, SUPPORT_TURN_OFF, SUPPORT_TURN_ON
from homeassistant.const import CONF_NAME, CONF_HOST, CONF_PORT, CONF_ID, STATE_OFF, STATE_ON
from homeassistant.helpers.entity import DeviceInfo
from pyamplipi.amplipi import AmpliPi
from pyamplipi.models import Zone, ZoneUpdate, Source

from .const import (
    DOMAIN, AMPLIPI_OBJECT, CONF_VENDOR, CONF_VERSION,
)

SUPPORT_AMPLIPI = (
        SUPPORT_TURN_ON
        | SUPPORT_TURN_OFF
        | SUPPORT_VOLUME_MUTE
        | SUPPORT_VOLUME_SET
        | SUPPORT_VOLUME_STEP
        | SUPPORT_SELECT_SOURCE
)

_LOGGER = logging.getLogger(__name__)

PARALLEL_UPDATES = 1


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the AmpliPi MultiZone Audio Controller"""
    hass_entry = hass.data[DOMAIN][config_entry.entry_id]

    amplipi: AmpliPi = hass_entry[AMPLIPI_OBJECT]
    vendor = hass_entry[CONF_VENDOR]
    name = hass_entry[CONF_NAME]
    host = hass_entry[CONF_HOST]
    port = hass_entry[CONF_PORT]
    config_id = hass_entry[CONF_ID]
    version = hass_entry[CONF_VERSION]

    zones = await amplipi.get_zones()

    async_add_entities([AmpliPiZone(zone, name, vendor, version, amplipi) for zone in zones], False)


class AmpliPiZone(MediaPlayerEntity):
    """Representation of an AmpliPi zone."""

    def turn_on(self):
        self._zone.disabled = True
        self.update_zone()

    def turn_off(self):
        self._zone.disabled = False
        self.update_zone()

    def __init__(self, zone: Zone, namespace: str, vendor: str, version: str, amplipi: AmpliPi):
        self._sources = []
        self._source = None
        self._zone = zone
        self._amplipi = amplipi
        self._unique_id = f"{namespace}_{self._zone.id + 1}"
        self._vendor = vendor
        self._version = version
        self._last_update_successful = False

    def mute_volume(self, mute):
        if mute is None:
            return
        self._zone.mute = mute
        self.update_zone()

    def set_volume_level(self, volume):
        if volume is None:
            return
        self._zone.vol = volume
        self.update_zone()

    def media_play(self):
        pass

    def media_pause(self):
        pass

    def media_stop(self):
        pass

    def media_previous_track(self):
        pass

    def media_next_track(self):
        pass

    def media_seek(self, position):
        pass

    def play_media(self, media_type, media_id, **kwargs):
        pass

    def select_source(self, source):
        pass

    def select_sound_mode(self, sound_mode):
        pass

    def clear_playlist(self):
        pass

    def set_shuffle(self, shuffle):
        pass

    def set_repeat(self, repeat):
        pass

    async def async_browse_media(self, media_content_type=None,
                                 media_content_id=None) -> BrowseMedia:
        pass

    @property
    def supported_features(self):
        """Return flag of media commands that are supported."""
        return SUPPORT_AMPLIPI

    @property
    def entity_registry_enabled_default(self):
        """Return if the entity should be enabled when first added to the entity registry."""
        return self._last_update_successful

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info for this device."""
        return DeviceInfo(
            identifiers={(DOMAIN, self.unique_id)},
            manufacturer=self._vendor,
            model="AmpliPi",
            name=self.name,
            sw_version=self._version,
        )

    @property
    def unique_id(self):
        """Return unique ID for this device."""
        return self._unique_id

    @property
    def name(self):
        """Return the name of the zone."""
        return self._zone.name

    async def update(self):
        """Retrieve latest state."""
        try:
            state = await self._amplipi.get_zone(self._zone.id)
            sources = await self._amplipi.get_sources()
        except Exception:
            self._last_update_successful = False
            _LOGGER.warning("Could not update zone %d", self._zone.id + 1)
            return

        if not state:
            self._last_update_successful = False
            return

        self.sync_state(state, sources)

    def sync_state(self, state: Zone, sources: List[Source]):
        self._zone = state
        self._sources = sources
        self._source = next((source for source in sources if source.id == state.source_id), [None])
        self._last_update_successful = True

    #
    # @property
    # def entity_registry_enabled_default(self):
    #     """Return if the entity should be enabled when first added to the entity registry."""
    #     return self._zone_id < 20 or self._update_success
    #
    # @property
    # def device_info(self) -> DeviceInfo:
    #     """Return device info for this device."""
    #     return DeviceInfo(
    #         identifiers={(DOMAIN, self.unique_id)},
    #         manufacturer="Monoprice",
    #         model="6-Zone Amplifier",
    #         name=self.name,
    #     )
    #
    # @property
    # def unique_id(self):
    #     """Return unique ID for this device."""
    #     return self._unique_id
    #
    # @property
    # def name(self):
    #     """Return the name of the zone."""
    #     return self._name
    #

    @property
    def state(self):
        """Return the state of the zone."""
        return STATE_OFF if self._zone.disabled else STATE_ON

    @property
    def volume_level(self):
        """Volume level of the media player (0..1)."""
        return self._zone.vol

    @property
    def is_volume_muted(self):
        """Boolean if volume is currently muted."""
        return self._zone.mute

    #
    # @property
    # def supported_features(self):
    #     """Return flag of media commands that are supported."""
    #     return SUPPORT_MONOPRICE
    #
    # @property
    # def media_title(self):
    #     """Return the current source as medial title."""
    #     return self._source
    #
    # @property
    # def source(self):
    #     """Return the current input source of the device."""
    #     return self._source
    #

    @property
    def source_list(self):
        """List of available input sources."""
        return self._source_names

    #
    # def snapshot(self):
    #     """Save zone's current state."""
    #     self._snapshot = self._monoprice.zone_status(self._zone_id)
    #
    # def restore(self):
    #     """Restore saved state."""
    #     if self._snapshot:
    #         self._monoprice.restore_zone(self._snapshot)
    #         self.schedule_update_ha_state(True)
    #
    # def select_source(self, source):
    #     """Set input source."""
    #     if source not in self._source_name_id:
    #         return
    #     idx = self._source_name_id[source]
    #     self._monoprice.set_source(self._zone_id, idx)
    #
    # def turn_on(self):
    #     """Turn the media player on."""
    #     self._monoprice.set_power(self._zone_id, True)
    #
    # def turn_off(self):
    #     """Turn the media player off."""
    #     self._monoprice.set_power(self._zone_id, False)
    #
    # def mute_volume(self, mute):
    #     """Mute (true) or unmute (false) media player."""
    #     self._monoprice.set_mute(self._zone_id, mute)
    #
    # def set_volume_level(self, volume):
    #     """Set volume level, range 0..1."""
    #     self._monoprice.set_volume(self._zone_id, int(volume * 38))
    #
    # def volume_up(self):
    #     """Volume up the media player."""
    #     if self._volume is None:
    #         return
    #     self._monoprice.set_volume(self._zone_id, min(self._volume + 1, 38))
    #
    # def volume_down(self):
    #     """Volume down media player."""
    #     if self._volume is None:
    #         return
    #     self._monoprice.set_volume(self._zone_id, max(self._volume - 1, 0))

    async def update_zone(self):
        zone = await self._amplipi.set_zone(self._zone.id, ZoneUpdate(
            name=self._zone.name,
            source_id=None,
            mute=self._zone.mute,
            vol=self._zone.vol,
            disabled=self._zone.disabled
        ))
        sources = await self._amplipi.get_sources()
        self.sync_state(zone, sources)
