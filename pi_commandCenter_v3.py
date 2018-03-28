#code works with only python 3 and above......
#note we will be mapping python integers to Arduino Long variables 
#furthermore dont forget to specify little endian


import RPi.GPIO as GPIO
from lib_nrf24 import NRF24
from struct import *
import time
import spidev
import phue
import logging
import psycopg2 as p
import psycopg2.extras as e
import datetime 


#0xF1F2F3F4C1 is command center
#0xF1F2F3F4A1 is the sensor
pipes = [[0xF1, 0xF2, 0xF3, 0XF4, 0xC1], [0xF1, 0xF2, 0xF3, 0xF4, 0xA1]]

#List of zones and their objects....
ZoneList = []
targetZoneUpperBound = 20
targetZoneLowerBound = 10

#Postgres SQL Constants.
host = "ec2-54-83-23-91.compute-1.amazonaws.com"
database = "d6q2l2eqtqu66u"
port = "5432"
username = "wcakxmmlvfppvl"
password = "509b5b0fac09ca205c14a6ff6e9db2d820b0d74d7142bc7aefd7144b73d710b6"
userID = 3 #hardcoded for now. might wana read in from a settings file
connection = None
cursor = None


#constant commands
cmdRequesDataPackage = 100
cmdPowerDown = 105
cmdReset = 110


#hue Constants
HueIP = '192.168.0.100'
#HueSecurityKey = 'NIlVZOyFJ1kDfw+m1osb2h-xDOqg2yfCG6q5vDu3d'
HueSecurityKey = 'NIlVZOyFJ1kDfwm1osb2h-xDOqg2yfCG6q5vDu3d'


#global object list
radio = None
receivedData = None	
bridge = None


def main():
	
	#initialize all of the devices and objects required 
	setupAllDevices()
	
	#loop forever
	while True:
		for curZone in ZoneList:
			
			print("Currently checking the zone with zone name: " + curZone.ZoneName)

			overrideflag = 10000 #some arbitrary number
			overrideflag = checkOverRideFlag(curZone.ZoneId) #check flag.
		
			#if user is not trying to override the settings then lets try to set the settings. 
			if (overrideflag == 0):
				RequesetData(curZone)
				if(RequesetData):
					AdjustLight(curZone)
			elif (overrideflag == 1):
				#change brightness setting. 
				print ("override flag is set for the zone:" + curZone.ZoneName + ", setting light to user's desired value")
				ManuallyAdjustLight(curZone)
			else:
				print ("urrrgh we got some random value from over ride flag check for errors...")
			
			#wait a second between each zone checks...
			time.sleep(1)

	
#this function initializes all of our antennas and devices for operations. 		
def setupAllDevices():
	global radio, bridge, receivedData
	
	print("Initialization sequence activated...")
	
	#connect to the Postgres Database
	if(ConnectToSQLDB()):
		GPIO.setmode(GPIO.BCM)
		radio = NRF24(GPIO, spidev.SpiDev())
		radio.begin(0, 17)
		#allow a maximum of 32 bytes
		#notes that we are transmitting arrays of bytes
		radio.setPayloadSize(32)
		radio.setChannel(0x76)
		radio.setDataRate(NRF24.BR_1MBPS)
		radio.setPALevel(NRF24.PA_MAX)
		#radio.setAutoAck(True)
		radio.enableDynamicPayloads()
		radio.enableAckPayload()
		radio.openReadingPipe(1, pipes[0])
		radio.openWritingPipe(pipes[1])
		radio.printDetails()
		
		#initialize the incoming package object 
		receivedData = IncommingDataPackage(0,0,0)
		
		#initialize all zones from the database....
		InitializeZoneList(userID)

		#hue configuration
		logging.basicConfig()
		bridge = phue.Bridge(HueIP, HueSecurityKey)
		time.sleep (0.2)

		print("Successfully initialized all devices and objects...")
	else:
		print ("Initialization sequence failed")

	
def ConnectToSQLDB():
	global connection, cursor
	try:
		connection =  p.connect("dbname = 'd6q2l2eqtqu66u' user = 'wcakxmmlvfppvl' host = 'ec2-54-83-23-91.compute-1.amazonaws.com' password = '509b5b0fac09ca205c14a6ff6e9db2d820b0d74d7142bc7aefd7144b73d710b6' port = '5432'")
		
		cursor = connection.cursor(cursor_factory =e.DictCursor)
		return True
		
	except :
		print ("An error occurred while connecting to the database please contact support")
		return False 



		
