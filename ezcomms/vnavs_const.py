#
# From a user point of view, a mission is a sequence of operations to
# accomplish a goal or set of goal. It may include both autonomous and
# manual operations.
#
# Technically, the only absolute function of a mission is to log a sequence
# of messages. Everything else about the mission is determined by the mission
# file.
#

# This should be importable anywehre in vnavs, so it should only import system modules.
import configparser
import os
import sys

data_save_topic = "data/save"
data_get_topic = "data/get"
data_put_topic = "data/put"

mission_async_event_topic = "mission/async_event"
mission_load_topic = "mission/load"
mission_loaded_topic = "mission/loaded"
mission_cancel_topic = "mission/cancel"
mission_init_topic = "mission/init"
mission_end_topic = "mission/end"
mission_log_start_topic = "mission/log_start"
mission_log_stop_topic = "mission/log_stop"
mission_mark_topic = "mission/mark"
mission_paused_topic = "mission/paused"
mission_resume_topic = "mission/resume"
mission_stage_completed_topic = "mission/stage_completed"
mission_stage_started_topic = "mission/stage_started"
mission_sync_event_topic = "mission/sync_event"

system_abend_topic = "system/abend"
system_message_error_topic = "system/nak"
system_whoru = "system/whoru"  # fast mqtt server query
system_server = "system/server"  # fast mqtt server id

cameraman_mark_topic = "cameraman/mark"
cameraman_orders_topic = "cameraman/orders"
cameraman_pic_ready_topic = "cameraman/pic_ready"
cameraman_process_topic = "cameraman/process"
cameraman_blob_spec_topic = "cameraman/blob_spec"

engineer_1_gps_topic = "engineer_1/gps"
engineer_1_imu_topic = "engineer_1/imu"
engineer_1_settings_topic = "engineer_1/settings"

helmsman_controls_topic = "helmsman/controls"
helmsman_orders_topic = "helmsman/orders"

navigator_service_topic = "navigator/service"
navigator_service_ack_topic = "navigator_service_ack"
navigator_mode_topic = "navigator/mode"
navigator_plot_topic = "navigator/plot"
navigator_waypoint_topic = "navigator/waypoint"

process_log_list_topic = "process/log_list"
process_clear_missions_topic = "process/clear_missions"
process_result_topic = "process/result"

stage_init = "init"
stage_finis = "finis"

DifferentialGpsClear = "clear"

DEFAULT_CONFIG_FILENAME = "vnavs.ini"
LEGACY_CONFIG_PATH = os.path.expanduser("~/vnavs.ini")
# Backwards-compatible module attribute; prefer resolve_config_path().
config_file_path = LEGACY_CONFIG_PATH
FAST_MQTT_PORT = 4000
FILE_TRANSFER_PORT = 4010
ANY_HOST = ""  # for server, bind to all networks
DEFAULT_PORT = 3000
STANDARD_MQTT_PORT = 1883
VNAVS_IMAGES = "/exports/vnavs_images"
VNAVS_LOGS = "/exports/vnavs_logs"

HOST_LOCAL = "127.0.0.1"
GLOBAL_IP = "8.8.8.8"  # Google DNS resolver
NON_ROUTABLE_IP = "192.168.0.1"

ini_specs = {
    "Cameraman": {
        "ImageDir": VNAVS_IMAGES,
        "Camera": "Picamera2",
        "HFlip": "0",
        "VFlip": "0",
        "Controls": "",  # JSON object of libcamera controls, e.g. {"Sharpness": 2.0}
    },
    "Helmsman": {
        "Type": "donkeycar",
        "I2cBus": "1",
        "I2cAddress": "0x40",
        "PwmFrequencyHz": "60",
        "SteeringChannel": "1",
        "ThrottleChannel": "0",
        "SteeringLeftPwm": "460",
        "SteeringCenterPwm": "375",
        "SteeringRightPwm": "290",
        "ThrottleForwardPwm": "500",
        "ThrottleStoppedPwm": "370",
        "ThrottleReversePwm": "220",
        "ThrottleDeadbandPwm": "0",  # PWM counts to skip the ESC/motor deadband
        "SteeringGain": "0.012",
        "MaxSteeringRadians": "0.6",
        "MaxSpeedCmPerSec": "200",
    },
    "FileClient": {
        "Host": HOST_LOCAL,
        "Port": FILE_TRANSFER_PORT,
        "DownloadDir": "~/vnavs/download",
    },
    "FileServer": {
        "Host": ANY_HOST,
        "Port": FILE_TRANSFER_PORT,
        "xi": VNAVS_IMAGES,
        "xl": VNAVS_LOGS,
    },
    "MqttBroker": {"Host": HOST_LOCAL, "Port": STANDARD_MQTT_PORT},
    "MqttFast": {"Host": HOST_LOCAL, "Port": FAST_MQTT_PORT},
    "MqttFastServer": {
        "Host": ANY_HOST,
        "Port": FAST_MQTT_PORT,
        "ArchiveDir": VNAVS_LOGS,
    },
    "MissionControl": {"Scripts": "~/vnavs/scripts"},
    "Navigator": {"missiondir": "~/vnavs/missions", "speed_method": "automatic"},
}


def resolve_config_path(config_path=None):
    """Decide which ``vnavs.ini`` to use.

    Priority:
      1. an explicit ``config_path`` (rarely needed -- e.g. a test or a tool
         driving several robots),
      2. ``vnavs.ini`` in the current working directory -- the normal case,
         where each robot has a "launch directory" holding its ini plus the
         shell scripts that start the nodes,
      3. the legacy ``~/vnavs.ini``.
    """
    if config_path:
        return os.path.expanduser(config_path)
    cwd_ini = os.path.join(os.getcwd(), DEFAULT_CONFIG_FILENAME)
    if os.path.isfile(cwd_ini):
        return cwd_ini
    return LEGACY_CONFIG_PATH


def read_config(config_path=None):
    resolved = resolve_config_path(config_path)
    config = configparser.ConfigParser()
    try:
        config.read_file(open(resolved))
    except FileNotFoundError:
        sys.exit(
            "Missing config file: {}\n"
            "Create it with:\n"
            '  python3 -c "from ezcomms import vnavs_const; vnavs_const.UpdateIni()"'.format(
                resolved
            )
        )
    return config


def CheckDirectory(dir_name, source, IsWriteable=True):
    expanded_dir_name = os.path.expanduser(dir_name)  # this expands tilde in path
    if not os.path.isdir(expanded_dir_name):
        raise ValueError(
            "Invalid directory path '{}' in {}".format(expanded_dir_name, source)
        )
    if IsWriteable:
        if not os.access(expanded_dir_name, os.W_OK):
            raise ValueError(
                "Directory path '{}' in {} is not writeable".format(
                    expanded_dir_name, source
                )
            )
    return expanded_dir_name


def UpdateIni(IniPath=None):
    if IniPath is None:
        IniPath = os.path.join(os.getcwd(), DEFAULT_CONFIG_FILENAME)
    config = configparser.ConfigParser()
    config.read(IniPath)
    for section_name, section_specs in ini_specs.items():
        for item_name, item_default in section_specs.items():
            try:
                current_value = config[section_name][item_name]
            except KeyError:
                if section_name not in config.sections():
                    config.add_section(section_name)
                config[section_name][item_name] = str(item_default)
            # print(section_name, item_name, current_value)
    with open(IniPath, "w") as configfile:
        config.write(configfile)


if __name__ == "__main__":
    if sys.argv[1] == "i":
        # UpdateIni(IniPath='test.ini')
        UpdateIni()
