/*
*
*  File: rii_master.h
*  Authors: Hawkeye, Paul
*  Created May 2012
*
*  Declares raven II master control functions.
*
*/

#include "ITPteleoperation.h"

#define MICRONS_PER_METER 1000*1000
#define DEFAULT_SCALING_FACTOR 0.125
#define USE_FOOT_PEDAL 03
#define DEBUG_OUTPUT true
#define ADDRESS_ROBOT "128.95.205.220"
#define PORT_ROBOT 36000

/*! HapticsFunction
Haptic rendering function called in every iteration of device haptics thread
\param arg pointer to the parent
*/
void HapticsFunction(void *arg);

void PrintHapticsThreadFrequency();
void PrintPositions(const float leftMasterPosition[], const float rightMasterPosition[]);
void PrintRotations(const float leftMasterRotation[], const float rightMasterRotation[]);
void PrintTorques(const float leftMasterTorques[], const float rightMasterTorques[]);
void PrintCableLengths(const float leftMasterCableLengths[], const float rightMasterCableLengths[]);
void PrintOpenings(const float leftMasterOpening, const float rightMasterOpening);
void PrintFootPedalStates(const bool footPedalStates[]);
void PrintEncoderValues(const int encoder_values[]);
void PrintRotationMatices(const float leftMasterRotationMatrix[][3], const float rightMasterRotationMatrix[][3]);

void RenderSphere(const float spherePosition[], const float masterPosition[3], float masterForce[3]);

void sendToSlave(struct u_struct *us);