# CameraMotionSensor 
This repository is used to build and run an executable file that runs on a Raspberry Pi Pico to operate the photo-capturing motion sensor device. It also sets up the Serial USB listener on the host machine to receive photos from the Pico device and communicate with services on the Cloud. The source code in this repo uses the ArduCAM/RPI-Pico-Cam header files from https://github.com/ArduCAM/RPI-Pico-Cam
 
# Device Setup
## Materials needed
- Raspberry Pi Pico
- Arducam Mini 2MP Plus
- Elegoo HC-SR04 Ultrasonic Module Distance Sensor
- Bread board 
- Wires
- USB

## Wiring 
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
(cd  Project/C && mkdir build)
(cd Project/C/build && cmake ..)
(cd Project/C/build && make)
```

# Run serial listener on host machine and executable on Raspberry Pi Pico

## Requirements
This code requires the following to run:

  * [python3][python] 3.7+
  * [pip3][pip] 23.0+


[python]: https://www.python.org/downloads/
[pip]: https://pypi.org/project/pip/

Install the necessary python dependencies:

```bash
pip install -r Project/Python/requirements.txt
```
## Start Up
Connect the Pico device to your linux computer or machine. Then run the following command to reset your Pico

```bash
sudo ./bootselBoot b
```
This will reset your Pico so you can flash a new executable file on it. You can verify the successs of the above command by:

```bash
$ dmesg | tail
[ 371.973555] sd 0:0:0:0: [sda] Attached SCSI removable disk
```
Now you can finally start the listener and executable with the command:

```bash
sudo Python3 Project/Python/src/listener.py
```

This will set up the listening program on the host machine while running the executable on the Pico. The listening program will receive photos from the Pico upon motion detection, and subsequently store the photos on the cloud as well as trigger the notification of the device owner. 

## Termination
You can terminate the listener program on the host machine through ```CTRL^Z``` or ```CTRL^C```. To terminate the program on the Pico device and reset it, run once again: 

```bash
sudo ./bootselBoot b
```

You can later re-run your program by following the steps in **Start Up**
