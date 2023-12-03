import configparser
import os

config = configparser.ConfigParser()
if os.getenv('ENV') == 'dev':
    config.read('dev_client.conf')
else:
    config.read('client.conf')

country_codes = config.get('Settings', 'CountryCodes', fallback=None)
if not country_codes:
    country_codes = None
else:
    country_codes = country_codes.split(',')

cutoff_ms = config.get('Settings', 'CutoffMS', fallback=None)
if not cutoff_ms:
    cutoff_ms = 120.0
else:
    cutoff_ms = float(cutoff_ms)

cutoff_load_percentage = config.get('Settings', 'CutoffLoadPercentage', fallback=None)
if not cutoff_load_percentage:
    cutoff_load_percentage = 25
else:
    cutoff_load_percentage = int(cutoff_load_percentage)

cutoff_bias = config.get('Settings', 'CutoffBias', fallback=None)
if not cutoff_bias:
    cutoff_bias = 'none'

_acceptable_bias_values = ['ms', 'msmed', 'none', 'loadmed', 'load']
if cutoff_bias not in _acceptable_bias_values:
    raise ValueError(f'Invalid value for CutoffBias in client.conf. Acceptable values are {_acceptable_bias_values}.')

api = config.get('Settings', 'API')
if not api:
    raise Exception('API not set in client.conf. API is mandatory.')

protocol = config.get('Settings', 'Protocol', fallback=None)
if not protocol:
    protocol = "openvpn_3_udp_443"

device_name = config.get('Settings', 'DeviceName')

try:
    nmcli = config.get("Settings", "NMCLI", fallback=None)
    if not nmcli or nmcli.lower() == "true":
        nmcli = True
    else:
        nmcli = False
except Exception:
    raise Exception("NMCLI is not a boolean value.")
