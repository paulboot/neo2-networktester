#!/usr/bin/env python3

"""
NanoHAT OLED for Armbian: NanoHAT OLED and GPIO Button Control for Armbian
MIT License
"""

from PIL import Image, ImageDraw, ImageFont
import gpiod
import os
import smbus
import subprocess
import time
import socket
import re

DISPLAY_OFF_TIMEOUT = 30
cmd_index = 0
current_time = time.time()
display_refresh_time = 0
display_off_time = current_time + DISPLAY_OFF_TIMEOUT

print('[DEBUG] Opening I2C bus...')
i2c0_bus = smbus.SMBus(0)

print('[DEBUG] Testing I2C write...')
try:
    i2c0_bus.write_byte_data(0x3C, 0x00, 0xAE)
    print('[DEBUG] I2C write succeeded.')
except Exception as e:
    print(f'[ERROR] I2C write failed: {e}')

image = Image.new("1", (128, 64))
image_draw = ImageDraw.Draw(image)

print('[DEBUG] Loading fonts...')
image_font8 = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", 8)
image_font10 = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", 10)
image_font15 = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", 15)
image_font25 = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", 25)

key1_cmd_index = 0
key2_cmd_index = 1
key3_cmd_index = 2

shutdown_time = 0

def get_ipv4():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('192.168.3.1', 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = '0.0.0.0'
    finally:
        s.close()
    return f"IP4: {ip}"

def download_speedtest():
    try:
        result = subprocess.run(
            ["iperf3", "-c", "185.216.141.19", "-t", "5", "-R"],
            capture_output=True,
            text=True,
            timeout=10
        )
        output = result.stdout
    except Exception as e:
        output = f"iperf3 failed: {e}"

    # Zoek regels met interval-data, bijvoorbeeld: "[  5]   1.00-2.00   sec  11.0 MBytes  92.3 Mbits/sec"
    lines = [line for line in output.splitlines() if re.search(r"\[\s*\d+\]\s+\d", line)]

    # Parse de bitrates
    bitrates = []
    for line in lines:
        match = re.search(r"(\d+\.\d+)\s+Mbits/sec", line)
        if match:
            bitrates.append(f"{match.group(1)} Mb/s")
        else:
            bitrates.append("N/A")

    # Zorg voor precies 5 regels
    while len(bitrates) < 5:
        bitrates.append("...")

    return bitrates

def upload_speedtest():
    try:
        result = subprocess.run(
            ["iperf3", "-c", "185.216.141.19", "-t", "5"],
            capture_output=True,
            text=True,
            timeout=10
        )
        output = result.stdout
    except Exception as e:
        output = f"iperf3 failed: {e}"

    # Zoek regels met interval-data, bijvoorbeeld: "[  5]   0.00-1.00   sec   384 KBytes  3.14 Mbits/sec    0   47.2 KBytes"
    lines = [line for line in output.splitlines() if re.search(r"\[\s*\d+\]\s+\d", line)]

    # Parse de bitrates
    bitrates = []
    for line in lines:
        match = re.search(r"(\d+\.\d+)\s+Mbits/sec", line)
        if match:
            bitrates.append(f"{match.group(1)} Mb/s")
        else:
            bitrates.append("N/A")

    # Zorg voor precies 5 regels
    while len(bitrates) < 5:
        bitrates.append("...")

    return bitrates


def write_i2c_image_data(i2c_bus, image):
    block_data = []
    image_data = image.load()
    for page in range(8):
        for x in range(128):
            byte = 0
            for bit in reversed(range(8)):
                byte = (byte << 1) | (1 if image_data[x, page * 8 + bit] else 0)
            block_data.append(byte)
            if len(block_data) == 32:
                i2c_bus.write_i2c_block_data(0x3C, 0x40, block_data)
                block_data = []
    if block_data:
        i2c_bus.write_i2c_block_data(0x3C, 0x40, block_data)

try:
    print('[DEBUG] Initializing GPIO lines...')
    chip = gpiod.Chip("/dev/gpiochip0")
    lines = {
        "F1": chip.get_line(0),
        "F2": chip.get_line(2),
        "F3": chip.get_line(3),
    }

    for name, line in lines.items():
        line.request(consumer=name, type=gpiod.LINE_REQ_DIR_IN)

    print('[DEBUG] Sending OLED init sequence...')
    i2c0_bus.write_i2c_block_data(0x3C, 0x00, [
        0xAE, 0x00, 0x10, 0x40, 0xB0, 0x81, 0xCF, 0xA1, 0xA8, 0x3F,
        0xC8, 0xD3, 0x00, 0xD5, 0x80, 0xD9, 0xF1, 0xDA, 0x12,
        0xDB, 0x40, 0x8D, 0x14, 0xA6, 0x20, 0x00, 0xAF
    ])
    print('[DEBUG] OLED init complete.')

    print('[DEBUG] Clearing display...')
    image_draw.rectangle((0, 0, 128, 64), 0)
    write_i2c_image_data(i2c0_bus, image)

    print('[DEBUG] Writing splash image to OLED...')
    if os.path.exists("splash.png"):
        splash = Image.open("splash.png")
        image.paste(splash)
        write_i2c_image_data(i2c0_bus, image)
        splash.close()
    else:
        print("[WARNING] splash.png not found")
    #display_refresh_time = current_time + DISPLAY_OFF_TIMEOUT
    time.sleep(3)

    print('[DEBUG] Entering main loop...')
    cmd_index = 1
    while True:
        time.sleep(0.05)
        current_time = time.time()
        button_state = {name: line.get_value() for name, line in lines.items()}
        #print(f"[DEBUG] Button states: F1={button_state['F1']} F2={button_state['F2']} F3={button_state['F3']}")

        if button_state['F1'] == 1:
            cmd_index = 1
        elif button_state['F2'] == 1:
            cmd_index = 2
        elif button_state['F3'] == 1:
            cmd_index = 3

        if cmd_index == 0:
            print('[DEBUG] Writing splash image to OLED...')
            if os.path.exists("splash.png"):
                splash = Image.open("splash.png")
                image.paste(splash)
                write_i2c_image_data(i2c0_bus, image)
                splash.close()
            else:
                print("[WARNING] splash.png not found")
            display_refresh_time = current_time + DISPLAY_OFF_TIMEOUT
        elif cmd_index == 1:
            text1 = time.strftime("%A")
            text2 = time.strftime("%e %b %Y")
            text3 = time.strftime("%X")
            image_draw.rectangle((0, 0, 128, 64), 0)
            image_draw.text((6, 2), text1, 1, image_font15)
            image_draw.text((6, 20), text2, 1, image_font15)
            image_draw.text((6, 36), text3, 1, image_font25)
            write_i2c_image_data(i2c0_bus, image)
        elif cmd_index == 2:
            text1 = get_ipv4()

            try:
                ip_output = subprocess.check_output(
                    "ip -4 addr show dev end0 | grep 'inet ' | awk '{print $2}'",
                    shell=True,
                    text=True,
                ).strip()
                subnet = ip_output.split("/")[1] if "/" in ip_output else "?"
            except Exception:
                subnet = "?"

            try:
                gateway = subprocess.check_output(
                    "ip route | grep default | awk '{print $3}'",
                    shell=True,
                    text=True,
                ).strip()
            except Exception:
                gateway = "?"

            try:
                dns = subprocess.check_output(
                    "resolvectl status | awk '/Current DNS Server:/ { print $4; exit }'",
                    shell=True,
                    text=True,
                ).strip()
            except Exception:
                dns = "?"

            try:
                domain = subprocess.check_output(
                    "resolvectl status | awk '/DNS Domain:/ { print $3; exit }'",
                    shell=True,
                    text=True,
                ).strip()
            except Exception:
                domain = "?"

            text2 = f"Sub: /{subnet}"
            text3 = f"Def: {gateway}"
            text4 = f"Dns: {dns}"
            text5 = f"Dom: {domain}"

            image_draw.rectangle((0, 0, 128, 64), 0)
            image_draw.text((6, 2), text1, 1, image_font10)
            image_draw.text((6, 14), text2, 1, image_font10)
            image_draw.text((6, 26), text3, 1, image_font10)
            image_draw.text((6, 38), text4, 1, image_font10)
            image_draw.text((6, 50), text5, 1, image_font10)
            write_i2c_image_data(i2c0_bus, image)
        elif cmd_index == 3:
            image_draw.rectangle((0, 0, 128, 64), 0)
            image_draw.text((6, 2), "Download test...", 1, image_font10)
            write_i2c_image_data(i2c0_bus, image)

            bitrates = download_speedtest()
            image_draw.rectangle((0, 0, 128, 64), 0)
            for i, rate in enumerate(bitrates[:5]):
                image_draw.text((6, 2 + i * 12), rate, 1, image_font10)
            write_i2c_image_data(i2c0_bus, image)
            time.sleep(5)

            image_draw.rectangle((0, 0, 128, 64), 0)
            image_draw.text((6, 2), "Upload test...", 1, image_font10)
            write_i2c_image_data(i2c0_bus, image)

            bitrates = upload_speedtest()
            image_draw.rectangle((0, 0, 128, 64), 0)
            for i, rate in enumerate(bitrates[:5]):
                image_draw.text((6, 2 + i * 12), rate, 1, image_font10)
            write_i2c_image_data(i2c0_bus, image)
            time.sleep(5)

            cmd_index = 1


except KeyboardInterrupt:
    print("[DEBUG] CTRL+C detected")

finally:
    print('[DEBUG] Cleaning up...')
    try:
        i2c0_bus.write_i2c_block_data(0x3C, 0x00, [0xAE])
    except Exception as e:
        print(f'[ERROR] Failed to turn off display: {e}')

    for line in lines.values():
        try:
            line.release()
        except Exception as e:
            print(f"[ERROR] GPIO release failed: {e}")

    chip.close()
    print('[DEBUG] GPIO released.')

    if cmd_index == 99:
        print('[DEBUG] Initiating shutdown...')
        os.system("shutdown now")
