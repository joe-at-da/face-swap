"""
Face Swapping API endpoints for the Parliament Video Clip Manager.

These endpoints provide face swapping functionality using the FaceSwapService.
"""

import os
import tempfile
import logging
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from pydantic import BaseModel

from backend.services.face_swap import FaceSwapService
from backend.services.intelligent_face_swap import IntelligentFaceSwapService

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(tags=["face-swap"])

# Initialize face swap services
face_swap_service = FaceSwapService()
intelligent_face_swap_service = IntelligentFaceSwapService()

class FaceSwapRequest(BaseModel):
    """Request model for face swapping."""
    target_member_id: str
    blend_factor: float = 0.7

class FaceSwapResponse(BaseModel):
    """Response model for face swapping results."""
    success: bool
    message: str
    faces_detected: Optional[int] = None
    faces_swapped: Optional[int] = None
    output_path: Optional[str] = None
    target_member_id: Optional[str] = None

@router.get("/targets", response_model=List[Dict[str, Any]])
async def get_available_targets():
    """
    Get list of available MP faces for face swapping.
    
    Returns:
        List of available MP faces with member information
    """
    try:
        available_faces = face_swap_service.get_available_mp_faces()
        return available_faces
    except Exception as e:
        logger.error(f"Error getting available targets: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get available targets: {str(e)}")

@router.post("/image", response_model=FaceSwapResponse)
async def swap_face_in_image(
    image: UploadFile = File(...),
    target_member_id: str = Form(...),
    blend_factor: float = Form(default=0.7)
):
    """
    Swap faces in an uploaded image with a target MP's face.
    
    Args:
        image: Image file to process
        target_member_id: Target MP member ID for face swapping
        blend_factor: Blending factor for face replacement (0.0-1.0)
        
    Returns:
        Face swap operation results
    """
    try:
        # Validate blend factor
        if not 0.0 <= blend_factor <= 1.0:
            raise HTTPException(status_code=400, detail="Blend factor must be between 0.0 and 1.0")
        
        # Validate file type
        if not image.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="Uploaded file must be an image")
        
        # Create temporary files
        with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as temp_input:
            # Save uploaded image
            content = await image.read()
            temp_input.write(content)
            temp_input_path = temp_input.name
        
        # Create output file path
        with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as temp_output:
            temp_output_path = temp_output.name
        
        try:
            # Perform face swap
            result = face_swap_service.swap_face_in_image(
                temp_input_path, 
                target_member_id, 
                temp_output_path, 
                blend_factor
            )
            
            if not result["success"]:
                raise HTTPException(status_code=400, detail=result.get("error", "Face swap failed"))
            
            # Return success response with output file
            return FaceSwapResponse(
                success=True,
                message="Face swap completed successfully",
                faces_detected=result.get("faces_detected"),
                faces_swapped=result.get("faces_swapped"),
                output_path=temp_output_path,
                target_member_id=target_member_id
            )
            
        finally:
            # Clean up input file
            try:
                os.unlink(temp_input_path)
            except:
                pass
                
    except HTTPException:
        # Clean up output file on error
        try:
            os.unlink(temp_output_path)
        except:
            pass
        raise
    except Exception as e:
        # Clean up output file on error
        try:
            os.unlink(temp_output_path)
        except:
            pass
        logger.error(f"Error in face swap: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Face swap failed: {str(e)}")

