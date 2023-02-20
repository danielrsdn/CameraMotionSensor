# CameraMotionSensor 
This repository is used to build an executable file that runs on a Raspberry Pi Pico to operate the photo-capturing motion sensor device. The source code in this repo uses the ArduCAM/RPI-Pico-Cam header files from https://github.com/ArduCAM/RPI-Pico-Cam

# Device Setup
## Materials needed
- Raspberry Pi Pico
- Arducam Mini 2MP Plus
- Elegoo HC-SR04 Ultrasonic Module Distance Sensor
- Bread board 
- Male-Male Jumperwires 
- USB
## Configuration
### Configure Arducam Mini 2MP Plus to Pico:
| Arducam | Pico |   
| --------|:----:| 
| CS      | GP5  | 
| MOSI    | GP3  |   
| MISO    | GP4  |    
| SCK     | GP2  |    
| GND     | GND  |  
| VCC     | 3.3V |  
| SDA     | GP8  |
| SCL     | GP9  |

### Configure Elegoo HC-SR04 Ultrasonic Module Distance Sensor to Pico:
| Sensor  | Pico |   
| --------|:----:| 
| VCC     | VBUS | 
| TRIG    | GP16 |   
| ECHO    | GP15 |    
| GND     | GND  |    

# Build executable file
## Install dependencies 
These instructions are limited to linux-based systems only. Please see https://datasheets.raspberrypi.com/pico/raspberry-pi-pico-c-sdk.pdf for instructions on other platforms. 

1. Install CMake (at least version 3.13), and GCC cross compiler
```bash
sudo apt install cmake gcc-arm-none-eabi libnewlib-arm-none-eabi libstdc++-arm-none-eabi-newlib
```

2. Clone Raspberry Pi Pico SDK in this root directory
```bash
git clone https://github.com/raspberrypi/pico-sdk.git
```

3. Initialize tinyUsb submodule
```bash
cd pico-sdk
git submodule update --init
```

4. Set PICO_SDK_PATH to this sdk
```bash
export PICO_SDK_PATH=$PWD/pico-sdk
```
## Compile and build executable

```bash
cd  Project/C
mkdir build
cd build
cmake ..
make 
```
# Run executable on Raspberry Pi Pico
Connect the Pico device to your computer or machine running the local server. If you have a monitor and keyboard setup, you can drag generated .uf2 file in ```build``` into the board. You can also do this manually:
```
$ dmesg | tail
[ 371.973555] sd 0:0:0:0: [sda] Attached SCSI removable disk
$ sudo mkdir -p /mnt/pico
sudo mount /dev/sda1 /mnt/pico
```

If you can see files in /mnt/pico then the USB Mass Storage Device has been mounted correctly:

```
$ ls /mnt/pico/
INDEX.HTM INFO_UF2.TXT
Copy your Main.uf2 onto RP2040:
sudo cp Main.uf2 /mnt/pico
sudo sync
```
