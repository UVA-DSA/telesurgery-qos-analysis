/*****************************************************************************

omni_comm.h/omni_comm.cpp

These files declare and define objects for communicating with the 
robot slave and the Surgical User Interface.

Class created by KoSy
Modified by Hawkeye

*****************************************************************************/

#define _CRT_SECURE_NO_WARNINGS 1
#include "stdafx.h"
#include <iostream>
#include <assert.h>
#include <fcntl.h>

#include <cstdio>
#include <cassert>
#include <conio.h>
#include <stdio.h>
#include <math.h>
#include <stdlib.h>
#include <time.h>


#include <HDU/hduVector.h>
#include <HDU/hduError.h>

#include "../PracticalSocket/PracticalSocket.h"
#include "C:\Users\Mimic Technologies\Desktop\BRL_Master-master_for2010\SUI_win RII\VS_GUI_SERVER/CommonDS.h"
#include "ITPteleoperation.h"
#include "coordinateSystems.h"

#include "comm.h"

#define FALSE 0
#define TRUE 1
#define OMNI1 0
#define OMNI2 1
#define TIMEOUT_SECS 0
#define TIMEOUT_USECS 100

#define THOUSAND 1000
#define MILLION  (THOUSAND*THOUSAND)
#define round(x) (x)

/*Identifier for two Omni device -- Name it wisely as you wish */
#define MANTIS

#define ADDR_BUBBLES   "172.28.39.158"//158"
#define ADDR_BUTTERCUP "172.28.39.158"//158"

extern unsigned short c_port_UI;
extern const char* c_addr_UI;

// Three camera rotation angles
extern double th1, th2, th3;
extern int useITP;

//Global variable for world coordinate scale uniform in all 3 axis.
extern double scalingFactor;

///////////////////////////////////////////////////////////////////
// Implementation 
///////////////////////////////////////////////////////////////////
Omni_Comm::Omni_Comm()
{
	//addr_Robot = ADDR_BUBBLES;
	strcpy(addr_Robot, ADDR_BUBBLES);
	port_Robot = 36000;
	iUDPaddr=0;
}


Omni_Comm::~Omni_Comm()
{
}


void Omni_Comm::Set_Flag(int value, int mode)
{
	if(value == TRUE)
		pUI2Madata.flag01 |= mode;
	else if(value == FALSE)
		pUI2Madata.flag01 &= (ALL_ONES - mode);
}


bool Omni_Comm::Check_Flag(int mode)
{
	return pUI2Madata.flag01&mode ? TRUE : FALSE;
}


int Omni_Comm::Update_MA2UI(hduVector3Dd pos[2],int rl, unsigned int servo)
{
	pMa2UIdata.delx[0] = int(round(pos[OMNI1][0]*THOUSAND));
	pMa2UIdata.dely[0] = int(round(pos[OMNI1][1]*THOUSAND));
	pMa2UIdata.delz[0] = int(round(pos[OMNI1][2]*THOUSAND));
	pMa2UIdata.delx[1] = int(round(pos[OMNI2][0]*THOUSAND));
	pMa2UIdata.dely[1] = int(round(pos[OMNI2][1]*THOUSAND));
	pMa2UIdata.delz[1] = int(round(pos[OMNI2][2]*THOUSAND));
	pMa2UIdata.tick = servo; 
	pMa2UIdata.runlevel = rl;
	pMa2UIdata.checksum = pMa2UIdata.delx[0] +  pMa2UIdata.dely[0] +  pMa2UIdata.delz[0] +  pMa2UIdata.runlevel + (int)pMa2UIdata.tick;   

	return 1;
}


