#include<SPI.h>
#include<RF24.h>
#include "printf.h"

// define my default device id.
#define myDeviceID 1002
#define tempSensorValue 900 
#define tempBatteryValue 10


const uint64_t pipes[2] = {0xF1F2F3F4C1LL,0xF1F2F3F4A1LL};

// ce, csn pins
RF24 radio(7,8);

// define the payload structs
// might need to change to long. 
struct CmdCenterPayload {
  long targetID;
  long Command;
};


struct SensorPayload {
  long senderID;
  long lightSensorValue;
  long batteryValue;
};



CmdCenterPayload receivedCommand;
SensorPayload sensorData;

void setup(void){
  
  Serial.begin(115200);
  radio.begin();
  printf_begin();
  radio.setPALevel(RF24_PA_MAX);
  radio.setChannel(0x76);
  radio.openWritingPipe(pipes[0]);
  radio.openReadingPipe(1,pipes[1]);


  radio.enableDynamicPayloads() ;
  radio.enableDynamicAck();
  
  radio.powerUp();
  radio.startListening();
  
}

int counter;
 // loop
void loop() {
 
 
  if(radio.available()){ 
    radio.read( &receivedCommand, sizeof(receivedCommand));             
    
    // lets print out what we just got 
    Serial.print("received Command was to the Sensor: ");
    Serial.print(receivedCommand.targetID);
    Serial.print(": Command = ");
    Serial.println(receivedCommand.Command);
    
  // if we are the one who is the target
    if(receivedCommand.targetID == myDeviceID)
    {

  
      // Gather the data (light sensor code)
      
      
      // Construct the data package
      sensorData.senderID = myDeviceID;
      sensorData.lightSensorValue = tempSensorValue;
      sensorData.batteryValue = tempBatteryValue;
      
      // prepare to xmit the data and xmit it then switch to listening again  
      radio.stopListening();
      radio.write( &sensorData, sizeof(sensorData) );            
      Serial.print("Transmitting Light Value of:");
      Serial.println(tempSensorValue);
      Serial.print("Transmitting Light Value of:"); 
      Serial.println(tempBatteryValue);
      radio.startListening();                                      

    }
    

    // when the size of the bufffer is not cleared (we dont read properly we gota use this to clear the buffer manually from the nrf sensors
   //radio.flush_rx();

   }
}
