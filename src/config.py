import configparser
import os

config = configparser.ConfigParser()
if os.getenv('ENV') == 'dev':
    config.read('dev_client.conf')
else:
    config.read('client.conf')

country_codes = config.get('Settings', 'CountryCodes', fallback='').split(',')
if not country_codes or country_codes == ['']:
    raise Exception('There were no country codes present in client.conf')
cutoff_ms = float(config.get('Settings', 'CutoffMS', fallback='120'))
cutoff_load_percentage = int(config.get('Settings', 'CutoffLoadPercentage', fallback='25'))
cutoff_bias = config.get('Settings', 'CutoffBias', fallback='none')
_acceptable_bias_values = ['ms', 'msmed', 'none', 'loadmed', 'load']
if cutoff_bias not in _acceptable_bias_values:
    raise ValueError(f'Invalid value for CutoffBias in client.conf. Acceptable values are {_acceptable_bias_values}.')
api = config.get('Settings', 'API')
if not api:
    raise Exception('API not set in client.conf. API is mandatory.')
protocol = config.get('Settings', 'Protocol', fallback="openvpn_3_udp_443")
device_name = config.get('Settings', 'DeviceName')
try:
    if config.get("Settings", "NMCLI", fallback="True") == "True" or config.get("Settings", "NMCLI", fallback="true") == "true":
        nmcli = True
    else:
        nmcli = False
except Exception:
    raise Exception("NMCLI is not a boolean value.")
