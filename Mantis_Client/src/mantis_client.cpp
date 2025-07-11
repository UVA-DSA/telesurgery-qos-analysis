/*
*
*  File: mantis_client
*  Authors: Hawkeye, Paul
*  Created October 2012
*
*  Implements raven II master control functions.
*  Is derived from mantis client code and omni_client code.
*
*/
#include "stdafx.h"
#include <iostream> 
#include <HDU/hduQuaternion.h>
#include <HDU/hduMatrix.h>
#include <HDU/hduVector.h>
#include <cmath>

#include "windows.h"
#include "MantisDuoControllerClass.h"

#include "C:\Users\Mimic Technologies\Desktop\BRL_Master-master_for2010\SUI_win RII\VS_GUI_SERVER/CommonDS.h"
#include "comm.h"
#include "ITPteleoperation.h"
#include "../PracticalSocket\PracticalSocket.h"
#include "coordinateSystems.h"

double filterRoll(int devID);
double filterPitch(int devID);
double filterYaw(int devID);

using namespace std;

MantisDuoControllerClass * g_Mantis;
extern unsigned int g_uiCounter; 
extern hduVector3Dd movechar;
extern int kbd_arm2move;
extern bool gohomenow ;
extern bool printnow;

//int frequency_div_factor = 1;

double scalingFactor = DEFAULT_SCALING_FACTOR;
bool enable_mantis_force = TRUE;

// Conversion of reference frames from Phantom Omni to Mantis Duo:
 //Omni X = Mantis Y ; Omni Y = Mantis Z ; Omni Z = Mantis X;
// Column major:
const static hduMatrix mantis2omni(0,0,1,0,  1,0,0,0,  0,1,0,0, 0,0,0,1);

const static hduVector3Dd ws_middle[2] = {
	hduVector3Dd(0.0, -175.0, 0.0), 
	hduVector3Dd(0.0, 175.0, 0.0)
};

// Communication object for networking
extern Omni_Comm gComm;

hduVector3Dd pos_delta[2];
hduVector3Dd rot_delta[2];
double orientation_current[2][3];
double orientation_delta[2][3];
double orientation_prev[2][3];
hduVector3Dd pos_offset[2];
hduVector3Dd rot_offset[2];
hduMatrix xfs[2];

int g_footpedal = 0;
unsigned int servo=0;
bool indexing= false;
bool startAuto = false;

const hduQuaternion q_identity;
const static float graspScale = -5000.0;   // scaling to miliradians and also to match robot grasp space.
                                            // Negative for sign convention of Mantis

int auto_trajectory_update(hduVector3Dd &position, int devID);

