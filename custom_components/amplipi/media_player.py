"""Support for interfacing with the AmpliPi Multizone home audio controller."""
import logging
from typing import List

from homeassistant.components.cover import SUPPORT_STOP
from homeassistant.components.media_player import MediaPlayerEntity, BrowseMedia, SUPPORT_VOLUME_MUTE, \
    SUPPORT_VOLUME_SET, SUPPORT_SELECT_SOURCE, SUPPORT_PLAY_MEDIA, SUPPORT_PLAY, SUPPORT_BROWSE_MEDIA, \
    MEDIA_CLASS_DIRECTORY
from homeassistant.components.media_player.const import MEDIA_CLASS_MUSIC, SUPPORT_PAUSE, SUPPORT_NEXT_TRACK
from homeassistant.const import CONF_NAME, STATE_OFF, STATE_PLAYING, \
    STATE_PAUSED, STATE_IDLE, STATE_STANDBY, STATE_OK, STATE_UNKNOWN
from homeassistant.helpers.entity import DeviceInfo
from pyamplipi.amplipi import AmpliPi
from pyamplipi.models import ZoneUpdate, Source, SourceUpdate, GroupUpdate, Stream

from .const import (
    DOMAIN, AMPLIPI_OBJECT, CONF_VENDOR, CONF_VERSION,
)

SUPPORT_AMPLIPI_DAC = (
        SUPPORT_SELECT_SOURCE
        | SUPPORT_PLAY_MEDIA
        | SUPPORT_BROWSE_MEDIA
        | SUPPORT_VOLUME_MUTE
        | SUPPORT_VOLUME_SET
        # | SUPPORT_VOLUME_STEP
)

SUPPORT_AMPLIPI_MEDIA = (
        SUPPORT_AMPLIPI_DAC
        | SUPPORT_STOP
        | SUPPORT_PLAY
        | SUPPORT_PAUSE
        | SUPPORT_NEXT_TRACK
)

_LOGGER = logging.getLogger(__name__)

