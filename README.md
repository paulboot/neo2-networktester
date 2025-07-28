# neo2-networktester
Python3 and Bash scripts to use the ARM Neo2 as a network tester


## Image download
This is currently the only image I could find that does not crash after the netwotk interface becomes active.
* Image: `Armbian_community_25.8.0-trunk.309_Nanopineo_noble_current_6.12.35.img.xz`
* Download: https://github.com/armbian/community/releases/download/25.8.0-trunk.309/Armbian_community_25.8.0-trunk.309_Nanopineo_noble_current_6.12.35.img.xz

## Installation

### Prevent kernel updates
Kernel development for the Neo2 is very unstable most images will will not boot anymore after kernel upgrades.

```
sudo apt-mark hold linux-image-current-sunxi
sudo apt-mark hold linux-dtb-current-sunxi
sudo apt-mark hold armbian-bsp-cli-nanopineo-current
apt-mark showhold
echo 'ARMBIAN_NO_UBOOT_INITRD=1' | sudo tee -a /etc/environment
sudo chmod -x /etc/initramfs/post-update.d/99-uboot
sudo chattr +i /etc/initramfs/post-update.d/99-uboot
```

Install needed packages.

```
sudo apt update && sudo apt -y upgrade

sudo apt -y install \
  git \
  vim \
  isc-dhcp-client \
  python3 \
  python3-libgpiod \
  python3-pil \
  python3-smbus \
  i2c-tools \
  fonts-dejavu-core
```

## Settings
Enable i2c0:

```
sudo nano /boot/armbianEnv.txt
```

Then add `i2c0` with a space seperating it from the other values:

```
overlays=i2c0 usbhost1 usbhost2
```

Save these changes by pressing `ctrl+x`, `ctrl+y` and `enter` as prompted at the bottom of the screen.

Reboot the system for the changes to take effect:

```
sudo reboot now
```

### Detect hardware

Next, scan the bus for connected devices:

```
sudo i2cdetect -y 0
```

Look for the OLED’s I²C address—usually **0x3c**. You should see it in the output grid.
### Clone repo and install code

```
git clone https://github.com/paulboot/neo2-networktester.git
cp -a ./neo2-networktester/* /usr/local/bin/
```

### Automatic Startup

For now add to the `/etc/rc.local`

```
#!/bin/sh -e
#
# rc.local
#
# This script is executed at the end of each multiuser runlevel.
# Make sure that the script will "exit 0" on success or any other
# value on error.
#
# In order to enable or disable this script just change the execution
# bits.
#
# By default this script does nothing.
cd /usr/local/bin
nice -n 10 /usr/bin/python3 oled-start.py &

exit 0
```
