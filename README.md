# ezcomms

Communication and data layer extracted from the VNAVS robotics framework.

Provides pub/sub messaging, MQTT client wrappers, socket abstractions, and a typed data attribute system for inter-node communication.

## Config file (vnavs.ini)

Any node that connects via `VnavsNode` or `SocketWrapper` reads settings (hosts, ports, directories) from an ini file at `~/vnavs.ini`. This file is not created automatically — on a fresh install it won't exist yet, and connecting before creating it fails with a "Missing config file" message.

Create or update it with the defaults in `vnavs_const.ini_specs`:

```bash
python3 -c "from ezcomms import vnavs_const; vnavs_const.UpdateIni()"
```

This writes any missing sections/keys to `~/vnavs.ini` (existing values are left untouched), covering sections like `Cameraman`, `MqttBroker`, `MqttFast`, `MqttFastServer`, `FileClient`, `FileServer`, `MissionControl`, and `Navigator`. Edit the resulting file by hand afterward to change hosts, ports, or paths for your setup.
