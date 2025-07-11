#pragma once

#ifndef _MantisDuoControllerClass_h_
#define _MantisDuoControllerClass_h_

#include "DataDefs.h"

/*!
\class MantisDuoControllerClass

Copyright 2010 MIMIC Technologies, Inc.

\brief An application programming interface class to communicate with and control MantisDuo workstation

\author Mert Sedef
\date 8/6/2010
 */

//! A number of MantisDuoControllerClass constants
#define NO_OF_MASTERS 2
#define NO_OF_ENCODERS 20
#define NO_OF_FOOT_PEDALS 4
#define NO_OF_MOTORS_PER_MASTER 4
#define NO_OF_CABLES_PER_MASTER 4
#define	PI 3.14159265358979323846f

class __declspec(dllexport) MantisDuoControllerClass
{
public:

	/*!
    Constructor for a MantisDuoControllerClass object
    */
	MantisDuoControllerClass(void);

	/*!
    Destructor for a MantisDuoControllerClass object
    */
	~MantisDuoControllerClass(void);

	/*! IsFootPedalPressed
	Gets current state of a foot pedal.
	\param footPedalID ID number of the pedal. There are 4 foot pedals and the ID numbers change between 0 and 3
	\return State of the pedal. True if pressed, false if not pressed
	*/
	bool IsFootPedalPressed(const unsigned int footPedalID);

	/*! GetHapticsThreadFrequency
	Gets current update rate of haptics thread.
	\return Current update rate of haptics thread.
	*/
	double GetHapticsThreadFrequency();

	/*! GetCableLength
	Gets current length of a cable connected to a master
	\param masterID ID number of the master. Left (0) or right (1).
	\param cableID ID number of the cable attached to the master. Side (0), top (1), front (2) or rear (3)
	\return Length of the cable.
	*/
	float GetCableLength(const unsigned int masterID, const unsigned int cableID);

	/*! GetXPosition
	Gets x-component of a master's position.
	\param masterID ID number of the master. Left (0) or right (1).
	\return x-component of the master's position.
	*/
	float GetXPosition(const unsigned int masterID);

	/*! GetYPosition
	Gets y-component of a master's position.
	\param masterID ID number of the master. Left (0) or right (1).
	\return y-component of the master's position.
	*/
	float GetYPosition(const unsigned int masterID);

	/*! GetZPosition
	Gets z-component of a master's position.
	\param masterID ID number of the master. Left (0) or right (1).
	\return z-component of the master's position.
	*/
	float GetZPosition(const unsigned int masterID);

	/*! GetRoll
	Gets roll angle of a master
	\param masterID ID number of the master. Left (0) or right (1).
	\return roll angle of the master in radians.
	*/
	float GetRoll(const unsigned int masterID);
	
	/*! GetPitch
	Gets pitch angle of a master
	\param masterID ID number of the master. Left (0) or right (1).
	\return pitch angle of the master in radians.
	*/
	float GetPitch(const unsigned int masterID);

	/*! GetYaw
	Gets yaw angle of a master
	\param masterID ID number of the master. Left (0) or right (1).
	\return yaw angle of the master in radians.
	*/
	float GetYaw(const unsigned int masterID);

	/*! GetOpening
	Gets opening of the grip of a master
	\param masterID ID number of the master. Left (0) or right (1).
	\return opening of the grip of the master
	*/
	float GetOpening(const unsigned int masterID);

	/*! GetMotorTorque
	Gets current torque of a motor connected to a master
	\param masterID ID number of the master. Left (0) or right (1).
	\param motorID ID number of the motor attached to the master. Side (0), top (1), front (2) or rear (3)
	\return Torque of the motor.
	*/
	float GetMotorTorque(const unsigned int masterID, const unsigned int motorID);

	/*! GetEncoderValue
	Gets current value of an encoder
	\param encoderID ID number of the encoder. 
	Left Master:	Encoders 0-3 correspond to motors
					Encoders 12-14 correspond to rotations
					Encoder 15 correspond to opening
	Right Master:	Encoders 4-7 correspond to motors
					Encoders 16-18 correspond to rotations
					Encoder 19 correspond to opening
	\return Value of the encoder.
	*/
	int GetEncoderValue(const unsigned int encoderID);

	/*! IsHapticsThreadOn
	Gets the current state of haptics thread
	\return True if haptics thread is running. False otherwise.
	*/
	bool IsHapticsThreadOn();

	/*! IsDeviceConnected
	Gets the current state of device connection
	\return True if device is connected. False otherwise.
	*/
	bool IsDeviceConnected();

	/*! SetForce
	Sets force to be displayed on a master.
	\param masterID ID number of the master. Left (0) or right (1).
	\param force Force vector to be displayed on the master.
	*/
	void SetForce(const unsigned int masterID, const float force[]);

	/*! SetHapticsFunction
	Sets the user function to be called at each iteration of haptics thread
	\param hapticsFunctionPtr Pointer to the user function responsible for haptic rendering. This function is called in each iteration
	of haptics thread.
	*/
	void SetHapticsFunction(void(*hapticsFunctionPtr)(void *));

	/*! InitializeDevice
	Connects to device, starts motors, releases breaks, starts haptics thread and sets the function to be called in haptics thread
	\param hapticsFunctionPtr Pointer to the user function responsible for haptic rendering. This function is called in each iteration
	of haptics thread.
	\param Parent of hapticsFunctionPtr
	\return True if device is connected and haptics thread is started. False otherwise.
	*/
	bool InitializeDevice(void(*hapticsFunctionPtr)(void *), void *arg);

	/*! TerminateDevice
	Stops haptics thread, sets brakes, and disconnects from device.
	*/
	void TerminateDevice();

private:

	void *m_pHapticsFunctionParent;
	bool m_bHapticsThreadOn;
	bool m_bDeviceConnected;
	unsigned int m_uiTimerResolution;
	double m_dHapticsThreadFrequency;
	float m_fMaximumForce;

	RecordEncoder m_Encoders;
	float m_fMasterPositions[NO_OF_MASTERS][3];
	float m_fMasterRotations[NO_OF_MASTERS][3];
	float m_fMasterOpenings[NO_OF_MASTERS];
	float m_fMasterMotorTorques[NO_OF_MASTERS][NO_OF_MOTORS_PER_MASTER];
	float m_fMasterCableLengths[NO_OF_MASTERS][NO_OF_CABLES_PER_MASTER];
	float m_fMasterRotationMatricesCompensated[NO_OF_MASTERS][3][3];
	bool m_bFootPedalStates[NO_OF_FOOT_PEDALS];

	float m_fMasterPositionsCompensated[NO_OF_MASTERS][3];
	float m_fMasterRotationsCompensated[NO_OF_MASTERS][3];

	float m_fIdleMotorTorques[NO_OF_MOTORS_PER_MASTER];

	RecordMantisDuoSetup m_MantisDuoSetup;
};

#endif