int Omni_Comm::Check_UI2MA(int message)
{
	if(pUI2Madata.checksum == (pUI2Madata.scale + pUI2Madata.flag01 + pUI2Madata.UDPaddr+ (int)pUI2Madata.tick))
	{ 
		// Set scale factor
		if (scalingFactor != (double)pUI2Madata.scale/100.0){
			scalingFactor = (double)pUI2Madata.scale/100.0;
			cout << "Scale changed to "<< scalingFactor << ".\n";
		}

		// Set camera angle 1
		if (th1 != pUI2Madata.camAngle[0]){
			th1 = pUI2Madata.camAngle[0];
			cout << "Camera angle 1 changed to "<< th1 <<" degrees.\n";
		}
		// Set camera angle 2
		if (th2 != pUI2Madata.camAngle[1]){
			th2 = pUI2Madata.camAngle[1];
			cout << "Camera angle 2 changed to "<< th2 <<" degrees.\n";
		}
		// Set camera angle 3
		if (th3 != pUI2Madata.camAngle[2]){
			th3 = pUI2Madata.camAngle[2];
			cout << "Camera angle 3 changed to "<< th3 <<" degrees.\n";
		}
		if (useITP != pUI2Madata.useITP) {
			useITP = pUI2Madata.useITP;
			if (useITP)
				cout << "Using ITP coordinate reference.\n";
			else
				cout << "Using native coordinate reference.\n";
		}

		// Robot's IP address Update
		if(iUDPaddr!=pUI2Madata.UDPaddr) {
			iUDPaddr = pUI2Madata.UDPaddr;
			sprintf(addr_Robot,"%d.%d.%d.%d",(unsigned int)((iUDPaddr&0xff000000)>>24),(unsigned int)((iUDPaddr&0xff0000)>>16), (unsigned int)((iUDPaddr&0xff00)>>8),(iUDPaddr&0x00ff));
			cout << "Surgical Robot's IP is chaged into " << addr_Robot <<endl;
		}
		if(message) {
			//	cout << "Communication with S-GUI is ok" << endl;
		}
		return TRUE;
	} else {
		pUI2Madata.flag01 &= (ALL_ONES - FPEDAL_RIGHT);
		cout << " Data is strange !!" << endl;
		return FALSE;
	}
}


int Omni_Comm::Initialize_TCP_GUI()
{
	Sleep(1);
	tcpsocket = new TCPSocket;

	try {
		tcpsocket->connect(c_addr_UI, c_port_UI);
	}
	catch( SocketException SE ) {
		cout << "Failed to connect TCP server.\n";
		return FALSE;
	}

	udpsocket = new UDPSocket(UDP_RECV_PORT);

	hduVector3Dd zero_pos[2];
	Update_MA2UI(zero_pos, 0, 0);
	Send_TCP();
	Recv_TCP();

	return (Check_UI2MA(1) ? TRUE : FALSE);
}


void Omni_Comm::Send_TCP()
{
	try{
		tcpsocket->send(&pMa2UIdata, sizeof(pMa2UIdata));
	}
	catch (SocketException SE){
		cerr << "failed to send_tcp\n";
	}
}


void Omni_Comm::Recv_TCP()
{
	try {
		tcpsocket->recv(&pUI2Madata, sizeof(pUI2Madata));
	}
	catch (SocketException SE){
		cerr << "failed to recv_tcp\n";
	}
}

int Omni_Comm::Initialize_UDP_Robot(int argc, char*argv[])
{
	strcpy(addr_Robot,ADDR_BUTTERCUP);
	cout << "Robot default IP : " << addr_Robot << endl;
	cout << "Default scaling  : " << scalingFactor << endl;

	return 1;
}


void Omni_Comm::Send_UDP()
{
	if(Check_Flag(BASIC_START)) {
		try {
			udpsocket->sendTo(&msgHeader,sizeof(u_struct),addr_Robot,port_Robot);
			//cout<<msgHeader<<endl;
		}
		catch (SocketException SE){
			cerr << "failed to send_UDP\n";
		}
	}
}
void Omni_Comm::send_command_to_vfr(char in_cmd)
{
	char *vfr_addr = "128.95.30.197";
	int vfr_port = 36001;
	struct 
	{
		char cmd;
	} vfr_cmd = {in_cmd};


	if(Check_Flag(BASIC_START)) {
		try {
			cout << "send vfr" << in_cmd <<"\n";
			udpsocket->sendTo((void*)&in_cmd, 1, vfr_addr, vfr_port);
		}
		catch (SocketException SE){
			cerr << "failed to send_UDP\n";
		}
	}
}