void HapticsFunction(void *arg)
{
	servo++;

	// if ((servo % frequency_div_factor == 0)) return;

	static int lead_in_counter = 0;

	// Footpedal commands
	int footpedal;
	static int AUTOpedal = 0;
	static int VFRpedal = 0;

	// Trajectory info
	int curr_traj_state = 0, prev_traj_state = 0;
	int bttn[2] = {0,0};
	
	// Motion info
	hduVector3Dd position[2];
	hduVector3Dd mantis_position[2];
	hduVector3Dd rotation[2];
	hduVector3Dd force [2];
	float graspAngle[2];
	hduMatrix rotMat;
	hduMatrix xform;
	static hduQuaternion qPrev[2];
	static hduVector3Dd p_position[2];
	static float p_graspAngle[2] = {0,0};

	hduQuaternion qCurr[2], qIncr[2];

	int rl2sui;

	// UNUSED VARIABES
	//	float forces[NO_OF_MASTERS][3], positions[NO_OF_MASTERS][3], rotations[NO_OF_MASTERS][3], openings[NO_OF_MASTERS];
	//	static float last_positions[NO_OF_MASTERS][3];
	
	//Get footpedal state
	const static int foot_pedal_ID = 1;
	const static int foot_AUTO_ID = 3;
	const static int foot_VFR_ID = 2;

	//Integrate keyboard pedal change.  Real footpedal overrides when toggled
	static int lastfp = 0;
	if (!!lastfp != g_Mantis->IsFootPedalPressed(foot_pedal_ID))
	{
		footpedal =  g_Mantis->IsFootPedalPressed(foot_pedal_ID);
		g_footpedal = footpedal;
		gohomenow = 0;
	}
	else 
	{
		footpedal = !!g_footpedal | g_Mantis->IsFootPedalPressed(foot_pedal_ID) | gohomenow;
		//cout << footpedal << endl;
	}
	lastfp = g_Mantis->IsFootPedalPressed(foot_pedal_ID);
	//cout << footpedal << "  " << lastfp << " " << g_footpedal << " " << gohomenow << endl;
	//Automtic movement
	if (!AUTOpedal && g_Mantis->IsFootPedalPressed(foot_AUTO_ID) )
	{
		startAuto = true;
	}
	AUTOpedal = g_Mantis->IsFootPedalPressed(foot_AUTO_ID);

	//Send keyboard command to VFR
	if (!VFRpedal&& g_Mantis->IsFootPedalPressed(foot_VFR_ID) )
	{
		gComm.send_command_to_vfr('n');
		cout <<"Pedal to the medal!\n";
	}
	VFRpedal = g_Mantis->IsFootPedalPressed(foot_VFR_ID);

	int encoder_x[2];
	int encoder_y[2];
	int encoder_z[2];
	//Get positions, rotations, and grasper values of masters.
	for (int devID = 0; devID < NO_OF_MASTERS; devID++)
	{
		force[devID][0] = force[devID][1] = force[devID][2] = 0.0f;
		graspAngle[devID] = g_Mantis->GetOpening(devID);

		// Get device position
		const int meter2mm = 1000;
		mantis_position[devID][0] = g_Mantis->GetXPosition(devID) * meter2mm;
		mantis_position[devID][1] = g_Mantis->GetYPosition(devID) * meter2mm;
		mantis_position[devID][2] = g_Mantis->GetZPosition(devID) * meter2mm;

		
		encoder_x[devID] = g_Mantis->GetEncoderValue(12 + 4*devID);
		encoder_y[devID] = g_Mantis->GetEncoderValue(12 + 4*devID + 1);
		encoder_z[devID] = g_Mantis->GetEncoderValue(12 + 4*devID + 2);
		xform = hduMatrix::createTranslation(mantis_position[devID][0],mantis_position[devID][1],mantis_position[devID][2]);

		// Get device rotation
		hduMatrix xrotmat = hduMatrix::createRotationAroundX(filterRoll(devID));
		hduMatrix yrotmat = hduMatrix::createRotationAroundY(filterPitch(devID));
		hduMatrix zrotmat = hduMatrix::createRotationAroundZ(filterYaw(devID));

		xform = xrotmat * yrotmat * zrotmat * xform;
		xform = xform * mantis2omni;
		applyTransforms(xform); 

		// position
		position[devID] = hduVector3Dd(xform[3][0], xform[3][1], xform[3][2]);
		hduVecScaleInPlace(position[devID],scalingFactor);		// position scaling

		// Throw in an automatic trajectory
		if (AUTOpedal)
		{
			static hduVector3Dd temp;
			curr_traj_state = (temp, devID);
			if(lead_in_counter < 1000){
				temp[0] = temp[0] * .001 * lead_in_counter;
				temp[1] = temp[1] * .001 * lead_in_counter;
				temp[2] = temp[2] * .001 * lead_in_counter;
				lead_in_counter++;
			}
			position[devID] += temp * meter2mm;
			if(curr_traj_state != prev_traj_state) lead_in_counter = 0;
			prev_traj_state = curr_traj_state;
		}
		else {
			lead_in_counter = 0;
		}
	
		//Get quaternion representation of current device transform
		rotMat.set(xform);
		rotMat.getRotationMatrix(rotMat);
		qCurr[devID] = hduQuaternion(rotMat);

		orientation_current[devID][0] = encoder_x[devID];
		orientation_current[devID][1] = encoder_y[devID];
		orientation_current[devID][2] = encoder_z[devID];

		//cout << "Pedal" << footpedal << endl;
		
		
		if( footpedal && 
			gComm.Check_Flag(BASIC_START) && 
			(scalingFactor > 0) && 
			!gohomenow // no moving during mantis homing
			)
		{

			// Get position increment
			hduVecSubtract(pos_delta[devID],position[devID],p_position[devID]);		// delta = current - previous

			// Get quaternion increment
			qIncr[devID] = qPrev[devID].inverse() * qCurr[devID];
			qIncr[devID].v()[0] = 0.0;

			orientation_delta[devID][0] = orientation_current[devID][0] - orientation_prev[devID][0];
			orientation_delta[devID][1] = orientation_current[devID][1] - orientation_prev[devID][1];
			orientation_delta[devID][2] = orientation_current[devID][2] - orientation_prev[devID][2];
			
			//if (devID == 0){
			//	cout << "X: " << orientation_delta[0][0] << " Y: " << orientation_delta[0][1] << " Z: " << orientation_delta[0][2] << endl;
			//}
			// Grasp calculations
			//bttn[devID] = int( (graspAngle[devID] - p_graspAngle[devID]) * graspScale );
			bttn[devID] = int(graspAngle[devID] * graspScale );
			// miliradians
			if (bttn[devID] != 0) {
				p_graspAngle[devID] +=  float(bttn[devID])/graspScale;               // update prev grasp, but avoid roundoff.
			}
		} 
		else 
		{
			indexing=true;
			// Set zero increments
			hduVecSet(pos_delta[devID],0.0,0.0,0.0);
			qIncr[devID] = q_identity;
			orientation_delta[devID][0] = 0;
			orientation_delta[devID][1] = 0;
			orientation_delta[devID][2] = 0;
			bttn[devID] = int(graspAngle[devID] * graspScale );
			p_graspAngle[devID] = graspAngle[devID];
		}

		// prev. position
		p_position[devID][0] = position[devID][0];
		p_position[devID][1] = position[devID][1];
		p_position[devID][2] = position[devID][2];
		// prev. rotation
		qPrev[devID] = qCurr[devID];

		orientation_prev[devID][0] = orientation_current[devID][0];
		orientation_prev[devID][1] = orientation_current[devID][1];
		orientation_prev[devID][2] = orientation_current[devID][2];
		
		// fake runlevel to GUI
		rl2sui = 3-gComm.Check_Flag(FPEDAL_RIGHT);
	} // end loop for each hand

	// integrate keyboard commands...
	if (!movechar.isZero(1e-5) && kbd_arm2move <=1)
	{
		pos_delta[kbd_arm2move] += movechar;
	}

	//Send data to slave
	if(gComm.Check_Flag(BASIC_PROGRAM)) { // when UI allows 'Server' run
		gComm.Update_UDP_Data(pos_delta, orientation_delta, bttn, footpedal, servo, xfs );  // Update robot command packet
		gComm.Send_UDP();
		gComm.Recv_UDP_Packet();
	}

	// Check force update from slave
	gComm.getSlaveForces(force[0], force[1]);

	//Force claculation stuff
	for (int devID = 0; devID < NO_OF_MASTERS && enable_mantis_force; devID++)
	{
		// Move device to "home" position 
		if (gohomenow && (kbd_arm2move == devID || kbd_arm2move == 2) )
		{
			hduVector3Dd kp(0.1,0.1,0.1);
			force[devID] =  -kp * (mantis_position[devID] - ws_middle[devID]);
		}
		float temp_force[3] = {(float)force[devID][0], (float)force[devID][1],(float)force[devID][2]};
		g_Mantis->SetForce(devID, temp_force);
		
		if (printnow) 
			cout << "f("<< devID << "):" << temp_force[0] << ",\t" << temp_force[1] << ",\t" << temp_force[2] << endl;
	}

	//Send to GUI
	if(servo%100 == 1) {
		gComm.Update_MA2UI(pos_delta, rl2sui, servo);			// Update SUI data
		gComm.Send_TCP();
	}

	/////// Check timing:   ///////
	__int64 tnow;
	static __int64 tlast=0, frequency=0;
	
	if (tlast == 0) {
		QueryPerformanceCounter((LARGE_INTEGER*)&tlast);
		QueryPerformanceFrequency((LARGE_INTEGER*)&frequency);
	}
	QueryPerformanceCounter((LARGE_INTEGER*)&tnow);
	
	static __int64 intervals[10] = {0};
	static __int64 sum = 0;

	sum -= intervals[servo%10];
	intervals[servo%10] = tnow - tlast;
	tlast = tnow;

	sum += intervals[servo%10];
	double av_interval = (double)sum / ((double)frequency * 10.0);
	/////// End check timing   ///////
}

