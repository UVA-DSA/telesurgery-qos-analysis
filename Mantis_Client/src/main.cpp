/*****************************************************************************

SUI_HK

Surgical Robot Master control using PHANToM OMNI
Ganesh Sankaranarayanan
BioRobotics Laboratory
08/04/05
Modified by Kosy 10/24/05
Modified by Hawkeye 4/17/06
Modified by Ganesh 5/17/06

*******************************************************************************/
#include "stdafx.h" 
#include <HDU/hduQuaternion.h>
#include <HD/hd.h>

#include "MantisDuoControllerClass.h"
#include "../PracticalSocket/PracticalSocket.h"

#include "C:\Users\Mimic Technologies\Desktop\BRL_Master-master_for2010\SUI_win RII\VS_GUI_SERVER/CommonDS.h"
#include "ITPteleoperation.h"
#include "comm.h"
#include "coordinateSystems.h"

#define TIMEOUT_SECS 0
#define TIMEOUT_USECS 100

// Communication object for communication with SUI and Slave robot
Omni_Comm gComm;
extern int g_footpedal;
hduVector3Dd movechar = hduVector3Dd(0,0,0);

// device handle
extern MantisDuoControllerClass * g_Mantis;
extern bool enable_mantis_force;

// loop condition
bool g_bQuit = 0;
bool gohomenow = 0;
bool printnow = 0;
int kbd_arm2move = 2;

/*! InitializeDevice
Initializes and connects to MantisDuo workstation
*/
bool InitializeDevice();
void TerminateDevice();

/******************************************************************************
main function
Initialize the device, create a callback to handle sphere forces, terminate
upon key press.
******************************************************************************/
int main(int argc, char* argv[])
{
	char ch = 'r';
	int hstdin = (int) GetStdHandle(STD_INPUT_HANDLE);
	fd_set readSet;
	TIMEVAL timeout = {TIMEOUT_SECS, TIMEOUT_USECS};
	int nfound;
	int the_tcpsock;
	int the_udpsock;

	cout << "Starting networking with robot and S-GUI... " << endl;

	// initialize communication with the robot //
	gComm.Initialize_UDP_Robot(argc, argv); 
	while(!gComm.Initialize_TCP_GUI()) {
		cout << "TCPIP initialization failed retry in 5 sec." << endl;
		Sleep(5);
	}

	cout << "S-GUI ok, UDP ready.\n\nInitalizing haptic interface... ";

	//// Initialize Mantis
	g_Mantis = new MantisDuoControllerClass();
	if (!InitializeDevice()){
		cout << "Failed to init device.  Goodbye.\n";
		exit(-1);
	}

	cout << "Device ready.\n\nStarting application loop... ";

	// TODO: check return value of initialization

	// Initialize FD_SET //
	FD_ZERO(&readSet);
	the_tcpsock = gComm.tcpsocket->sockDesc;
	the_udpsock = gComm.udpsocket->sockDesc;
	FD_SET(the_tcpsock, &readSet);
	FD_SET(the_udpsock, &readSet);

	// TCP and UI receive loop //
	cout << "Pres 'q' to quit." << endl;

	while( !g_bQuit) {
		timeout.tv_sec = TIMEOUT_SECS;
		timeout.tv_usec = TIMEOUT_USECS;

		nfound = select( 1 , &readSet, NULL, NULL, &timeout );		// check the TCP Socket
		if ( nfound < 0 ) {						// Socket error
			cerr << "Socket error "<<nfound<<" : "<<WSAGetLastError()<<" \n";
			cout << "sockedesc:"<< gComm.tcpsocket->sockDesc<<endl;
		}
		else if ( nfound > 0 && FD_ISSET(the_tcpsock, &readSet)) {			// TCP socket ready to read
			//cout << "recv TCP...\n";
			gComm.Recv_TCP();
			gComm.Check_UI2MA(0);// 0 means not to dispay the message
		} 
		else if ( nfound > 0 && FD_ISSET(the_udpsock, &readSet)) {			// TCP socket ready to read
//			gComm.Recv_UDP_Packet();
		} 

		FD_CLR(the_tcpsock,&readSet);					// Reset fd_set
		FD_CLR(the_udpsock,&readSet);					// Reset fd_set
		FD_SET(the_tcpsock,&readSet);					//  ""
		FD_SET(the_udpsock,&readSet);					//  ""

		if( _kbhit() )							// check for keyboard input`
		{
			ch = _getch();
			switch(ch)
			{
				case 'q':
					g_bQuit = true;
					break;
				case 'g':
					cout << "go home now.\n";
					gohomenow = !gohomenow;
					break;
				case 'p':
					printnow = !printnow;
					break;
				case 'e':
					g_footpedal = true;
					cout << "pd _down\n";
					break;
				case 'd':
					g_footpedal = false;
					cout << "pd _up\n";
					break;
				case 'f':
					enable_mantis_force = !enable_mantis_force;
					cout << "Force enabled? " << enable_mantis_force << endl;
					break;
				case 'a':
				case 'A':
					kbd_arm2move = (kbd_arm2move == 2) ? 0 : kbd_arm2move+1;
					cout << "Moving " << kbd_arm2move << " arm\n";
				case 0x20:
					movechar.set(0,0,0);
					break;
				case 'x':
					movechar += hduVector3Dd( .01,0,0);
					break;
				case 'X':
					movechar += hduVector3Dd(-.01,0,0);
					break;
				case 'y':
					movechar += hduVector3Dd(0, 0.01,0);
					break;
				case 'Y':
					movechar += hduVector3Dd(0,-0.01,0);
					break;
				case 'z':
					movechar += hduVector3Dd(0,0, 0.01);
					break;
				case 'Z':
					movechar += hduVector3Dd(0,0,-0.01);
					break;

				case '0':
				case '1':
				case '2':
					gComm.send_command_to_vfr(ch);
				break;
			}
		}
	}

	cout << "Closing TCP... ";

	try {
		gComm.tcpsocket->cleanUp();
	} 
	catch (SocketException SE) {
		cerr<< "ERROR: Socket cleanUp failed.\n";
	}

	cout << "TCP closed.\n\nShutting down device...";

	// terminate connection with device
	TerminateDevice();

	cout << "Device termiated.\n\nShutting down application...  ";
	
	g_Mantis->~MantisDuoControllerClass();

	cout << "goodbye.\n";
	Sleep(500);

	return 0;
} // end: main




bool InitializeDevice()
{
	bool device_initialization_successful = g_Mantis->InitializeDevice(HapticsFunction, NULL);

	if ( !device_initialization_successful )
	{
		cout << "MantisDuo could not be initialized and connected. Exiting..." << endl;
		Sleep(3000);

		g_bQuit = true;
	}
	else
	{
		cout << "MantisDuo initialized and connected successfully." << endl;

		if ( g_Mantis->IsHapticsThreadOn() )
		{
			cout << "Haptics thread started." << endl;
		}
		else
		{
			device_initialization_successful = false;
			cout << "Haptics thread could not be started. Exiting..." << endl;
			Sleep(3000);

			g_bQuit = true;
		}
	}

	return device_initialization_successful;
}

void TerminateDevice()
{
	g_Mantis->TerminateDevice();
}