@router.get("/image/{output_path}")
async def get_face_swap_result(output_path: str):
    """
    Download a face-swapped image.
    
    Args:
        output_path: Path to the output image file
        
    Returns:
        The face-swapped image file
    """
    try:
        if not os.path.exists(output_path):
            raise HTTPException(status_code=404, detail="Output image not found")
        
        return FileResponse(
            output_path,
            media_type="image/jpeg",
            filename="face_swapped_result.jpg"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error serving face swap result: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to serve image: {str(e)}")

@router.delete("/cleanup/{output_path}")
async def cleanup_face_swap_result(output_path: str):
    """
    Clean up a temporary face swap result file.
    
    Args:
        output_path: Path to the output image file to delete
        
    Returns:
        Cleanup operation result
    """
    try:
        if os.path.exists(output_path):
            os.unlink(output_path)
            return {"success": True, "message": "File cleaned up successfully"}
        else:
            return {"success": True, "message": "File not found, nothing to clean up"}
    except Exception as e:
        logger.error(f"Error cleaning up file: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to clean up file: {str(e)}")

@router.post("/intelligent-swap")
async def intelligent_face_swap(
    image: UploadFile = File(...),
    target_member_id: str = Form(...),
    enhancement_type: str = Form(default="smooth"),
    target_specific: bool = Form(default=True)
):
    """
    Intelligent face swapping that targets specific faces and enhances them.
    
    Args:
        image: Upload file containing the source image
        target_member_id: Target MP member ID to enhance
        enhancement_type: Type of enhancement (smooth, sharpen, cartoon, age, beautify)
        target_specific: If True, only enhance the target MP's face
        
    Returns:
        Face enhancement results
    """
    try:
        # Validate enhancement type
        valid_enhancements = ["smooth", "sharpen", "cartoon", "age", "beautify"]
        if enhancement_type not in valid_enhancements:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid enhancement type. Must be one of: {valid_enhancements}"
            )
        
        # Create temporary file for uploaded image
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as temp_file:
            temp_file.write(await image.read())
            temp_file_path = temp_file.name
        
        # Create output file path
        output_path = tempfile.mktemp(suffix="_enhanced.jpg")
        
        try:
            # Perform intelligent face swapping
            result = intelligent_face_swap_service.swap_target_face_intelligently(
                image_path=temp_file_path,
                target_member_id=target_member_id,
                output_path=output_path,
                enhancement_type=enhancement_type,
                target_specific=target_specific
            )
            
            if not result.get("success"):
                raise HTTPException(status_code=400, detail=result.get("error", "Face enhancement failed"))
            
            return {
                "success": True,
                "message": f"Face enhancement completed successfully",
                "faces_detected": result.get("faces_detected", 0),
                "target_faces_found": result.get("target_faces_found", 0),
                "faces_processed": result.get("faces_processed", 0),
                "enhancement_type": enhancement_type,
                "target_specific": target_specific,
                "target_member_id": target_member_id,
                "output_path": output_path,
                "face_details": result.get("face_details", [])
            }
            
        finally:
            # Clean up temporary input file
            try:
                os.unlink(temp_file_path)
            except:
                pass
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in intelligent face swap: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Intelligent face swap failed: {str(e)}")

@router.post("/analyze-faces")
async def analyze_faces(image: UploadFile = File(...)):
    """
    Analyze faces in an image and provide detailed identification information.
    
    Args:
        image: Upload file containing the source image
        
    Returns:
        Detailed face analysis results
    """
    try:
        # Create temporary file for uploaded image
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as temp_file:
            temp_file.write(await image.read())
            temp_file_path = temp_file.name
        
        try:
            # Perform face analysis
            analysis = intelligent_face_swap_service.create_face_analysis_report(temp_file_path)
            
            if not analysis.get("success"):
                raise HTTPException(status_code=400, detail=analysis.get("error", "Face analysis failed"))
            
            return analysis
            
        finally:
            # Clean up temporary file
            try:
                os.unlink(temp_file_path)
            except:
                pass
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in face analysis: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Face analysis failed: {str(e)}")

@router.get("/health")
async def health_check():
    """
    Health check endpoint for face swap service.
    
    Returns:
        Health status of the face swap service
    """
    try:
        # Test if service is working by checking available targets
        available_faces = face_swap_service.get_available_mp_faces()
        
        return {
            "status": "healthy",
            "available_targets": len(available_faces),
            "service": "FaceSwapService"
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")