const static int filtlen=50;
const static double rollover = 2.5;;

// filter rol values using windowed average
double filterRoll(int devID)
{
	static double filtvalR[2][filtlen];
	static double winav[2] = {0,0};

	//int encoder_x[2];
	//int encoder_y[2];
	//int encoder_z[2];
	//for (int i = 0; i < NO_OF_MASTERS; i++)
	//{
	//	encoder_x[i] = g_Mantis->GetEncoderValue(12 + 4*i);
	//	encoder_y[i] = g_Mantis->GetEncoderValue(12 + 4*i + 1);
	//	encoder_z[i] = g_Mantis->GetEncoderValue(12 + 4*i + 2);
	//}

	//cout << "X: " << encoder_x[0] << " Y: " << encoder_y[0] << " Z: " << encoder_z[0] << endl;

	double rl = g_Mantis->GetRoll(devID);

	// check rollover
	while (fabs(winav[devID] - rl) > PI)
	{
		if (winav[devID] > rl) 
			rl += 2*PI;
		else 
			rl -= 2*PI;
	}

	// TODO divide by filtlen here.
	filtvalR[devID][servo%filtlen] =  rl;

	// initialize filter
	if (servo<filtlen)
		return filtvalR[devID][servo];

	double avg=0;
	for (int i=0; i<filtlen; i++)
	{
		avg += filtvalR[devID][i];
	}
	winav[devID] = avg/filtlen;

	return winav[devID];
}

