"""Support for interfacing with the AmpliPi Multizone home audio controller."""
import logging
from typing import List

import validators
from homeassistant.components.cover import SUPPORT_STOP
from homeassistant.components.media_player import MediaPlayerEntity, BrowseMedia, SUPPORT_VOLUME_MUTE, \
    SUPPORT_VOLUME_SET, SUPPORT_SELECT_SOURCE, SUPPORT_PLAY_MEDIA, SUPPORT_PLAY, SUPPORT_BROWSE_MEDIA, \
    MEDIA_CLASS_DIRECTORY
from homeassistant.components.media_player.const import MEDIA_CLASS_MUSIC, SUPPORT_PAUSE, SUPPORT_NEXT_TRACK, \
    MEDIA_TYPE_MUSIC
from homeassistant.const import CONF_NAME, STATE_OFF, STATE_PLAYING, \
    STATE_PAUSED, STATE_IDLE, STATE_UNKNOWN
from homeassistant.helpers.entity import DeviceInfo
from pyamplipi.amplipi import AmpliPi
from pyamplipi.models import ZoneUpdate, Source, SourceUpdate, GroupUpdate, Stream, Group, Zone, Announcement

from .const import (
    DOMAIN, AMPLIPI_OBJECT, CONF_VENDOR, CONF_VERSION, CONF_WEBAPP, CONF_API_PATH,
)

RCA_INPUTS = [
    BrowseMedia(
        can_play=True,
        can_expand=False,
        media_class=MEDIA_CLASS_MUSIC,
        media_content_id="rca1",
        media_content_type="input",
        title="RCA Input 1",
    ),
    BrowseMedia(
        can_play=True,
        can_expand=False,
        media_class=MEDIA_CLASS_MUSIC,
        media_content_id="rca2",
        media_content_type="input",
        title="RCA Input 2",
    ),
    BrowseMedia(
        can_play=True,
        can_expand=False,
        media_class=MEDIA_CLASS_MUSIC,
        media_content_id="rca3",
        media_content_type="input",
        title="RCA Input 3",
    ),
    BrowseMedia(
        can_play=True,
        can_expand=False,
        media_class=MEDIA_CLASS_MUSIC,
        media_content_id="rca4",
        media_content_type="input",
        title="RCA Input 4",
    ),
]

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

