/*
*
*  File: rii_master.cpp
*  Authors: Hawkeye, Paul
*  Created May 2012
*
*  Implements raven II master control functions.
*
*/
#include "stdafx.h"
#include <iostream> 
#include "windows.h"
#include "MantisDuoControllerClass.h"
#include <cmath>


#include "rii_master.h"
#include "ITPteleoperation.h"
#include "PracticalSocket\PracticalSocket.h"

using namespace std;

extern MantisDuoControllerClass *g_DeviceController;
extern unsigned int g_uiCounter; 
const double scalingFactor = DEFAULT_SCALING_FACTOR;

// Communication object for networking
extern Omni_Comm gComm;


hduVector3Dd pos_delta[2];
hduVector3Dd rot_delta[2];
hduVector3Dd pos_offset[2];
hduVector3Dd rot_offset[2];
hduMatrix xfs[2];

int g_footpedal = 0;
unsigned int servo=0;
bool indexing= false;

extern stMA2UI_DATA Ma2UIdata;
extern stUI2MA_DATA UI2Madata;

const hduQuaternion q_identity;

void HapticsFunction(void *arg)
{
	float forces[NO_OF_MASTERS][3], positions[NO_OF_MASTERS][3], rotations[NO_OF_MASTERS][3], openings[NO_OF_MASTERS];
	static float last_positions[NO_OF_MASTERS][3];
	bool foot_pedal_states[4];

	// get positions, rotations, and opening values of masters.
	for (int master_ID = 0; master_ID < NO_OF_MASTERS; master_ID++)
	{
		positions[master_ID][0] = g_DeviceController->GetXPosition(master_ID);
		positions[master_ID][1] = g_DeviceController->GetYPosition(master_ID);
		positions[master_ID][2] = g_DeviceController->GetZPosition(master_ID);

		rotations[master_ID][0] = g_DeviceController->GetRoll(master_ID);
		rotations[master_ID][1] = g_DeviceController->GetPitch(master_ID);
		rotations[master_ID][2] = g_DeviceController->GetYaw(master_ID);

		openings[master_ID] = g_DeviceController->GetOpening(master_ID);
	}

	// get foot pedal states
	for (int foot_pedal_ID = 0; foot_pedal_ID < NO_OF_FOOT_PEDALS; foot_pedal_ID++)
	{
		foot_pedal_states[foot_pedal_ID] = g_DeviceController->IsFootPedalPressed(foot_pedal_ID);
	}
	
	// initialize forces - should compensate for gravity.
	for (int master_ID = 0; master_ID < NO_OF_MASTERS; master_ID++)
	{
		for (int ui = 0; ui < 3; ui++)
		{
			forces[master_ID][ui] = 0.0f;
		}
	}

	int footpedal     = foot_pedal_states[USE_FOOT_PEDAL] ;
	static int inited = 0;
	float pos_delta[NO_OF_MASTERS][3];

	if (!footpedal || !inited) 
	{	// initialize deltas
		inited = 1;
		for (int master_ID = 0; master_ID < NO_OF_MASTERS; master_ID++)
			for (int i = 0; i < 3; i++)
				pos_delta[master_ID][i] = 0;

	}
	else
	{	//generate deltas
		for (int master_ID = 0; master_ID < NO_OF_MASTERS; master_ID++)
			for (int i = 0; i < 3; i++)
				pos_delta[master_ID][i] = positions[master_ID][i] - last_positions[master_ID][i];
	}

	for (int master_ID = 0; master_ID < NO_OF_MASTERS; master_ID++)
	{	//copy current position to last position
		for (int i = 0; i < 3; i++)
		{
			last_positions[master_ID][i] = positions[master_ID][i];
		}
	}

	
	if (g_uiCounter % 10000 == 0 && DEBUG_OUTPUT)
	{
		for (int master_ID = 0; master_ID < NO_OF_MASTERS; master_ID++)
		{
			cout << "US Size:" << sizeof(struct u_struct) << endl;
			cout << "\tFP    : " << footpedal << endl;
			cout << "\tDev   : " << master_ID << " (x,y,z) :  (" <<	positions[master_ID][0] << ",\t " << positions[master_ID][1] << ",\t " << positions[master_ID][2] << ")\t\t";
			cout << "\tDelta : " << master_ID << " (x,y,z) :  (" <<	pos_delta[master_ID][0] << ",\t " << pos_delta[master_ID][1] << ",\t " << pos_delta[master_ID][2] << ")\n";
		}
	}

	struct u_struct us;
	us.sequence = g_uiCounter;
	us.pactyp = 6;
	us.version = 7;
	us.surgeon_mode = footpedal;

	for (int master_ID = 0; master_ID < NO_OF_MASTERS; master_ID++)
	{
		us.delx[master_ID] = -1*(int)(pos_delta[master_ID][0] * MICRONS_PER_METER * scalingFactor); // sign directions correctly
		us.dely[master_ID] = (int)(pos_delta[master_ID][1] * MICRONS_PER_METER * scalingFactor);
		us.delz[master_ID] = -1*(int)(pos_delta[master_ID][2] * MICRONS_PER_METER * scalingFactor); 

		// not currently implemented.
		us.Qx[master_ID] = 0; 		us.Qy[master_ID] = 0; 		us.Qz[master_ID] = 0; 		us.Qw[master_ID] = 0;

		us.buttonstate[master_ID] = 0;
		us.grasp[master_ID] = 0;
	}
	us.checksum = UDPChecksumI(&us);

	if(DEBUG_OUTPUT){
		printf("receiddd u_s (%i): delX(%i,  \t%i,  \t%i) \t/delQ(%f,  \t%f,  \t%f,  \t%f) \t\t delX(%i,  \t%i,  \t%i) \t/delQ(%f,  \t%f,  \t%f  \t%f) \n",
			sizeof(int),
			us.delx[0], us.dely[0], us.delz[0],
			us.Qx[0], us.Qy[0], us.Qz[0], us.Qw[0],
			us.delx[1], us.dely[1], us.delz[1],
			us.Qx[1], us.Qy[1], us.Qz[1], us.Qw[1]
		);
	}

	sendToSlave(&us);
	g_uiCounter++;

}













