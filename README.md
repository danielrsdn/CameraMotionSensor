# CameraMotionSensor 
This repository is used to build an executable file that runs on a Raspberry Pi Pico to operate the photo-capturing motion sensor device. The source code in this repo uses the ArduCAM/RPI-Pico-Cam header files from https://github.com/ArduCAM/RPI-Pico-Cam

# Device Setup
## Materials needed
- Raspberry Pi Pico
- Arducam Mini 2MP Plus
- Elegoo HC-SR04 Ultrasonic Module Distance Sensor
- Bread board 
- Jumperwires 
- Breadboard
- USB
## Configuration

# Compile and build executable file
```bash
cd  PICO_SPI_CAM/C
mkdir build
cd build
cmake ..
make 
```
## Run executable on Raspberry Pi Pico
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
Copy your arducam_demo.uf2 onto RP2040:
sudo cp arducam_demo.uf2 /mnt/pico
sudo sync
```