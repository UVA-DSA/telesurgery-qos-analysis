/*

File: cameraAngle.h
Author: Hawkeye King
Written June-2008

This file implements rotation from the Omni frame to the camera view angle.

*/
void applyTransforms(hduMatrix &xform);
void omni2ITPTransform(hduMatrix &xform);


const static hduMatrix mantis_to_ITP( -1,0,0,0,  0,1,0,0,  -0,0,-1,0, 0,0,0,1);

template<class myType> 
myType xform_ITP2Mantis(myType &in_xf)
{
	return mantis_to_ITP.getInverse() * in_xf;
}

//hduVector3Dd xform_ITP2Mantis(hduVector3Dd vec)
