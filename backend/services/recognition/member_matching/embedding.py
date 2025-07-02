"""
Module for handling face embeddings and similarity calculations
"""
import logging
import numpy as np
from typing import Dict, Any, Union, List

logger = logging.getLogger(__name__)

def extract_embedding(embedding_data: Union[Dict[str, Any], List[float], np.ndarray]) -> np.ndarray:
    """
    Extract embedding from various formats
    
    Args:
        embedding_data: Embedding data in various formats (dict, list, numpy array)
        
    Returns:
        Numpy array containing the embedding
    """
    # Extract embeddings if they are dictionaries
    if isinstance(embedding_data, dict) and 'embedding' in embedding_data:
        embedding_data = embedding_data['embedding']
    
    # Ensure embeddings are numpy arrays
    embedding = np.array(embedding_data)
    
    # Ensure embeddings are flattened to 1D arrays
    embedding = embedding.flatten()
    
    return embedding

def compute_similarity(embedding1: Union[Dict[str, Any], List[float], np.ndarray], 
                       embedding2: Union[Dict[str, Any], List[float], np.ndarray]) -> float:
    """
    Compute similarity between two face embeddings
    
    Args:
        embedding1: First embedding (numpy array, list, or dict with 'embedding' key)
        embedding2: Second embedding (numpy array, list, or dict with 'embedding' key)
        
    Returns:
        Similarity score between 0 and 1
    """
    try:
        # Extract and convert embeddings
        embedding1_array = extract_embedding(embedding1)
        embedding2_array = extract_embedding(embedding2)
        
        # Check embedding dimensions
        if embedding1_array.size == 0 or embedding2_array.size == 0:
            logger.error(f"Empty embedding detected: embedding1 size={embedding1_array.size}, embedding2 size={embedding2_array.size}")
            return 0.0
        
        # Log embedding details for debugging
        try:
            logger.debug(f"Embedding1: shape={embedding1_array.shape}, min={np.min(embedding1_array):.4f}, max={np.max(embedding1_array):.4f}")
            logger.debug(f"Embedding2: shape={embedding2_array.shape}, min={np.min(embedding2_array):.4f}, max={np.max(embedding2_array):.4f}")
        except Exception as debug_error:
            logger.debug(f"Could not log embedding details: {str(debug_error)}")
        
        # Handle embeddings from different sources (dlib vs OpenCV)
        # If sizes don't match, we need to adapt the comparison strategy
        if embedding1_array.size != embedding2_array.size:
            logger.warning(f"Embedding size mismatch: {embedding1_array.size} vs {embedding2_array.size}")
            
            # If one is 128 (dlib) and the other is different (likely OpenCV), 
            # we need to use a different comparison approach
            if embedding1_array.size == 128 or embedding2_array.size == 128:
                logger.info("Detected potential dlib vs OpenCV embedding comparison")
                
                # For mismatched embedding types, we'll use a lower threshold
                # and normalize each separately before computing similarity on the 
                # first min(size1, size2) dimensions
                min_size = min(embedding1_array.size, embedding2_array.size)
                embedding1_array = embedding1_array[:min_size]
                embedding2_array = embedding2_array[:min_size]
                logger.info(f"Using first {min_size} dimensions for comparison")
            else:
                logger.error(f"Cannot compare embeddings with incompatible sizes: {embedding1_array.size} vs {embedding2_array.size}")
                return 0.0
        
        # Normalize the embeddings
        norm1 = np.linalg.norm(embedding1_array)
        norm2 = np.linalg.norm(embedding2_array)
        
        if norm1 < 1e-10 or norm2 < 1e-10:
            logger.warning("Near-zero norm detected in embedding")
            return 0.0
            
        embedding1_array = embedding1_array / norm1
        embedding2_array = embedding2_array / norm2
        
        # Compute cosine similarity
        similarity = np.dot(embedding1_array, embedding2_array)
        
        # Adjust similarity score for cross-model comparisons
        # Empirically, dlib vs OpenCV comparisons tend to have lower similarity scores
        # even for the same face, so we apply a small boost to compensate
        if embedding1_array.size != embedding2_array.size:
            similarity = min(1.0, similarity * 1.2)  # Apply a 20% boost, capped at 1.0
            
        return float(similarity)
    except Exception as e:
        logger.error(f"Error computing similarity: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return 0.0
