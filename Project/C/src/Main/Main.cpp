#include <stdio.h>
#include "pico/stdlib.h"
#include "pico/multicore.h"
#include "hardware/dma.h"
#include "hardware/spi.h"
#include "hardware/clocks.h"
#include "ArduCAM.h"
#include "hardware/irq.h"
#include "ov2640_regs.h"
#include <cstdlib>
#include "stdio.h"
#include "bsp/board.h"
#include "tusb.h"
#include "pico/mutex.h"
#include <string>


static mutex_t usb_mutex;
void convertCharToUInt8(const char* str, int sizeOfStr, uint8_t* res);
void SerialUsb(uint8_t* buffer,uint32_t lenght);
void captureAndSendImage(void);
double absDifference(double newAverageDistance, double distance);
void trigger(void);
int SerialUSBAvailable(void);
int SerialUsbRead(void);
uint8_t read_fifo_burst(ArduCAM myCAM);
#define BMPIMAGEOFFSET 66
uint8_t bmp_header[BMPIMAGEOFFSET] =
{
  0x42, 0x4D, 0x36, 0x58, 0x02, 0x00, 0x00, 0x00, 0x00, 0x00, 0x42, 0x00, 0x00, 0x00, 0x28, 0x00,
  0x00, 0x00, 0x40, 0x01, 0x00, 0x00, 0xF0, 0x00, 0x00, 0x00, 0x01, 0x00, 0x10, 0x00, 0x03, 0x00,
  0x00, 0x00, 0x00, 0x58, 0x02, 0x00, 0xC4, 0x0E, 0x00, 0x00, 0xC4, 0x0E, 0x00, 0x00, 0x00, 0x00,
  0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xF8, 0x00, 0x00, 0xE0, 0x07, 0x00, 0x00, 0x1F, 0x00,
  0x00, 0x00
};

// set pin 10 as the slave select for the digital pot:
const uint8_t CS = 5;
bool is_header = false;
const uint8_t TRIGGER_PIN = 16;
const uint8_t ECHO_PIN = 15;
int mode = 0;
uint8_t start_capture = 0;
uint64_t start = 0;
uint64_t elapsedTime = 0;
double distance = 0;
double inst_distance = 0;
double newAverageDistance = 0;
const char done[] = "done";
const char askToTakeImage[] = "Should take image?";
uint8_t* askToTakeImageBuff = (uint8_t*) malloc(18*sizeof(uint8_t));
uint8_t * doneBuff = (uint8_t*) malloc(4*sizeof(uint8_t));
ArduCAM myCAM( OV2640, CS );

int response  = -1;