def InitializeZoneList(uid):
	global ZoneList

	try:
		query = "select * from zonetable where uid = " + str(uid) + ";"
		cursor.execute(query)
		rows = cursor.fetchall()

		for row in rows:
			object = Zone(row["zoneid"],row["uid"],row["zonename"],row["bulbid"],row["brightnesssetting"],row["lightsensorid"])
			ZoneList.append(object)
	except:
		print ("Error initializing zone list... maybe database connection is down, try resetting the pi")

	

def checkOverRideFlag(zoneID):
	try:
		query = "select overrideflag from zonetable where zoneid = " + str(zoneID) + ";"
		cursor.execute(query)
		result = cursor.fetchone()
		return (result[0])
	
	except:
		print ("Error checking override flag... maybe database connection is down, try resetting the pi")
		return 9000


def ManuallyAdjustLight(curZone):
	#get the desired lighting level from the server
	value = getBrightnessSetting(curZone.ZoneId)
	#set the value of the zone.
	setLightBrightness(curZone,value)
	
	

#get value of brightness from db
def getBrightnessSetting(zoneID):
	try:
		query = "select brightnesssetting from zonetable where zoneid = " + str(zoneID) + ";"
		cursor.execute(query)
		result = cursor.fetchone()
		return (result[0])
	
	except:
		print ("An error occured while trying to read the brightness setting from the zone table")
		return 9000

		
#set value of brightness variable in db 
def updateBrirghtnessSetting(zoneID,brightnessSettingVal):
	try:
		query = "update zonetable set brightnesssetting = " + str(brightnessSettingVal) + " where zoneid = " + str(zoneID) + ";"
		cursor.execute(query)
		connection.commit()
	except:
		print ("An error occured while saving the brightness setting back to the server")

		
def checkEnergySavingMode(zoneID):
	try:
		query = "select energysavingmode from zonetable where zoneid = " + str(zoneID) + ";"
		cursor.execute(query)
		result = cursor.fetchone()
		return (result[0])
	
	except:
		print ("Error checking energysavingmode flag... maybe database connection is down, try resetting the pi")
		return 9000

		
		
def checkUserBrightnessModifier(zoneID):
	try:
		query = "select desiredbrightness from zonetable where zoneid = " + str(zoneID) + ";"
		cursor.execute(query)
		result = cursor.fetchone()
		return (result[0])
	
	except:
		print ("Error checking brightness modifier flag... maybe database connection is down, try resetting the pi")
		return 9000
		
		
#light adjustment logic... 
def AdjustLight(curZone):
	

	onPeakModifier = 0.75
	offPeakModifier = 1
	midPeakModifier = 0.85
	energySavingModeOn = checkEnergySavingMode (curZone.ZoneId)
	currentValueOfZone = getBrightnessSetting (curZone.ZoneId) #lets get the current zone value 
	
	currentValueOfBulbs = bridge.get_light(int(curZone.bulbList(0)),'bri')
	
	#bridge.set_light(int(bulb),'on', False)

	
	
	
	

	if (energySavingModeOn == 9000):
		print ("an error occured getting the energy saving mode and the user control modifier from the server")
		return 
		
	#if the user wana check the 
	if (energySavingModeOn == 1):
		
		print ("Energy saving option is on....")

		now = datetime.datetime.now()
		now_time = now.time()

		if (now_time >= datetime.time(7,00) and now_time <= datetime.time(10,59)) or (now_time >= datetime.time(17,00) and now_time <= datetime.time(18,59)):        
			smartGridModifier = onPeakModifier
			print ("yikes! we are currently in on peak hours!")

		elif now_time >= datetime.time(11,00) and now_time <= datetime.time(16,59): 
			smartGridModifier = midPeakModifier
			print ("meh! we are currently in mid peak hours!")
		
		elif (now_time >= datetime.time(19,00) and now_time <= datetime.time(23,59)) or (now_time >= datetime.time(0,00) and now_time <= datetime.time(6,59)):
			smartGridModifier = offPeakModifier
			print ("yay! we are currently in off peak hours!")

		else:
			smartGridModifier = 1
			print ("error getting date time for some reason fell into this condition, must be a logic error somewhere")
		
		#this comes out to some value....that we are trying to reach. 
		targetVal = targetZoneLowerBound * smartGridModifier