//Global variable for world coordinate scale uniform in all 3 axis.
HDdouble scale = 0.1;

hduVector3Dd pos_delta[2];
hduVector3Dd rot_delta[2];
hduVector3Dd pos_offset[2];
hduVector3Dd rot_offset[2];
hduMatrix xfs[2];

extern const hduMatrix rotXMx;
extern const hduMatrix rotYMx;
extern const hduMatrix rotZMx;

int g_footpedal = 0;
unsigned int servo=0;
bool indexing= false;

extern stMA2UI_DATA Ma2UIdata;
extern stUI2MA_DATA UI2Madata;

const hduQuaternion q_identity;

// Communication object for communication with SUI and Slave robot
Omni_Comm gComm(&Ma2UIdata, &UI2Madata);








/*******************************************************************************
Incremental position update callback function
*******************************************************************************/
HDCallbackCode HDCALLBACK PositionUpdate(void *data)
{
	servo++;
	int nButtons = 0, footpedal;
	int bttn[2] = {0,0};
	hduVector3Dd position[2];
	hduMatrix rotMat;
	hduMatrix xform;
	static hduQuaternion qPrev[2];
	static hduVector3Dd p_position[2];

	hduQuaternion qCurr[2], qIncr[2];

	HDErrorInfo error;
	int rl2sui;

	footpedal = gComm.Check_Flag(FPEDAL_RIGHT) ? TRUE : FALSE;

	for (int devID=0; devID <= 1; devID++){

		// Set current frame and device
		hdBeginFrame(devHandle[devID]);
		hdMakeCurrentDevice(devHandle[devID]);

		// Get button state using bitmask:
		hdGetIntegerv(HD_CURRENT_BUTTONS, &nButtons);
		
		bttn[devID] = 0;
		if ( nButtons & HD_DEVICE_BUTTON_2 ) // button 2 releases grasp
			bttn[devID] = -1;
		else if ( nButtons & HD_DEVICE_BUTTON_1 ) // button 1 engages grasp
			bttn[devID] = 1;

		// Get omni position in pedal dn state
		hdGetDoublev(HD_CURRENT_TRANSFORM, xform);
		applyTransforms(xform);

		// position
		position[devID] = hduVector3Dd(xform[3][0], xform[3][1], xform[3][2]);
		hduVecScaleInPlace(position[devID],scale);		// position scaling

		// rotation
		rotMat.set(xform);
		rotMat.getRotationMatrix(rotMat);
		qCurr[devID] = hduQuaternion(rotMat);

		int fake_rotation = 0;
		if( gComm.Check_Flag(FPEDAL_RIGHT) && gComm.Check_Flag(BASIC_START) )
		{
			// Get position increment
			hduVecSubtract(pos_delta[devID],position[devID],p_position[devID]);		// delta = current - previous
			// Get quaternion increment
			qIncr[devID] = qPrev[devID].inverse()*qCurr[devID];

			if (fake_rotation)
			{
				rotMat.set(rotZMx);
				rotMat.getRotationMatrix(rotMat);
				qIncr[devID] = hduQuaternion(rotMat);
			}
		} 

		else 
		{
			indexing=true;

			// Set zero increments
			hduVecSet(pos_delta[devID],0.0,0.0,0.0);
			qIncr[devID] = q_identity;
			bttn[devID] = 0;
		}

		// prev. position
		p_position[devID][0] = position[devID][0];
		p_position[devID][1] = position[devID][1];
		p_position[devID][2] = position[devID][2];

		// prev. rotation
		qPrev[devID] = qCurr[devID];

		// fake runlevel to GUI
		rl2sui = 3-gComm.Check_Flag(FPEDAL_RIGHT);

		hdEndFrame(devHandle[devID]);
	}



	if(gComm.Check_Flag(BASIC_PROGRAM)) { // when UI allows 'Server' run
		gComm.Update_UDP_Data(pos_delta, qIncr, bttn, footpedal, servo, xfs );  // Update robot gCommand packet
		gComm.Send_UDP();
	}

	if(servo%100 == 1) {
		gComm.Update_MA2UI(pos_delta, rl2sui, servo);			// Update SUI data
		gComm.Send_TCP();
	}

	if (HD_DEVICE_ERROR(error = hdGetError())) {
		hduPrintError(stderr, &error, "Error during main scheduler callback\n");
		//		if (hduIsSchedulerError(&error))    return HD_CALLBACK_DONE;
	}

	return HD_CALLBACK_CONTINUE;
}