import requests
import json
from ping3 import ping, verbose_ping
import config
import subprocess
import tempfile
import os
import time


def main():
    vpn = get_vpn_data("https://airvpn.org/api/status/")
    vpn_json = json.loads(vpn.content)
    valid_servers = []
    i = 0
    while not valid_servers and i < 20:
        for server in vpn_json['servers']:
            if config.country_codes:
                if server['country_code'] not in config.country_codes:
                    continue
            if server['health'] != 'ok':
                continue
            if server['currentload'] > config.cutoff_load_percentage:
                continue
            try:
                ping_ms = ping(server['ip_v4_in1']) * 1000
            except Exception:
                continue
            if ping_ms > config.cutoff_ms:
                continue
            server['ping'] = ping_ms
            server['score'] = calculate_score(server, config.cutoff_bias, config.cutoff_ms, config.cutoff_load_percentage)
            # print(server)
            valid_servers.append(server)
            valid_servers.sort(key=lambda x: x['score'], reverse=True)
        if not valid_servers:
            config.cutoff_ms += 50
            config.cutoff_load_percentage += 5
        i += 1

    if not valid_servers:
        raise Exception("No acceptable servers were found!")

    headers = {
        "API-KEY": config.api
    }
    response = requests.get(f"https://airvpn.org/api/generator/?protocols={config.protocol}&servers={valid_servers[0]['public_name']}&device={config.device_name}", headers=headers)
    stop_active_vpn_connections()
    if "openvpn" in config.protocol:
        if not config.nmcli:
            connect_to_openvpn(response.text)
        else:
            connect_to_openvpn_with_nmcli(response.text)
    else:
        connect_to_wireguard(response.text)
    print("Connected\n\n")
    print(valid_servers[0])


def get_vpn_data(url, retries=5, backoff_factor=10):
    for i in range(retries):
        try:
            response = requests.get(url)
            response.raise_for_status()
            return response  # or whatever processing you need
        except requests.exceptions.RequestException as e:
            if i == retries - 1:  # If this was the last attempt
                raise "Could not connect to server"
            else:
                time.sleep(backoff_factor * (2 ** i))  # exponential back-off


def calculate_score(server, cutoff_bias, cutoff_ms, cutoff_load_percentage):
    normalized_ping = server['ping'] / cutoff_ms
    normalized_load = server['currentload'] / cutoff_load_percentage

    if cutoff_bias == 'ms':
        weight_ping = 0.8
        weight_load = 0.2
    elif cutoff_bias == 'msmed':
        weight_ping = 0.65
        weight_load = 0.35
    elif cutoff_bias == 'msload':
        weight_ping = 0.35
        weight_load = 0.65
    elif cutoff_bias == 'load':
        weight_ping = 0.2
        weight_load = 0.8
    else:
        weight_ping = 0.5
        weight_load = 0.5

    score = 100 * (1-(weight_ping * normalized_ping + weight_load * normalized_load))

    return score


script_dir = os.path.dirname(os.path.realpath(__file__))


def connect_to_wireguard(config_text):
    path = os.path.join("/etc/wireguard", "AirBuddyWG.conf")
    with open(path, 'w') as file:
        file.write(config_text)
    command = ['wg-quick', 'up', path]
    process = subprocess.run(command, capture_output=True, text=True)
    if process.returncode != 0:
        print(f'Could not connect to Wireguard server: {process.stderr}')
    else:
        print('Connected to WireGuard server.')


def connect_to_openvpn(config_text):
    # Write the configuration text to a file
    path = "/etc/openvpn/client/AirBuddy.conf"
    with open(path, 'w') as file:
        file.write(config_text)

    # Start the VPN connection with systemd
    start_command = ['systemctl', 'start', 'openvpn-client@AirBuddy']
    process = subprocess.run(start_command, capture_output=True, text=True)
    if process.returncode != 0:
        print(f'Could not start OpenVPN connection: {process.stderr}')
    else:
        print('Connected to OpenVPN server.')


def connect_to_openvpn_with_nmcli(config_text):

    # Write the configuration text to a file
    path = os.path.join("/tmp", "AirBuddy.ovpn")
    try:
        with open(path, 'w') as file:
            file.write(config_text)
        # Check if the connection already exists
        show_command = ['nmcli', 'connection', 'show', "AirBuddy"]
        process = subprocess.run(show_command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if process.returncode == 0:
            # If the connection exists, delete it
            delete_command = ['nmcli', 'connection', 'delete', "AirBuddy"]
            subprocess.run(delete_command, check=True)
        # Import the configuration file with nmcli
        import_command = ['nmcli', 'connection', 'import', 'type', 'openvpn', 'file', path]
        process = subprocess.run(import_command, capture_output=True, text=True)
        if process.returncode != 0:
            print(f'Could not import OpenVPN configuration: {process.stderr}')
            return

        # Start the VPN connection with nmcli
        start_command = ['nmcli', 'connection', 'up', "AirBuddy"]
        process = subprocess.run(start_command, capture_output=True, text=True)
        if process.returncode != 0:
            print(f'Could not start OpenVPN connection: {process.stderr}')
        else:
            print('Connected to OpenVPN server.')
    finally:
        os.remove(path)


def stop_active_vpn_connections():

    # Check for active WireGuard connections
    wg_show_command = ['sudo', 'wg', 'show', "AirBuddyWG"]
    process = subprocess.run(wg_show_command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if process.returncode == 0:
        wgpath = os.path.join("/etc/wireguard", "AirBuddyWG.conf")
        # If a WireGuard connection is active, stop it
        wg_stop_command = ['wg-quick', 'down', wgpath]
        subprocess.run(wg_stop_command, check=True)

    # Check for active OpenVPN connections
    openvpn_show_command = ['systemctl', 'is-active', 'openvpn-client@AirBuddy']
    process = subprocess.run(openvpn_show_command, stdout=subprocess.PIPE, text=True)
    if process.stdout.strip() == 'active':
        # If an OpenVPN connection is active, stop it
        openvpn_stop_command = ['systemctl', 'stop', 'openvpn-client@AirBuddy']
        subprocess.run(openvpn_stop_command, check=True)

        # Remove the OpenVPN configuration file
        os.remove("/etc/openvpn/client/AirBuddy.conf")

    # Check for active NetworkManager VPN connections
    nmcli_show_command = ['nmcli', 'connection', 'show', '--active', "AirBuddy"]
    process = subprocess.run(nmcli_show_command, capture_output=True, text=True)
    if "AirBuddy" in process.stdout:
        # If a NetworkManager VPN connection is active, stop it
        nmcli_stop_command = ['nmcli', 'connection', 'down', "AirBuddy"]
        subprocess.run(nmcli_stop_command, check=True)


main()