#-----------------------------------------------------------------------------------------------
	#print ("attempting to adjust value of bulb to a target value of " + str(targetVal))
	print ("at first zone was at " + str(currentValueOfZone))

	while(not withinRange(receivedData.LightSensorValue,targetZoneLowerBound,targetZoneUpperBound)):
		print("entered Loop")
		if (receivedData.LightSensorValue < targetZoneLowerBound):
			if(currentValueOfBulbs < 240):
				currentValueOfBulbs = currentValueOfBulbs + 15
			else:
				print ("already at max unable to up the bulb anymore")
				break
				
		
		elif (receivedData.LightSensorValue > targetZoneUpperBound):
			if(currentValueOfBulbs > 0):
				currentValueOfBulbs = currentValueOfBulbs - 15
			else:
				print("Cant go much lower")
				break
		

		#makes sure we stay within our limits 
		if currentValueOfBulbs > 255:
			currentValueOfBulbs == 255
		
		if currentValueOfBulbs < 0:
			currentValueOfBulbs = 0

		setLightBrightness(curZone,currentValueOfZone)
		time.sleep(0.1)
		
		#lets recheck the value of the sensor. 
		RequesetData(curZone)
		
		#lets give arduino a chance to collect data and transmit it. 
		time.sleep(0.1)
	
#-------------------------------------------------------------------------------------------------------------------------

	 
def setLightBrightness(curZone,value):
	
	print ("attempting to set value of bulb to value")
	mybulbList = curZone.bulbList.split(",")
	for bulb in mybulbList:
		if (value < 1):
			bridge.set_light(int(bulb),'on', False)
		
		elif (value >= 1):
			
			#check if light is off. if it is tturn it on.
		
			bridge.set_light(int(bulb),'on', True)
			
			#set the brightness. 
			bridge.set_light(int(bulb),'bri', int(value))	
		time.sleep (0.2)
	
	updateBrirghtnessSetting(curZone.ZoneId,value)

	
	
	
	
	
	
	
def GetUserID():
	return True 
	
	
def RequesetData(curZone):
	#stop listening so we can talk
	radio.stopListening()
	#might not need the little endian thing
	commandPackage = pack('<ii',curZone.LightSensorID,cmdRequesDataPackage)
	radio.write(commandPackage)
	print ("Requested Data from: " + str(curZone.LightSensorID))
	
	#start listening for the response
	radio.startListening()
	
	#define the timeout variable for now we set the timeout to be 1 second
	timeout = time.time() + 1   
	timedOut = False
	#wait for the timeout
	while not radio.available():
		if time.time() > timeout:
			timedOut = True
			break
	
	if timedOut:
		print ("timed out no response received")
		#move to the next device
		#continue
		return False
	
	#if we dont get timed out then ul reach this point else you wont
	
	rawSensorData = []
	radio.read(rawSensorData, radio.getDynamicPayloadSize())
	
	
	#map the raw data to the correct variables
	#overwrite the received Data Object's parameters	
	receivedData.SensorID = int.from_bytes(rawSensorData[0:3],byteorder='little', signed=False)
	receivedData.LightSensorValue = int.from_bytes(rawSensorData[4:7],byteorder='little', signed=False)
	receivedData.BatteryValue = int.from_bytes(rawSensorData[8:11],byteorder='little', signed=False)	
	
	#print ("the length of the data array is: " + str(len(rawSensorData)))
	#print ("the Sensor ID is: " + str(receivedData.SensorID))
	print ("the Light Sensor value is: " + str(receivedData.LightSensorValue))
	#print ("the Battery level is: " + str(receivedData.BatteryValue))
	return True
	
	
	

	
def withinRange(numberInput,lowerbound,upperbound):
	if(numberInput >= lowerbound and numberInput <= upperbound):
		return True
	else:
		return False
	
	
#class definitions below:	
#just to package up the incoming data to keep things nice and clean. 
class IncommingDataPackage:
	def __init__(self, SensorID,LightSensorValue,BatteryValue):
		self.SensorID = SensorID
		self.LightSensorValue = LightSensorValue
		self.BatteryValue = BatteryValue


		
		#zone objects... hard code for now ...later initialize to a list read in from a JSON file 
class Zone:
	def __init__(self,ZoneId,Uid,ZoneName,bulbList,Brightnesssetting,LightSensorID):
	
		self.ZoneId = ZoneId
		self.Uid = Uid
		self.ZoneName = ZoneName
		self.bulbList = bulbList
		self.Brightnesssetting = Brightnesssetting
		self.LightSensorID = LightSensorID
		


		
#entry point for the code 		
if __name__ == '__main__':
	main()
