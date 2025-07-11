/*****************************************************************************

omni_comm.h/omni_comm.h

These files declare and define objects for communicating with the 
robot slave and the Surgical User Interface.

Class created by KoSy
Modified by Hawkeye

*****************************************************************************/
#include <HDU/hduQuaternion.h>
#include "../PracticalSocket/PracticalSocket.h"
#include "ITPteleoperation.h"



#define UDP_RECV_PORT 36001
class Omni_Comm
{
public:
	//Omni_Comm(stMA2UI_DATA*, stUI2MA_DATA*,unsigned short, char *);
	Omni_Comm();
	~Omni_Comm();

	// ** TCP Commnucation to GUI  **
	int Initialize_TCP_GUI();
	int Update_MA2UI(hduVector3Dd pos[2],int rl, unsigned int servo);
	int Check_UI2MA(int message);
	bool Check_Flag(int mode);
	void Set_Flag(int value,int mode);
	void Send_TCP();
	void Recv_TCP();

	TCPSocket* tcpsocket;
	stMA2UI_DATA pMa2UIdata;
	stUI2MA_DATA pUI2Madata;

	// ** UDP Commnucation to Robot  **
	int Initialize_UDP_Robot(int argc, char*argv[]); 
	void Update_UDP_Data(hduVector3Dd pos[2], double orientation[2][3], int bttn[2], int fp, unsigned int servo, hduMatrix xfs[2]);
	void Send_UDP();
	int checksumUDPData();

	// send separate udp commands to virtual fixture renderer
	void send_command_to_vfr(char cmd);
	
	int startUDPListener();
	int Recv_UDP_Packet();

	void getSlaveForces(hduVector3Dd& fleft, hduVector3Dd& fright);

	u_struct msgHeader;
	v_struct raven2MA;
	UDPSocket *udpsocket;
	unsigned short port_Robot;
	char addr_Robot[16];
	int iUDPaddr;
};