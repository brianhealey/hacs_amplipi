"""Support for interfacing with the AmpliPi Multizone home audio controller."""
import logging
from typing import List

from homeassistant.components.cover import SUPPORT_STOP
from homeassistant.components.media_player import MediaPlayerEntity, BrowseMedia, SUPPORT_VOLUME_MUTE, \
    SUPPORT_VOLUME_SET, SUPPORT_VOLUME_STEP, SUPPORT_SELECT_SOURCE, SUPPORT_TURN_OFF, SUPPORT_TURN_ON, \
    SUPPORT_PLAY_MEDIA, SUPPORT_CLEAR_PLAYLIST, SUPPORT_PLAY, SUPPORT_SHUFFLE_SET, SUPPORT_SELECT_SOUND_MODE, \
    SUPPORT_BROWSE_MEDIA, SUPPORT_REPEAT_SET, SUPPORT_GROUPING, MEDIA_CLASS_DIRECTORY
from homeassistant.components.media_player.const import MEDIA_CLASS_MUSIC
from homeassistant.const import CONF_NAME, STATE_OFF, STATE_ON, STATE_PLAYING, \
    STATE_PAUSED, STATE_IDLE, STATE_STANDBY
from homeassistant.helpers.entity import DeviceInfo
from pyamplipi.amplipi import AmpliPi
from pyamplipi.models import Zone, ZoneUpdate, Source

from .const import (
    DOMAIN, AMPLIPI_OBJECT, CONF_VENDOR, CONF_VERSION,
)

SUPPORT_AMPLIPI = (
        SUPPORT_TURN_ON
        | SUPPORT_PLAY_MEDIA
        | SUPPORT_VOLUME_STEP
        | SUPPORT_SELECT_SOURCE
        #        | SUPPORT_STOP
        #        | SUPPORT_CLEAR_PLAYLIST
        | SUPPORT_PLAY
        #        | SUPPORT_SHUFFLE_SET
        | SUPPORT_SELECT_SOUND_MODE
        #        | SUPPORT_BROWSE_MEDIA
        #        | SUPPORT_REPEAT_SET
        | SUPPORT_TURN_OFF
        | SUPPORT_VOLUME_MUTE
        | SUPPORT_VOLUME_SET
        | SUPPORT_GROUPING
)

_LOGGER = logging.getLogger(__name__)

PARALLEL_UPDATES = 1

async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the AmpliPi MultiZone Audio Controller"""

    global ZONES
    hass_entry = hass.data[DOMAIN][config_entry.entry_id]

    amplipi: AmpliPi = hass_entry[AMPLIPI_OBJECT]
    vendor = hass_entry[CONF_VENDOR]
    name = hass_entry[CONF_NAME]
    version = hass_entry[CONF_VERSION]

    zones = await amplipi.get_zones()
    groups = await amplipi.get_groups()

    ZONES = [AmpliPiZone(zone, name, vendor, version, amplipi) for zone in zones]

    async_add_entities(ZONES, False)


async def async_remove_entry(hass, entry) -> None:
    pass


class AmpliPiZone(MediaPlayerEntity):
    """Representation of an AmpliPi zone."""

    @property
    def should_poll(self):
        """Polling needed."""
        return True

    def join_players(self, group_members):
        pass

    def unjoin_player(self):
        pass

    async def async_turn_on(self):
        await self._update_zone(
            ZoneUpdate(
                disabled=False,
            )
        )

    async def async_turn_off(self):
        await self._update_zone(
            ZoneUpdate(
                disabled=True,
            )
        )

    def __init__(self, zone: Zone, namespace: str, vendor: str, version: str, amplipi: AmpliPi):
        # self._sources = []
        self._source = None
        self._zone = zone
        self._amplipi = amplipi
        self._unique_id = f"{namespace}_{self._zone.id + 1}"
        self._vendor = vendor
        self._version = version
        self._last_update_successful = False

    async def async_mute_volume(self, mute):
        if mute is None:
            return

        await self._update_zone(
            ZoneUpdate(
                mute=mute,
            )
        )

    async def async_set_volume_level(self, volume):
        if volume is None:
            return

        _LOGGER.warning('setting zone volume from {} to {}', self._zone.vol, volume)
        await self._update_zone(
            ZoneUpdate(
                vol=(volume * 1.2345) - 79,
            )
        )

    async def async_media_play(self):
        assert self._zone is not None
        assert self._source is not None
        await self._amplipi.play_stream(self._source.id)
        await self.async_update()

    async def async_media_pause(self):
        assert self._zone is not None
        assert self._source is not None
        await self._amplipi.pause_stream(self._source.id)
        await self.async_update()

    # def media_stop(self):
    #     pass
    #
    # def media_previous_track(self):
    #     pass

    async def async_media_next_track(self):
        assert self._zone is not None
        assert self._source is not None
        await self._amplipi.next_stream(self._source.id)
        await self.async_update()

    # def media_seek(self, position):
    #     pass

    def play_media(self, media_type, media_id, **kwargs):
        pass

    async def async_select_source(self, source):

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

        sources = await self._amplipi.get_sources()

        return BrowseMedia(
            can_expand=True,
            can_play=False,
            media_class=MEDIA_CLASS_DIRECTORY,
            media_content_id="",
            media_content_type="",
            title="AmpliPi",
            children=[BrowseMedia(
                can_play=True,
                can_expand=False,
                media_class=MEDIA_CLASS_MUSIC,
                media_content_id=source.input,
                media_content_type="speaker",
                title=source.name

            ) for source in sources]
        )

    @property
    def supported_features(self):
        """Return flag of media commands that are supported."""
        return SUPPORT_AMPLIPI

    @property
    def media_content_type(self):
        """Content type of current playing media."""
        return "speaker"

    @property
    def entity_registry_enabled_default(self):
        """Return if the entity should be enabled when first added to the entity registry."""
        return True

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

    async def async_update(self):
        """Retrieve latest state."""
        _LOGGER.warning("Retrieving state for zone %d", self._zone.id + 1)

        try:
            state = await self._amplipi.get_zone(self._zone.id)
            sources = await self._amplipi.get_sources()
        except Exception:
            self._last_update_successful = False
            _LOGGER.error("Could not update zone %d", self._zone.id + 1)
            return

        if not state:
            self._last_update_successful = False
            return

        self.sync_state(state, sources)

    def sync_state(self, state: Zone, sources: List[Source]):
        self._zone = state
        self._source = next((source for source in sources if source.id == state.source_id), [None])
        self._last_update_successful = True

    @property
    def state(self):
        """Return the state of the zone."""
        if not self._zone or self._zone.disabled:
            return STATE_OFF
        if not self._source:
            return STATE_ON
        if not self._source.info or not self._source.info.state:
            return STATE_IDLE
        if self._source.info.state in (
                'paused'
        ):
            return STATE_PAUSED
        if self._source.info.state in (
                'playing'
        ):
            return STATE_PLAYING
        if self._source.info.state in (
                'stopped'
        ):
            return STATE_IDLE

        return STATE_STANDBY

    @property
    def volume_level(self):
        """Volume level of the media player (0..1)."""

        # amplipi stores this as a number between -79 and 0
        #
        # -99 = 0
        # 0 = 1
        #

        return (self._zone.vol + 79) * .0123456

    @property
    def is_volume_muted(self):
        """Boolean if volume is currently muted."""
        return self._zone.mute

    # @property
    # def source_list(self):
    #     """List of available input sources."""
    #     return self._sources

    async def _update_zone(self, update: ZoneUpdate):
        await self._amplipi.set_zone(self._zone.id, update)
        await self.async_update()
