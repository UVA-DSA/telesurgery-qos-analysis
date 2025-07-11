/* Copyright 2010 MIMIC Technologies, Inc.
 *
 * M. Vollenweider
 * 2006
 * 
 * Modified by J. Jurmain
 * 2006
 *
 * Modified by Mert Sedef
 * 2010
 */

//! A number of Barracuda.dll type definitions and constants

#ifndef DATADEFS_H
#define DATADEFS_H

#define PWM_OUT		0x02	
#define DIGITAL_IN	0x10	
#define ENCODER_IN	0x20	

typedef float FLOAT32, *PFLOAT32;

typedef struct _RecordVector3f
{
    FLOAT32	x;		
    FLOAT32	y;		
    FLOAT32	z;		
} Vector3f; 

typedef struct 
{
    int	Value[20];		
    int	Zero[20];		
} RecordEncoder;

typedef struct 
{
    WORD	Header;		
    WORD	Argument;	

	FLOAT32	min_pwm_value;	
	FLOAT32	max_pwm_value;	
	FLOAT32	torque_factor;	

	FLOAT32	pulse_per_rot;	
	FLOAT32	r_pully;		

	Vector3f	c_exit_0;	
	Vector3f	c_exit_1;	
	Vector3f	c_exit_2;	
	Vector3f	c_exit_3;	
	Vector3f	c_offset;	

	Vector3f	c_pos_0;	
	Vector3f	c_rot_0;	

	FLOAT32	rpy_ratio;		
	FLOAT32	grip_ratio;		
	int		enc_Offset;		
	int		grip_offset;	
	int		gpio_button_offset;	
	int		grip_button_offset;	

	FLOAT32	forceFilter;		
	FLOAT32	forceFilterDec;						

	Vector3f	filteredF;	
	FLOAT32	c_ratio_0;		
	FLOAT32	c_ratio_1;		
	FLOAT32	c_ratio_2;		
	FLOAT32	c_ratio_3;		
	FLOAT32	c_length_0;		
	FLOAT32	c_length_1;		
	FLOAT32	c_length_2;		
	FLOAT32	c_length_3;		

	FLOAT32	c_pos_1;		
	FLOAT32	c_pos_2;		
	FLOAT32	c_pos_3;		
	FLOAT32	c_pos_4;		
	FLOAT32	c_pos_5;		
	FLOAT32	c_pos_6;		
	FLOAT32	c_pos_7;		
	FLOAT32	c_pos_8;		
	FLOAT32	t_pos_1;		
	FLOAT32	t_pos_2;		
} RecordMantisDuoSetup; 
#define MANTIS_DUO_SETUP_SIZE		sizeof(RecordMantisDuoSetup)

#endif  // DATADEFS_H
