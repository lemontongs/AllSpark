#include "application.h"

STARTUP(WiFi.selectAntenna(ANT_EXTERNAL));


int last_heartbeat_request;

IPAddress discovery_address( 225, 1, 1, 1 );
int discovery_port = 5100;

IPAddress control_address( 225, 1, 1, 2 );
int control_rx_port = 5300;
int control_tx_port = 5400;


//
// UDP stuff
//
void sendUDPmessage( IPAddress addr, int port, String msg )
{
    UDP server;
    if ( server.begin( port ) )
    {
        server.beginPacket( addr, port );
        server.write( msg );
        server.endPacket();
        server.stop();
    }
}


UDP udp;
void processUDPmessage()
{
    int size = udp.parsePacket();
    
    if ( size == 2 )
    {
        // Read message
        String pin = String::format("%c", udp.read() );
        int enable = String::format("%c", udp.read() ).equals("1") ? HIGH : LOW;
        
        if ( pin.equals("3") )
            digitalWrite(D3, enable);
        if ( pin.equals("4") )
            digitalWrite(D4, enable);
        if ( pin.equals("5") )
            digitalWrite(D5, enable);
        if ( pin.equals("6") )
            digitalWrite(D6, enable);
        if ( pin.equals("0") )          // Pin 0 is actually a heartbeat request
        {
            last_heartbeat_request = Time.now();
            sendUDPmessage( control_address, control_tx_port, "OK" );
        }
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

void setup()
{
    pinMode( D3, OUTPUT );
    pinMode( D4, OUTPUT );
    pinMode( D5, OUTPUT );
    pinMode( D6, OUTPUT );
    
    waitUntil(WiFi.ready);
    
    udp.begin( control_rx_port );
    udp.joinMulticast( control_address );
    
    last_heartbeat_request = Time.now();
}

void loop()
{
    //
    // Process commands
    //
    processUDPmessage();
    
    //
    // If 30 seconds has elapsed, send statistics
    //
    if ( millis() % 30000 == 0 )
    {
        // ID message
        sendUDPmessage( discovery_address, 
                        discovery_port, 
                        System.deviceID() + ":" + String( WiFi.localIP() ) + ":furnace_control" );
        
        // Statistics
        sendToGraphite( "allspark.devices." + System.deviceID() + ".rssi ", String( WiFi.RSSI() ) );
        
        // Just for good measure
        udp.stop();
        udp.begin( control_rx_port );
        udp.joinMulticast( control_address );
    }
    
    //
    // If we havent received a heartbeat in a while, reset
    //
    if ( ( Time.now() - last_heartbeat_request ) > 300 )
    {
        sendUDPmessage( control_address, control_tx_port, "RESET" );
        System.reset();
    }
}
