int main() 
{
  int value=0;
  convertCharToUInt8(done, 4, doneBuff);
  convertCharToUInt8(askToTakeImage, 18, askToTakeImageBuff);
  uint8_t vid, pid;
  uint8_t cameraCommand;
  stdio_init_all();
  tusb_init();
	// put your setup code here, to run once:
  myCAM.Arducam_init();	
  gpio_init(CS);
  gpio_set_dir(CS, GPIO_OUT);
  gpio_put(CS, 1);

  gpio_init(25);
  gpio_set_dir(25, GPIO_OUT);

  gpio_init(TRIGGER_PIN);
  gpio_set_dir(TRIGGER_PIN, GPIO_OUT);
  

  gpio_init(ECHO_PIN);
  gpio_set_dir(ECHO_PIN, GPIO_IN);
  gpio_pull_down(ECHO_PIN);

    //Reset the CPLD
  myCAM.write_reg(0x07, 0x80);
  sleep_ms(100);
  myCAM.write_reg(0x07, 0x00);
  sleep_ms(100);
  while (1) {
 			//Check if the ArduCAM SPI bus is OK
 			myCAM.write_reg(ARDUCHIP_TEST1, 0x55);
 			cameraCommand = myCAM.read_reg(ARDUCHIP_TEST1);
 			if (cameraCommand != 0x55) {
 				//printf(" SPI interface Error!");
         		gpio_put(25, 1);
         		sleep_ms(1000);
         		gpio_put(25, 0);
 				sleep_ms(5000); continue;
 			} 
 			else {
 				//printf("ACK CMD SPI interface OK.END"); 
         		break;
 			}
 	}
  
 	while (1) {
 		//Check if the camera module type is OV2640
 		myCAM.wrSensorReg8_8(0xff, 0x01);
 		myCAM.rdSensorReg8_8(OV2640_CHIPID_HIGH, &vid);
 		myCAM.rdSensorReg8_8(OV2640_CHIPID_LOW, &pid);
 		if ((vid != 0x26 ) && (( pid != 0x41 ) || ( pid != 0x42 ))) {
 			//printf("Can't find OV2640 module!");
       		gpio_put(25, 1);
       		sleep_ms(1000);
       		gpio_put(25, 0);
       		sleep_ms(1000);
       		gpio_put(25, 1);
       		sleep_ms(1000);
       		gpio_put(25, 0);
    			sleep_ms(5000); continue;
 		}
 		else {
 			//printf("OV2640 detected.END"); 
       		break;
 		}
   }

//   sleep_ms(10000);

	 //Change to JPEG capture mode and initialize the OV5642 module
   myCAM.set_format(JPEG);
   myCAM.InitCAM();
   myCAM.OV2640_set_JPEG_size(OV2640_320x240);
   sleep_ms(1000);
   myCAM.clear_fifo_flag();

  uint8_t cameraCommand_last = 0;
  uint8_t is_header = 0;

  // Initialize sensor thread
  multicore_launch_core1(trigger);

  while (1){
    while (!gpio_get(ECHO_PIN)) {
      continue;
    }

    start = time_us_64();

    while (gpio_get(ECHO_PIN)) {
      continue;
    }

    elapsedTime = time_us_64() - start;

    inst_distance = ((double) elapsedTime/1000000)*343/2;
    std::string s = std::to_string(inst_distance);
    uint8_t* messageBuff = (uint8_t*) malloc(7*sizeof(uint8_t));
    convertCharToUInt8(s.c_str(),s.size(), messageBuff); 
    SerialUsb(messageBuff, s.size());
    free(messageBuff);
    continue;


    if (distance == 0) {
      distance = inst_distance;
    }

    newAverageDistance = distance*0.70 + inst_distance*0.30;
    
	//sleep_ms(100);

    if (((((double) absDifference(newAverageDistance, distance))/distance)*100.0) > 50.0) {
    	//printf("Average distance: %f\n", newAverageDistance);
    	//uint8_t * doneBuff = (uint8_t*) malloc(4*sizeof(uint8_t));
		//const char * done = "Hiii";
		//convertCharToUInt8(done, 4, doneBuff);
		//SerialUsb(doneBuff, 4);
		//free(doneBuff);
		//sleep_ms(500);
      gpio_put(25, 1);
      sleep_ms(5000);
      gpio_put(25, 0);  
      distance = newAverageDistance;
      continue;  
   		SerialUsb(askToTakeImageBuff, 18);
   		
   		while ((response = SerialUsbRead()) == -1) {
   		
   		}
   		
		  // 'q' = quit
 		  if (response == 113)
		  {
		
			  multicore_fifo_push_blocking(1);
			  break;
			
		  }
		
		  // 'c' = capture
		  else if (response == 99)
		  {
		
			  multicore_fifo_push_blocking(2);
			  captureAndSendImage();
			  multicore_fifo_push_blocking(3);
		
		  }
		
		  // i = ignore
		  else if (response == 105)
		  {
		
			  // do nothing 
		
		  }
      	
      sleep_ms(5000);
      gpio_put(25, 0);    
    }

    distance = newAverageDistance;
    
  }

  return 0;
  
}