// filter pitch values using windowed average
double filterPitch(int devID)
{
	static double filtvalP[2][filtlen];
	static double winav[2] = {0,0};

	double pt = g_Mantis->GetPitch(devID);
	
	// check rollover
	while (fabs(winav[devID] - pt) > PI)
	{
		if (winav[devID] > pt) 
			pt += 2*PI;
		else 
			pt -= 2*PI;
	}

	filtvalP[devID][servo%filtlen] =  pt;

	// initialize filter
	if (servo<filtlen)
		return filtvalP[devID][servo];

	double avg=0;
	for (int i=0; i<filtlen; i++)
	{
		avg += filtvalP[devID][i];
	}
	winav[devID] = avg/filtlen;

	return winav[devID];
}

// filter yaw values using windowed average
double filterYaw(int devID)
{
	static double filtvalY[2][filtlen];
	static double winav[2] = {0,0};

	double yw = g_Mantis->GetYaw(devID);

	// check rollover
	while (fabs(winav[devID] - yw) > PI)
	{
		if (winav[devID] > yw) 
			yw += 2*PI;
		else 
			yw -= 2*PI;
	}
	filtvalY[devID][servo%filtlen] =  yw;

	// initialize filter
	if (servo<filtlen)
		return filtvalY[devID][servo%filtlen];

	double avg=0;
	for (int i=0; i<filtlen; i++)
	{
		avg += filtvalY[devID][i];
	}
	winav[devID] = avg/filtlen;

	return winav[devID];
}



/*
*  auto_trajectory_update()
*     Follow some automatic trajectory
*/
int auto_trajectory_update(hduVector3Dd &out_trajUpdate, int devID)
{
	static int traj_state = 0;
	const static int cycles = 3;  // number of cycles in our trajectory thingy

	double Ax = 0.040;
	double Ay = 0.040;
	double Az = 0.020;
	
	double global_seconds = (double)(servo) / 1000;
	static double start_seconds = 0;

	if (startAuto)
	{
		startAuto = false;
		start_seconds = global_seconds;
		cout<< "STARTSTARTSTARTSTARTSTARTSTARTSTARTSTARTSTARTSTARTSTARTSTARTSTARTSTARTSTARTSTARTSTART\n\n\n";
	}
	double loop_seconds = global_seconds - start_seconds;

	double period = 4.0; //seconds
	traj_state = (int) (loop_seconds/period) % cycles;

	hduVector3Dd update(0,0,0);

	switch(traj_state){
//	case 4:
//		update[0] = Ax * sin(2*PI * loop_seconds/period + PI/4);
//		update[1] = 0; Ay * cos(2*PI * loop_seconds/period + PI/4);
//		update[2] = 0; // Az * sin(2*PI * loop_seconds/period);
//		break;
	case 0:
		update[0] = Ax * sin(2*PI * loop_seconds/period);
		update[1] = Ay * cos(2*PI * loop_seconds/period);
		update[2] = Az * sin(2*PI * loop_seconds/period);
		break;
	case 1:
		update[0] = 1.25 * Ax * sin(2*PI * loop_seconds/period);
		update[1] = 1.25 * Ay * cos(2*PI * loop_seconds/period);
		update[2] = 1.25 * Az * sin(2*PI * loop_seconds/period);
		break;
	case 2:
		update[0] = 1.5 * Ax * sin(2*PI * loop_seconds/period);
		update[1] = 1.5 * Ay * cos(2*PI * loop_seconds/period);
		update[2] = 1.5 * Az * sin(2*PI * loop_seconds/period);
		break;
	case 3:
		update[0] = 1.75 * Ax * sin(2*PI * loop_seconds/period);
		update[1] = 1.75 * Ay * cos(2*PI * loop_seconds/period);
		update[2] = 1.75 * Az * sin(2*PI * loop_seconds/period);
		break;
	default:
		traj_state = 0;
		break;
	}

	out_trajUpdate = update;
//	cout << "ts:" << traj_state << "\t l_s: " <<  loop_seconds << "\tvec: " << update << endl;
	return traj_state;
}