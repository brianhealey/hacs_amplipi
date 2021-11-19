# AmpliPi Plugin for Home Assistant

This component adds support for auto-discovery and configuration of
AmpliPi Groups and Zones.

If you like this component, please give it a star on [github](https://github.com/brianhealey/hacs_amplipi).

## Installation

1. Ensure that [HACS](https://hacs.xyz) is installed.
2. Install **AmpliPi** integration via HACS.
3. **AmpliPi** integration should auto-discover your AmpliPi, and prompt you to configure the integration

   [![](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start?domain=amplipi)

In case you would like to install manually:

1. Copy the folder `custom_components/amplipi` to `custom_components` in your Home Assistant `config` folder.
2. **AmpliPi** integration should auto-discover your AmpliPi, and prompt you to configure the integration

   [![](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start?domain=amplipi)

AmpliPi devices do not report a distinct identifier, so this integration currently only supports one controller per installation.

Each Zone and Group will be auto-discovered and a separate `media_player` entity will be created per zone.

The AmpliPi Media Player entities support:
- Play
- Pause
- Off
- On
- PA