double absDifference(double newAverageDistance, double distance)
{
  if (newAverageDistance > distance)
  {
    return newAverageDistance - distance;
  }

  return distance - newAverageDistance;
}

void trigger()
{
  while(1) {
    gpio_put(TRIGGER_PIN, 1);
    sleep_us(10);
    gpio_put(TRIGGER_PIN, 0);
  }
  uint32_t dataSentByCore1 = 0;
  //gpio_put(25,1);
  while (1) {
    gpio_put(TRIGGER_PIN, 0);
    if (multicore_fifo_pop_timeout_us(50, &dataSentByCore1))
    {
    	// Quit thread
    	if (dataSentByCore1 == 1)
    	{
    		break;	
    	}
    	
    	// Pause
    	if (dataSentByCore1 == 2)
    	{	
    		if (multicore_fifo_pop_blocking() == 3)
    		{
    			continue;
    		}
   
    	}
    }
     
    gpio_put(TRIGGER_PIN, 1);
	if (multicore_fifo_pop_timeout_us(100, &dataSentByCore1))
    {	
    	gpio_put(TRIGGER_PIN, 0);
    	// Quit thread
    	if (dataSentByCore1 == 1)
    		break;	
    	}
    	
    	// Pause thread
    	if (dataSentByCore1 == 2)
    	{	
    		if (multicore_fifo_pop_blocking() == 3)
    		{
    			continue;
    		}
   
    	}
    }
  }


void captureAndSendImage()
{
   myCAM.flush_fifo();
   myCAM.clear_fifo_flag();
   //Start capture
   myCAM.start_capture();
   start_capture = 0;
  
   while (myCAM.get_bit(ARDUCHIP_TRIG, CAP_DONE_MASK) == (uint8_t) 0)
   {
   
   }
      
   //printf("ACK CMD CAM Capture Done. END");
   read_fifo_burst(myCAM);
   //Clear the capture done flag
   myCAM.clear_fifo_flag();
      
   SerialUsb(doneBuff, 4);
   
}

void convertCharToUInt8(const char* str, int sizeOfStr, uint8_t* res)
{
  for (int i = 0; i < sizeOfStr; i++)
  {
    res[i] = (uint8_t) str[i];
  }

}

uint8_t read_fifo_burst(ArduCAM myCAM)
{
   int i , count;
   int length = myCAM.read_fifo_length();
   uint8_t * imageBuf =(uint8_t *) malloc(length*sizeof(uint8_t));
   gpio_put(25, 1);  
   i = 0 ;
   myCAM.CS_LOW();
   myCAM.set_fifo_burst();//Set fifo burst mode
   spi_read_blocking(SPI_PORT, BURST_FIFO_READ,imageBuf, length);
   myCAM.CS_HIGH();
   SerialUsb(imageBuf, length);
   free(imageBuf);
  return 1;
}


void SerialUsb(uint8_t* buf,uint32_t length)
{
    static uint64_t last_avail_time;
    int i = 0;
    if (tud_cdc_connected()) 
    {
        for (int i = 0; i < length;) 
        {
            int n = length - i;
            int avail = tud_cdc_write_available();
            if (n > avail) n = avail;
            if (n) 
            {
                int n2 = tud_cdc_write(buf + i, n);
                tud_task();
                tud_cdc_write_flush();
                i += n2;
                last_avail_time = time_us_64();
            } 
            else 
            {
                tud_task();
                tud_cdc_write_flush();
                if (!tud_cdc_connected() ||
                    (!tud_cdc_write_available() && time_us_64() > last_avail_time + 1000000 /* 1 second */)) {
                    break;
                }
            }
        }
    } 
    else 
    {
        // reset our timeout
        last_avail_time = 0;
    }
}

int SerialUSBAvailable(void)
{
  return tud_cdc_available();
} 

int SerialUsbRead(void) 
{
  if (tud_cdc_connected() && tud_cdc_available()) 
  {
    return tud_cdc_read_char();
  }
  return -1;
}