PARALLEL_UPDATES = 1


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the AmpliPi MultiZone Audio Controller"""

    hass_entry = hass.data[DOMAIN][config_entry.entry_id]

    amplipi: AmpliPi = hass_entry[AMPLIPI_OBJECT]
    vendor = hass_entry[CONF_VENDOR]
    name = hass_entry[CONF_NAME]
    version = hass_entry[CONF_VERSION]

    sources = await amplipi.get_sources()

    async_add_entities([
        AmpliPiDac(DOMAIN, f"{name} Input {source.id}", source.id, vendor, version, amplipi)
        for source in sources
    ])


async def async_remove_entry(hass, entry) -> None:
    pass


class AmpliPiDac(MediaPlayerEntity):
    """Representation of an AmpliPi Source Input, of which 4 are supported (Hard Coded)."""

    @property
    def should_poll(self):
        """Polling needed."""
        return True

    # async def async_turn_on(self):
    #     await self._update_zones(
    #         ZoneUpdate(
    #             source_id=self._source.id,
    #             disabled=False,
    #         )
    #     )
    #
    # async def async_turn_off(self):
    #     await self._update_zones(
    #         ZoneUpdate(
    #             source_id=self._source.id,
    #             disabled=True,
    #         )
    #     )

    def __init__(self, namespace: str, name: str, dac_id: int, vendor: str, version: str, client: AmpliPi):
        self._streams = None
        self._source_id = None
        self._name = name
        self._vendor = vendor
        self._version = version
        self._source = None
        self._id = dac_id
        self._client = client
        self._unique_id = f"{namespace}_dac_{dac_id}"
        self._last_update_successful = False

    async def async_mute_volume(self, mute):
        if mute is None:
            return

        if self._source is not None:
            _LOGGER.info(f"setting mute to {mute}")
            await self._update_source(SourceUpdate(
                mute=mute
            ))

    async def async_set_volume_level(self, volume):
        if volume is None:
            return
        assert self._source_id is not None
        _LOGGER.info(f"setting volume to {volume}")
        await self._update_source(SourceUpdate(
            vol_delta=volume
        ))

    async def async_media_play(self):
        assert self._source is not None
        await self._client.play_stream(self._source.id)
        await self.async_update()

    async def async_media_pause(self):
        assert self._source is not None
        await self._client.pause_stream(self._source.id)
        await self.async_update()

    # def media_stop(self):
    #     pass
    #
    # def media_previous_track(self):
    #     pass

    async def async_media_next_track(self):
        assert self._source is not None
        await self._client.next_stream(self._source.id)
        await self.async_update()

    # def media_seek(self, position):
    #     pass

    async def async_play_media(self, media_type, media_id, **kwargs):
        _LOGGER.warning(f'Play Media {media_type} {media_id} {kwargs}')
        pass

    async def async_select_source(self, source):
        _LOGGER.warning(f'Select Source {source}')
        pass

    async def async_select_sound_mode(self, sound_mode):
        _LOGGER.warning(f'Select sound mode {sound_mode}')
        pass

    def clear_playlist(self):
        pass

    def set_shuffle(self, shuffle):
        pass

    def set_repeat(self, repeat):
        pass

    async def async_browse_media(self, media_content_type=None,
                                 media_content_id=None) -> BrowseMedia:

        streams = await self._client.get_streams()

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
                media_content_id=stream.name,
                media_content_type="speaker",
                title=stream.name + " - " + stream.type,
            ) for stream in streams]
        )

    @property
    def supported_features(self):
        """Return flag of media commands that are supported."""
        return SUPPORT_AMPLIPI_DAC

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
            model="AmpliPi Digital Audio Controller",
            name="DAC " + self._source.id,
        )

    # name: str | None
    # connections: set[tuple[str, str]]
    # identifiers: set[tuple[str, str]]
    # manufacturer: str | None
    # model: str | None
    # suggested_area: str | None
    # sw_version: str | None
    # via_device: tuple[str, str]
    # entry_type: str | None
    # default_name: str
    # default_manufacturer: str
    # default_model: str

    @property
    def unique_id(self):
        """Return unique ID for this device."""
        return self._unique_id

    @property
    def name(self):
        """Return the name of the zone."""
        return self._source.name

    async def async_update(self):
        """Retrieve latest state."""
        _LOGGER.info(f'Retrieving state for source {self._source_id}')

        try:
            state = await self._client.get_source(self._source_id)
            streams = await self._client.get_streams()
        except Exception:
            self._last_update_successful = False
            _LOGGER.error(f'Could not update source {self._source_id}')
            return

        if not state:
            self._last_update_successful = False
            return

        self.sync_state(state, streams)

    def sync_state(self, state: Source, streams: List[Stream]):
        self._source = state
        self._streams = streams
        self._last_update_successful = True

    @property
    def state(self):
        """Return the state of the zone."""
        if self._last_update_successful is False:
            return STATE_UNKNOWN
        if self._source is None:
            return STATE_OFF
        if self._source.info is None or self._source.info.state is None:
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
            return STATE_STANDBY

        return STATE_OK

    @property
    def volume_level(self):
        """Volume level of the media player (0..1)."""

        if self._source is None:
            return 0

        return self._source.vol_delta

    @property
    def is_volume_muted(self):
        """Boolean if volume is currently muted."""
        if self._source is None:
            return False

        return self._source.mute

    @property
    def source_list(self):
        """List of available input sources."""
        return [stream.name for stream in self._streams]

    async def _update_source(self, update: SourceUpdate):
        await self._client.set_source(self._source_id, update)

    async def _update_zones(self, update: ZoneUpdate):
        zones = await self._client.get_zones()
        associated_zones = filter(lambda z: z.source_id is self._source.id, zones)
        for zone in associated_zones:
            await self._client.set_zone(zone.id, update)
        await self.async_update()

    async def _update_groups(self, update: GroupUpdate):
        groups = await self._client.get_groups()
        associated_groups = filter(lambda g: g.source_id is self._source.id, groups)
        for group in associated_groups:
            await self._client.set_group(group.id, update)
        await self.async_update()
