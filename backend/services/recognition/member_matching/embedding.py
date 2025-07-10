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

def normalize_embedding(embedding: np.ndarray) -> np.ndarray:
    """
    Normalize an embedding to unit length
    
    Args:
        embedding: Embedding to normalize
        
    Returns:
        Normalized embedding
    """
    # Check for NaN or Inf values
    if np.isnan(embedding).any() or np.isinf(embedding).any():
        embedding = np.nan_to_num(embedding)
    
    # Compute the norm
    norm = np.linalg.norm(embedding)
    
    # Avoid division by zero
    if norm < 1e-10:
        return np.zeros_like(embedding)
    
    # Normalize
    return embedding / norm

def compute_similarity(embedding1, embedding2):
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
        if isinstance(embedding1, dict) and 'embedding' in embedding1:
            embedding1 = embedding1['embedding']
        if isinstance(embedding2, dict) and 'embedding' in embedding2:
            embedding2 = embedding2['embedding']
        
        # Convert to numpy arrays if they aren't already
        if not isinstance(embedding1, np.ndarray):
            embedding1 = np.array(embedding1)
        if not isinstance(embedding2, np.ndarray):
            embedding2 = np.array(embedding2)
        
        # Normalize the embeddings
        embedding1 = normalize_embedding(embedding1)
        embedding2 = normalize_embedding(embedding2)
        
        # Compute cosine similarity
        similarity = np.dot(embedding1, embedding2)
        
        # Special debug for Darren Jones
        if similarity > 0.9:
            logger.info(f"High similarity detected: {similarity:.6f}")
            
        return float(similarity)
    except Exception as e:
        logger.error(f"Error computing similarity: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return 0.0
