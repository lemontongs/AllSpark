#include "application.h"

#include "ds18x20/ds18x20.h"
#include "ds18x20/onewire.h"


char temperature[64];
char error[64];

uint8_t sensors[80];

//
// UDP stuff
//
void sendUDPmessage( String msg )
{
    IPAddress multicast( 225, 1, 1, 1 );
    UDP server;
    
    if ( server.begin( 5100 ) )
    {
        server.beginPacket( multicast, 5100 );
        server.write( msg );
        server.endPacket();
        
        server.stop();
    }
}


//
// TCP stuff
//
TCPClient client;

void sendToGraphite( String id, String value )
{
    if ( client.connect( "rpi2", 2003 ) )
    {
        client.println( id + " " + value + " " + String( Time.now() ) );
    }
}


bool getTemperature( double& tempFarenhight )
{   
    DS18X20_start_meas( DS18X20_POWER_PARASITE, NULL ); //Asks all DS18x20 devices to start temperature measurement, takes up to 750ms at max resolution
    delay(1000);                                        //If your code has other tasks, you can store the timestamp instead and return when a second has passed.
    
    uint8_t numsensors = ow_search_sensors(10, sensors);
    
    if ( numsensors > 0 )
    {
        uint8_t subzero, cel, cel_frac_bits;
        
        if ( DS18X20_read_meas( &sensors[0], &subzero, &cel, &cel_frac_bits) == DS18X20_OK )
        {
			int frac = cel_frac_bits * DS18X20_FRACCONV;
			
			double tempC = double( cel ) + ( double( frac ) / 10000.0 );
			
			double tempF = ( tempC * 1.8 ) + 32.0;
			
			if ( subzero )
			    tempFarenhight = tempF * -1;
			else
			    tempFarenhight = tempF;
			
			return true;
	    }
    }
    
    return false;
}




// ****************************************************************************************
// MAIN
// ****************************************************************************************

void setup()
{
    ow_setPin(D4);
    
    Spark.variable("temperature", temperature, STRING);
    
    String myID = Spark.deviceID();
    if (0 == myID.compareTo(String("53ff6c066667574852542467")))  // basement_floor_temp
    {
        RGB.control(true);
        RGB.color(50, 0, 0); // Change the LED color
        RGB.brightness(50);  // and brightness
    }
}
 
void loop()
{
    double tempF;
    
    if ( getTemperature( tempF ) )
    {
//        String myID = Spark.deviceID();
//        if      (0 == myID.compareTo(String("53ff6c066667574832552467")))  // top_floor_temp
//        {
//            tempF += -6.2;
//        }
//        else if (0 == myID.compareTo(String("53ff6f066667574845371267")))  // main_floor_temp
//        {
//            tempF += -5.7;
//        }
//        else if (0 == myID.compareTo(String("53ff6c066667574852542467")))  // basement_floor_temp
//        {
//            tempF += -5.1;
//        }
        
        sprintf( temperature, "%3.3f", tempF );
    }
    
    delay(10000);
    
    // ID message
    sendUDPmessage( System.deviceID() + ":" + String( WiFi.localIP() ) + ":temperature_source" );
    
    // Statistics
    int rssi = WiFi.RSSI();
    if ( rssi < 1 )
    {
        sendToGraphite( "allspark.devices." + System.deviceID() + ".rssi", String( rssi ) );
    }
}





