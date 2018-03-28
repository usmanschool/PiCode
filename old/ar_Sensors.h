#include<SPI.h>
#include<RF24.h>
#include "printf.h"


const uint64_t pipes[2] = {0xF1F2F3F4C1LL,0xF1F2F3F4A1LL};

// ce, csn pins
RF24 radio(7,8);

void setup(void){
  radio.begin();
  
  radio.setPALevel(RF24_PA_MAX);
  radio.setChannel(0x76);
  radio.openWritingPipe(pipes[0]);
  radio.enableDynamicPayloads();
  radio.powerUp();
}

void loop(void){
  const char text[] = "Hello World!";
  radio.write(&text, sizeof(text));
  delay(2000);
}