DB_MAX = -80
DB_MIN = 0


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the AmpliPi MultiZone Audio Controller"""

    hass_entry = hass.data[DOMAIN][config_entry.entry_id]

    amplipi: AmpliPi = hass_entry[AMPLIPI_OBJECT]
    vendor = hass_entry[CONF_VENDOR]
    name = hass_entry[CONF_NAME]
    version = hass_entry[CONF_VERSION]
    image_base_path = f'{hass_entry[CONF_WEBAPP]}{hass_entry[CONF_API_PATH]}'

    status = await amplipi.get_status()

    async_add_entities([
        AmpliPiDac(DOMAIN, source, status.streams, vendor, version, image_base_path, amplipi)
        for source in status.sources
    ])


async def async_remove_entry(hass, entry) -> None:
    pass


def db_to_pct(decibels: float) -> float:
    return 1 - (decibels - DB_MIN) / (DB_MAX - DB_MIN)


def pct_to_db(percentage: float) -> float:
    print(f'using percentage {percentage}')
    return DB_MAX - ((DB_MAX - DB_MIN) * percentage)





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

    def __init__(self, namespace: str, source: Source, streams: List[Stream], vendor: str, version: str,
                 image_base_path: str, client: AmpliPi):
        self._streams = streams
        self._image_base_path = image_base_path
        self._zones = []
        self._groups = []
        self._name = source.name
        self._vendor = vendor
        self._version = version
        self._source = source
        self._id = source.id
        self._client = client
        self._unique_id = f"{namespace}_input_{source.id}"
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
        _LOGGER.info(f"setting volume to {volume}")
        await self._update_source(SourceUpdate(
            vol_delta=pct_to_db(volume)
        ))

    async def async_media_play(self):
        await self._client.play_stream(self._source.id)
        await self.async_update()

    async def async_media_pause(self):
        await self._client.pause_stream(self._source.id)
        await self.async_update()

    # def media_stop(self):
    #     pass
    #
    # def media_previous_track(self):
    #     pass

    async def async_media_next_track(self):
        await self._client.next_stream(self._source.id)
        await self.async_update()

    # def media_seek(self, position):
    #     pass

    async def async_play_media(self, media_type, media_id, **kwargs):
        _LOGGER.warning(f'Play Media {media_type} {media_id} {kwargs}')

        if media_type is MEDIA_TYPE_MUSIC:
            _LOGGER.warning(f'This might be a TTS announcement..')
            await self._client.announce(
                Announcement(
                    source_id=self._source.id,
                    media=media_id,
                    vol=pct_to_db(.5),
                )
            )

        pass

    async def async_select_source(self, source):
        stream = next(filter(lambda z: z.name == source, self._streams), None)
        if stream is None:
            _LOGGER.warning(f'Select Source {source} called but a match could not be found in the stream cache, '
                            f'{self._streams}')
            pass
        else:
            await self._update_source(SourceUpdate(
                input=f'stream={stream.id}'
            ))

    async def async_select_sound_mode(self, sound_mode):
        _LOGGER.warning(f'Select sound mode {sound_mode}')
        pass

    def clear_playlist(self):
        pass

    def set_shuffle(self, shuffle):
        pass

    def set_repeat(self, repeat):
        pass

    def build_url(self, img_url):
        if img_url is None:
            return None

        # if we have a full url, go ahead and return it
        if validators.url(img_url):
            return img_url

        # otherwise it might be a relative path.
        new_url = f'{self._image_base_path}{img_url}'

        if validators.url(new_url):
            return new_url

        return None

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
            children=([BrowseMedia(
                can_play=True,
                can_expand=False,
                media_class=MEDIA_CLASS_MUSIC,
                media_content_id=stream.name,
                media_content_type=stream.type,
                title=stream.name + " - " + stream.type,
            ) for stream in streams]).extend(RCA_INPUTS)
        )

    @property
    def supported_features(self):
        """Return flag of media commands that are supported."""

        # if 'stream=' in self._source.input:
        #     stream_id = int(self._source.input.split('=')[1])
        #     stream = next(filter(lambda z: z.id == stream_id, self._streams), None)
        #
        #     if stream is not None and stream.type in (
        #         'spotify',
        #         'pandora'
        #     ):
        #         return SUPPORT_AMPLIPI_MEDIA

        return SUPPORT_AMPLIPI_MEDIA

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
            model="AmpliPi MultiZone Digital Audio Controller",
            name=self._name,
            manufacturer=self._vendor,
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
        return self._name

    async def async_update(self):
        """Retrieve latest state."""
        _LOGGER.info(f'Retrieving state for source {self._source.id}')

        try:
            state = await self._client.get_status()
            source = next(filter(lambda z: z.id == self._source.id, state.sources), None)
            streams = state.streams
        except Exception:
            self._last_update_successful = False
            _LOGGER.error(f'Could not update source {self._source.id}')
            return

        if not source:
            self._last_update_successful = False
            return

        groups = list(filter(lambda z: z.source_id == self._source.id, state.groups))
        zones = list(filter(lambda z: z.source_id == self._source.id, state.zones))

        self.sync_state(source, streams, zones, groups)

    def sync_state(self, state: Source, streams: List[Stream], zones: List[Zone], groups: List[Group]):
        self._source = state
        self._streams = streams
        self._zones = zones
        self._groups = groups
        self._last_update_successful = True

        info = self._source.info

        if info is not None:
            self._attr_media_album_artist = info.artist
            self._attr_media_album_name = info.album
            self._attr_media_title = info.name
            self._attr_media_track = info.track
            self._attr_media_image_url = self.build_url(info.img_url)
            self._attr_media_channel = info.station
        else:
            self._attr_media_album_artist = None
            self._attr_media_album_name = None
            self._attr_media_title = None
            self._attr_media_track = None
            self._attr_media_image_url = None
            self._attr_media_channel = None

    @property
    def state(self):
        """Return the state of the zone."""
        if self._last_update_successful is False:
            return STATE_UNKNOWN
        elif self._source is None:
            return STATE_OFF
        elif self._source.info is None or self._source.info.state is None:
            return STATE_IDLE
        elif self._source.info.name is f'{self._source.name} - rca' and self._source.info.state in (
                'unknown'
        ):
            return STATE_IDLE
        elif self._source.info.state in (
                'paused'
        ):
            return STATE_PAUSED
        elif self._source.info.state in (
                'playing'
        ):
            return STATE_PLAYING
        elif self._source.info.state in (
                'stopped'
        ):
            return STATE_IDLE
        elif self._source.info.state in (
                'stopped'
        ):
            return STATE_IDLE

        return STATE_IDLE

    @property
    def volume_level(self):
        """Volume level of the media player (0..1)."""
        if self._source.vol_delta is None:
            group = next(filter(lambda z: z.vol_delta is not None, self._groups), None)
            zone = next(filter(lambda z: z.vol is not None, self._zones), None)
            if group is not None:
                return group.vol_delta
            elif zone is not None:
                return zone.vol
            return STATE_UNKNOWN

        return db_to_pct(self._source.vol_delta)

    @property
    def is_volume_muted(self) -> bool:
        """Boolean if volume is currently muted."""
        if self._source.mute is None:
            group = next(filter(lambda z: z.mute is not None, self._groups), None)
            zone = next(filter(lambda z: z.mute is not None, self._zones), None)
            if group is not None:
                return group.mute
            elif zone is not None:
                return zone.mute
            return STATE_UNKNOWN

        return self._source.mute

    @property
    def source_list(self):
        """List of available input sources."""
        return [stream.name for stream in self._streams].extend(['rca 1', 'rca 2', 'rca 3', 'rca 4'])

    async def _update_source(self, update: SourceUpdate):
        await self._client.set_source(self._source.id, update)
        await self.async_update()

    async def _update_zones(self, update: ZoneUpdate):
        zones = await self._client.get_zones()
        associated_zones = filter(lambda z: z.source_id == self._source.id, zones)
        for zone in associated_zones:
            await self._client.set_zone(zone.id, update)
        await self.async_update()

    async def _update_groups(self, update: GroupUpdate):
        groups = await self._client.get_groups()
        associated_groups = filter(lambda g: g.source_id == self._source.id, groups)
        for group in associated_groups:
            await self._client.set_group(group.id, update)
        await self.async_update()