void Omni_Comm::Update_UDP_Data(hduVector3Dd pos[2], double orientation[2][3], int bttn[2], int fp, unsigned int servo, hduMatrix xfs[2])
{

	static int i;
	msgHeader.delx[0]		= int(round(pos[OMNI1][0]*THOUSAND));
	msgHeader.dely[0]		= int(round(pos[OMNI1][1]*THOUSAND));
	msgHeader.delz[0]		= int(round(pos[OMNI1][2]*THOUSAND));
	//msgHeader.Qx[0]			= int(round( qIncr[OMNI1].v()[0]*1e9 ));
	//msgHeader.Qy[0]			= int(round( qIncr[OMNI1].v()[1]*1e9));
	//msgHeader.Qz[0]			= int(round( qIncr[OMNI1].v()[2]*1e9));
	//msgHeader.Qw[0]			= int(round( qIncr[OMNI1].s()*1e9 ));
	msgHeader.Qx[0]			=  orientation[0][0];
	msgHeader.Qy[0]			=  orientation[0][1];
	msgHeader.Qz[0]			=  orientation[0][2];
	msgHeader.Qw[0]			=  1.0;

	//msgHeader.transform[0]			=  xfs[0];
	//msgHeader.transform[1]			=  xfs[1];

	msgHeader.delx[1]		= int(round(pos[OMNI2][0]*THOUSAND));
	msgHeader.dely[1]		= int(round(pos[OMNI2][1]*THOUSAND));
	msgHeader.delz[1]		= int(round(pos[OMNI2][2]*THOUSAND));
	//msgHeader.Qx[1]			= int(round( qIncr[OMNI2].v()[0]*1e9 ));
	//msgHeader.Qy[1]			= int(round( qIncr[OMNI2].v()[1]*1e9 ));
	//msgHeader.Qz[1]			= int(round( qIncr[OMNI2].v()[2]*1e9 ));
	//msgHeader.Qw[1]			= int(round( qIncr[OMNI2].s()*1e9 ));
	msgHeader.Qx[1]			=  orientation[1][0];
	msgHeader.Qy[1]			=  orientation[1][1];
	msgHeader.Qz[1]			=  orientation[1][2];
	msgHeader.Qw[1]			=  1.0;
	
	msgHeader.buttonstate[OMNI1]= bttn[OMNI1];
	msgHeader.buttonstate[OMNI2]= bttn[OMNI2];
	msgHeader.grasp[OMNI1]= bttn[OMNI1];
	msgHeader.grasp[OMNI2]= bttn[OMNI2];
	msgHeader.sequence=servo;
	msgHeader.surgeon_mode=fp;
	msgHeader.checksum=checksumUDPData();
	
	// cout<< "msgHeader.delx[1]  "<< msgHeader.delx[1] <<endl;
	//cout << "Button 0: " << bttn[0] << "Button 1: " << bttn[1] << endl;
	cout << "Lef x: " << msgHeader.delx[0] << ", Right x: " << msgHeader.delx[1] << endl;
}
int Omni_Comm::checksumUDPData(){
	int chk=0;
	chk =  (msgHeader.surgeon_mode);
	chk += (msgHeader.delx[0])+(msgHeader.dely[0])+(msgHeader.delz[0]);
	chk += (msgHeader.delx[1])+(msgHeader.dely[1])+(msgHeader.delz[1]);
	chk += (msgHeader.buttonstate[0]);
	chk += (msgHeader.buttonstate[1]);
	chk += (int)(msgHeader.sequence);
	return chk;
}


// get UDP Routine
int Omni_Comm::Recv_UDP_Packet()
{
	int i_ret=1, cnt=0;
	std::string sourceAddress;
	unsigned short sourcePort;
	const int bufferLen = sizeof v_struct;
	char _buff[bufferLen];
	
	while (i_ret > 0){
		
		try {
			i_ret = udpsocket->recvFrom( _buff, bufferLen, sourceAddress, sourcePort );
			if (i_ret == bufferLen){
				// good packet
				memcpy( (void*)&raven2MA, _buff, bufferLen);
				cnt++; 
			} else if (i_ret > 0) {
				// invalid packet size
				cout << "invalid packet size\n";
			}
		}
//		catch (SocketException SE){
//			cerr << "Recv_UDP ERR:"<< SE.what()<< " WSA:" << WSAGetLastError() << ":\n";
//			break;	
//		}
		catch (SocketException SE){
			LPSTR errString = NULL; 
			int errCode = WSAGetLastError(); 
			int size = FormatMessage( FORMAT_MESSAGE_ALLOCATE_BUFFER | FORMAT_MESSAGE_FROM_SYSTEM, 0,
				errCode, 0,	(LPSTR)&errString, 0, 0 ); 
//			cerr << "Recv_UDP ERR (" << errCode << "):" << errString << ":\n";
			break;	
		}


	}

	//cout << "packet " << cnt << "\tforce 0:"<< raven2MA.fz[0]<<":"<<endl;
	return 0;
}

void Omni_Comm::getSlaveForces(hduVector3Dd &fleft, hduVector3Dd &fright)
{
	fleft[0] = (float)raven2MA.fx[0] / 1000;
	fleft[1] = (float)raven2MA.fy[0] / 1000;
	fleft[2] = (float)raven2MA.fz[0] / 1000;

	fright[0] = (float)raven2MA.fx[1] / 1000;
	fright[1] = (float)raven2MA.fy[1] / 1000;
	fright[2] = (float)raven2MA.fz[1] / 1000;

	fleft = xform_ITP2Mantis<hduVector3Dd>(fleft);
	fright = xform_ITP2Mantis<hduVector3Dd>(fright);
}
