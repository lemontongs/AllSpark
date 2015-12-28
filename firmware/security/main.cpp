#include "application.h"


STARTUP(WiFi.selectAntenna(ANT_EXTERNAL));

//
// UDP stuff
//
void sendUDPmessage( String msg, int port = 5100 )
{
    IPAddress multicast( 225, 1, 1, 1 );
    UDP server;
    
    if ( server.begin( port ) )
    {
        server.beginPacket( multicast, port );
        server.write( msg );
        server.endPacket();
        
        server.stop();
    }
}

//
// TCP stuff
//
void sendToGraphite( String id, String value )
{
    TCPClient client;
    
    if ( client.connect( "rpi2", 2003 ) )
    {
        client.println( id + " " + value + " " + String( Time.now() ) );
        client.stop();
    }
}



// ********************************************************************************************
// MAIN
// ********************************************************************************************

const int NUM_ZONES = 8;

uint32_t new_zone_state = 0;
uint32_t old_zone_state = 0;
uint32_t shift = 0;


void setup()
{
    waitUntil(WiFi.ready);
    
    // Set the pin modes to INPUT_PULLDOWN and initialize the state
    shift = NUM_ZONES - 1;
    for ( pin_t pin = 0; pin < NUM_ZONES; pin++ )
    {
        pinMode( pin, INPUT_PULLDOWN );
        old_zone_state += ( digitalRead( pin ) << shift );
        shift--;
    }
    
    // D0 = zone_0 = Basement Door
    // D1 = zone_1 = Basement Window
    // D2 = zone_2 = Back Slider
    // D3 = zone_3 = Kitchen Door
    // D4 = zone_4 = Office Window
    // D5 = zone_5 = Front Door
    // D6 = zone_6 = Basement Motion
    // D7 = zone_7 = Livingroom Motion
}



void loop()
{
    // Read the pin states into the state array
    new_zone_state = 0;
    shift = NUM_ZONES - 1;
    for ( pin_t pin = 0; pin < NUM_ZONES; pin++ )
    {
        new_zone_state += ( digitalRead( pin ) << shift );
        shift--;
    }
    
    //
    // Check for a change in state, or send if 30 seconds has elapsed
    //
    bool send_signal = ( new_zone_state != old_zone_state );
    
    if ( millis() % 30000 == 0 )
    {
        send_signal = true;
        
        // ID message
        sendUDPmessage( System.deviceID() + ":" + String( WiFi.localIP() ) + ":security" );
        
        // Statistics
        sendToGraphite( "allspark.devices." + System.deviceID() + ".rssi ", String( WiFi.RSSI() ) );
    }
    
    //
    // Send the new state
    //
    if ( send_signal )
    {
        String msg = "0000000000" + String( new_zone_state, BIN );
        msg = msg.substring( msg.length() - NUM_ZONES, msg.length() );
        
        sendUDPmessage( msg, 5500 );
    }
    
    // Save the new state for comparison
    old_zone_state = new_zone_state;
}

