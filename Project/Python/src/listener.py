import serial
import time
import adafruit_board_toolkit.circuitpython_serial
import sys
import datetime
import subprocess
import os
import requests
import face_recognition
from multiprocessing import Process, Queue
import json

DMESG_CMD = "/usr/bin/dmesg"
TAIL_CMD = "/usr/bin/tail"
GREP_CMD = "/usr/bin/grep"
CREATE_NESTED_DIR_CMD = "mkdir"
MOUNT_CMD = "mount"
CP_CMD = "cp"
SYNC_CMD = "sync"
LIST_CMD = "ls"

PATTERN_1 = '''"sd.*: sd.*"'''
PATTERN_2 = '''"sd.[0-9]"'''

DEV_DIR = "/dev"
MNT_DIR = "/mnt/pico"

USB_DEVICE = DEV_DIR + "/ttyACM*"

UF2_FILE_PATH = '''./Project/C/build/src/Main/Main.uf2'''

Headers = {"session_id": "testkey"}
UPLOAD_URL = "https://ljgqi1zvt4.execute-api.us-west-2.amazonaws.com/v1/upload"
NOTIFY_URL = "https://ljgqi1zvt4.execute-api.us-west-2.amazonaws.com/v1/notify"


class LambdaAPI:
    @staticmethod
    def uploadAndNotifyImage(image):
        response = requests.get(UPLOAD_URL, headers=Headers)
        if response.status_code == 200:
            response = response.json()
            if response['httpRequest'] == 'PUT':
                with open(image, "rb") as i:
                    imageData = i.read()
                    response2 = requests.put(response['url'], data=imageData, headers=response['headers'])
                    if (response2.status_code // 200) == 1:
                        response3 = requests.put(NOTIFY_URL, data=json.dumps({'photoName': response['photoName']}), headers=Headers)
                        if (response3.status_code // 200 == 1):
                            print("Succesfully uploaded image and notified device owner(s)")


class ImageAnalyzer:
    @staticmethod
    def detectFace(imagePath, queue):
        image = face_recognition.load_image_file(imagePath)
        face_locations = face_recognition.face_locations(image)
        if len(face_locations) > 0:
            queue.put(imagePath)

class ImageHandler:
    def __init__ (self):
        self.queue = Queue()
    
    def validateImage(self, image):
        Process(target=ImageAnalyzer.detectFace, args=(image, self.queue))

    def getValidatedImage(self):
        try:
            image = self.queue.get(block=False)
            return image
        except Queue.Empty:
            return None
    
    def clearQueue(self):
        self.queue = Queue()


class Listener:
    def __init__ (self, device, imageHandler):
        self.device = device
        self.buffer = bytes()
        self.imageHandler = imageHandler
    
    def listen(self):
        lastTimeNoRead = None
        imageBurstStart = None
        while True:
            if self.device.in_waiting > 0:
                lastTimeNoRead = time.time()
                response = self.device.read(self.device.in_waiting)

                if bytes("Out of memory", 'utf-8') in response:
                    lastTimeNoRead = None
                    self.buffer = bytes() 
                    continue

                if bytes("Begin capturing images?", 'utf-8') in response:
                    print(response)
                    # write q for quit, write s for stop 
                    imagePath =  self.imageHandler.getValidatedImage()
                    if imageBurstStart is None:
                        imageBurstStart = time.time()
                    if (imagePath is None) and ((time.time() - imageBurstStart) < 5):
                        print("no human face detected yet, keep capturing: c")
                        self.device.write(bytes("c", 'utf-8'))
                    elif (imagePath is None):
                        print("no human face detected after 5 seconds: s")
                        self.device.write(bytes("s", 'utf-8'))
                        imageBurstStart = None
                    else:  
                        print("detected Face: s")
                        self.device.write(bytes("s", 'utf-8'))
                        self.imageHandler.clearQueue()
                        imageBurstStart = None
                        LambdaAPI.uploadAndNotifyImage(imagePath)

                    lastTimeNoRead = None
                    self.buffer = bytes() 
                    continue

                if bytes("done", 'utf-8') in response:
                    print("Read image from Pico")
                    response = response.split(bytes("done", 'utf-8'))[0]
                    self.buffer = self.buffer + response
                    print("Got new picture!")
                    imageName = "/tmp/image_" + datetime.datetime.today().strftime("%d-%b-%Y-%H-%M-%S-%f") +  ".jpeg";
                    image = open(imageName, "wb+")
                    image.write(self.buffer)
                    image.close()
                    self.imageHandler.validateImage(imageName)
                    lastTimeNoRead = None

                self.buffer = self.buffer + response
                
            elif lastTimeNoRead is None:
                continue
            elif (time.time() - lastTimeNoRead) < 20:
                continue
            else:
                break

def kill(s):
    print(f'{sys.argv[0]}: {s}', file=sys.stderr)
    sys.exit(1)

def start():
    comports = adafruit_board_toolkit.circuitpython_serial.data_comports()
    device_COM = None
    while device_COM is None:
        cp = subprocess.run([LIST_CMD + " -a " + USB_DEVICE], shell=True, stdout=subprocess.PIPE)
        if cp.returncode == 0:
            device_COM = cp.stdout.decode("utf-8").split("\n")[0]
        else:
            print("Still waiting to detect usb device")
            time.sleep(1)

    print("detected device_COM: " + device_COM)
    lastTimeNoRead = None
    s3 = boto3.resource('s3')
    #if not comports:
        #kill("No comports module found")

    device = serial.Serial(device_COM, baudrate=115200)
    imageHandler = ImageHandler()
    listener = Listener(imageHandler)
    try: 
        listener.listen()
    finally:
        device.close()
    

def flash():
     #Create tmp directory
     if subprocess.run([CREATE_NESTED_DIR_CMD, "-p", MNT_DIR]).returncode != 0:
         kill("Cannot create mounted directory")

     disk_file = subprocess.run([GREP_CMD + " -o " + PATTERN_2], stdout=subprocess.PIPE, input=subprocess
               .run([GREP_CMD + " -o " + PATTERN_1], stdout=subprocess.PIPE, input=subprocess
               .run([TAIL_CMD], stdout=subprocess.PIPE, input=subprocess
                    .run([DMESG_CMD], stdout=subprocess.PIPE).stdout).stdout, shell=True).stdout, shell=True).stdout.decode("utf-8").split("\n")[0]
     
     if "sd" not in disk_file:
         kill("Can't find pico disk file")
    
     if subprocess.run([MOUNT_CMD, DEV_DIR + "/" + disk_file, MNT_DIR]).returncode != 0:
         kill("Can't mount disk on temp folder")
          
     if not os.access(UF2_FILE_PATH, os.R_OK):
         kill("UF2 File does not exist")
    
     if subprocess.run([CP_CMD, UF2_FILE_PATH, MNT_DIR]).returncode != 0:
         kill("Can't copy uf2 file to pico")

     if subprocess.run([SYNC_CMD]).returncode != 0:
         kill("Can't flash uf2 file to pico")

          
def main():
     # Flash UF2 on PICO
     flash()
     start()


if __name__ == "__main__":
    main()