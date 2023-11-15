import requests
import json
from ping3 import ping, verbose_ping
import configparser

config = configparser.ConfigParser()
config.read('client.conf')

country_codes = config.get('Settings', 'CountryCodes', fallback="").split(',')
if not country_codes or country_codes == ['']: raise Exception("There were no country codes present in client.conf")
cutoff_ms = float(config.get('Settings','CutoffMS', fallback="120"))
cutoff_load_percentage = int(config.get("Settings", "CutoffLoadPercentage", fallback="25"))
vpn = requests.get("https://airvpn.org/api/status/")
vpn_json = json.loads(vpn.content)
valid_servers = []
for server in vpn_json['servers']:
    if server["country_code"] not in country_codes: continue
    if server["health"] != "ok": continue
    if server["currentload"] > cutoff_load_percentage: continue
    ping_ms = ping(server["ip_entry"]) * 1000
    if ping_ms > cutoff_ms: continue
    valid_servers.append(server)
print(valid_servers)
# print(vpn_json)