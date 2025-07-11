#!/bin/bash
# Script to patch the ParliamentMemberMatcher in the Docker container to improve speaker diversity

# Set up logging
LOG_FILE="patch_matcher_diversity_$(date +%Y%m%d_%H%M%S).log"
echo "Starting matcher diversity patch at $(date)" | tee -a $LOG_FILE

# Define the Docker container name
CONTAINER_NAME="the-mp-app-1"

# Check if the container is running
echo "Checking if Docker container $CONTAINER_NAME is running..." | tee -a $LOG_FILE
if ! docker ps | grep -q "$CONTAINER_NAME"; then
    echo "Error: Docker container $CONTAINER_NAME is not running" | tee -a $LOG_FILE
    exit 1
fi

# Create the patch file
echo "Creating patch file for ParliamentMemberMatcher..." | tee -a $LOG_FILE
cat > /tmp/matcher_diversity_patch.py << 'EOF'
"""
Patch for ParliamentMemberMatcher to improve speaker diversity.
This patch adds cooldown and diversity-promoting logic to the matcher.
"""
import os
import json
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Define the path to the matcher file in the Docker container
MATCHER_PATH = "/app/backend/services/recognition/member_matching/matcher.py"

# Check if the file exists
if not os.path.exists(MATCHER_PATH):
    logger.error(f"Matcher file not found at {MATCHER_PATH}")
    exit(1)

# Read the original file
with open(MATCHER_PATH, 'r') as f:
    content = f.read()

# Add member cooldown tracking to __init__ method
if "self.member_match_history = {}" not in content:
    logger.info("Adding member cooldown tracking to __init__ method")
    init_pattern = "        # Initialize member data\n        self.members = []\n        self.member_embeddings = {}\n        self.member_cache_file = os.path.join(self.cache_dir, \"parliament_members.json\")\n"
    cooldown_code = "        # Initialize member cooldown tracking for diversity promotion\n        self.member_match_history = {}\n        self.member_match_counts = {}\n        self.last_matched_member_id = None\n        self.consecutive_same_matches = 0\n"
    content = content.replace(init_pattern, init_pattern + cooldown_code)

# Replace the _match_face_to_member method with our improved version
match_method_start = "    def _match_face_to_member(self, face_data, confidence_threshold=0.5, house=None):"
match_method_end = "        return {'matched': False}"

# Find the start and end positions of the method
start_pos = content.find(match_method_start)
if start_pos == -1:
    logger.error("Could not find _match_face_to_member method in the file")
    exit(1)

# Find the end of the method by looking for the next method definition
next_method_pos = content.find("    def ", start_pos + len(match_method_start))
if next_method_pos == -1:
    logger.error("Could not find the end of _match_face_to_member method")
    exit(1)

# Extract the original method
original_method = content[start_pos:next_method_pos]

# Create the improved method
improved_method = """    def _match_face_to_member(self, face_data, confidence_threshold=0.5, house=None):
        # Get the face embedding
        face_embedding = face_data.get('embedding')
        if face_embedding is None:
            logger.error("No embedding found in face data")
            return {'matched': False}
        
        # Ensure face embedding is normalized
        if not isinstance(face_embedding, np.ndarray):
            face_embedding = np.array(face_embedding)
        face_embedding = normalize_embedding(face_embedding)
        
        # Find the best match and track second best for confidence gap analysis
        best_match = None
        best_confidence = 0
        second_best_confidence = 0
        
        # Track all matches for debugging
        all_matches = []
        original_confidences = {}
        adjusted_confidences = {}
        
        # Get current timestamp for cooldown calculations
        current_time = datetime.now().timestamp()
        
        # Process all members
        for member in self.members:
            member_id = str(member.get('member_id'))
            member_house = member.get('house_id')
            member_name = member.get('display_name', 'Unknown')
            
            # Skip members from the wrong house if house is specified
            if house is not None and str(member_house) != str(house):
                continue
            
            # Skip if no embedding
            if member_id not in self.member_embeddings:
                continue
            
            # Get the member embedding
            member_embedding = self.member_embeddings[member_id].get('embedding')
            if member_embedding is None:
                continue
            
            # Ensure member embedding is normalized
            if not isinstance(member_embedding, np.ndarray):
                member_embedding = np.array(member_embedding)
            member_embedding = normalize_embedding(member_embedding)
            
            # Compute similarity directly with normalized embeddings
            original_confidence = float(np.dot(face_embedding, member_embedding))
            original_confidences[member_id] = original_confidence
            
            # Apply cooldown and diversity adjustments
            adjusted_confidence = original_confidence
            cooldown_factor = 1.0
            diversity_boost = 0.0
            
            # Apply cooldown if this member was recently matched
            if member_id in self.member_match_history:
                last_match_time = self.member_match_history[member_id]
                time_since_last_match = current_time - last_match_time
                
                # Cooldown effect decreases over time (30 seconds cooldown period)
                if time_since_last_match < 30:
                    cooldown_factor = 0.7 + (0.3 * (time_since_last_match / 30))
                    adjusted_confidence *= cooldown_factor
            
            # Apply diversity boost for members who haven't been matched often
            match_count = self.member_match_counts.get(member_id, 0)
            if match_count == 0:
                # Significant boost for never-matched members
                diversity_boost = 0.05
            elif match_count < 3:
                # Smaller boost for rarely-matched members
                diversity_boost = 0.03
            
            # Apply extra penalty if this is the same as the last matched member
            if member_id == self.last_matched_member_id and self.consecutive_same_matches > 2:
                # Increasing penalty for consecutive matches of the same member
                repeat_penalty = min(0.1 * (self.consecutive_same_matches - 2), 0.3)
                adjusted_confidence *= (1.0 - repeat_penalty)
            
            # Apply the diversity boost
            adjusted_confidence += diversity_boost
            
            # Store the adjusted confidence
            adjusted_confidences[member_id] = adjusted_confidence
            
            # Add to all matches for debugging with both original and adjusted confidence
            all_matches.append({
                'member_id': member_id,
                'name': member_name,
                'original_confidence': original_confidence,
                'adjusted_confidence': adjusted_confidence,
                'cooldown_factor': cooldown_factor,
                'diversity_boost': diversity_boost,
                'confidence': adjusted_confidence  # Use adjusted confidence for sorting
            })
            
            # Update best match if this is better (using adjusted confidence)
            if adjusted_confidence > best_confidence:
                # Current best becomes second best
                second_best_confidence = best_confidence
                # Update best
                best_confidence = adjusted_confidence
                best_match = {
                    'member_id': member_id,
                    'name': member_name,
                    'confidence': original_confidence,  # Store original confidence
                    'adjusted_confidence': adjusted_confidence  # Also store adjusted confidence
                }
            # Update second best if this is better than current second best but not better than best
            elif adjusted_confidence > second_best_confidence:
                second_best_confidence = adjusted_confidence
        
        # Sort all matches for debugging (by adjusted confidence)
        all_matches.sort(key=lambda x: x['confidence'], reverse=True)
        
        # Log top 5 matches for debugging with adjustment details
        if all_matches:
            logger.info(f"Top 5 matches (with diversity adjustments):")
            for i, match in enumerate(all_matches[:5]):
                logger.info(f"{i+1}. {match['name']} (ID: {match['member_id']}): "
                          f"orig={match['original_confidence']:.4f}, "
                          f"adj={match['adjusted_confidence']:.4f}, "
                          f"cooldown={match['cooldown_factor']:.2f}, "
                          f"boost={match['diversity_boost']:.2f}")
        
        # Calculate confidence gap between best and second best (using adjusted confidences)
        confidence_gap = best_confidence - second_best_confidence
        
        # Check if the best match is above the threshold and has sufficient gap
        min_gap = 0.1  # Require at least 0.1 gap for reliable matching
        if best_match and best_match['adjusted_confidence'] >= confidence_threshold:
            # Add confidence gap to the result
            best_match['matched'] = True
            best_match['confidence_gap'] = confidence_gap
            
            # Update match history for this member
            member_id = best_match['member_id']
            self.member_match_history[member_id] = current_time
            self.member_match_counts[member_id] = self.member_match_counts.get(member_id, 0) + 1
            
            # Track consecutive matches of the same member
            if member_id == self.last_matched_member_id:
                self.consecutive_same_matches += 1
                logger.info(f"Consecutive match #{self.consecutive_same_matches} for member {member_id}")
            else:
                self.consecutive_same_matches = 1
                self.last_matched_member_id = member_id
            
            # Log match details with confidence gap and adjustments
            logger.info(f"Matched {best_match['name']} with original confidence {best_match['confidence']:.4f}, "
                      f"adjusted to {best_match['adjusted_confidence']:.4f} "
                      f"(threshold: {confidence_threshold:.4f}, gap: {confidence_gap:.4f})")
            
            # Log diversity statistics
            total_matches = sum(self.member_match_counts.values())
            unique_members = len(self.member_match_counts)
            logger.info(f"Diversity stats: {unique_members} unique members matched out of {total_matches} total matches")
            
            # If gap is too small, log a warning but still return the match
            if confidence_gap < min_gap:
                logger.warning(f"Low confidence gap ({confidence_gap:.4f}) for match to {best_match['name']}. "
                             f"Second best confidence: {second_best_confidence:.4f}")
            
            return best_match
        
        # If no match found, return transparent error
        if not best_match:
            logger.warning(f"No match found above threshold {confidence_threshold}")
            return {'matched': False}
        
        logger.info(f"Best match {best_match['name']} with adjusted confidence {best_match['adjusted_confidence']:.4f} below threshold {confidence_threshold}")
        return {'matched': False}"""

# Replace the original method with the improved one
content = content.replace(original_method, improved_method)

# Write the modified content back to the file
with open(MATCHER_PATH, 'w') as f:
    f.write(content)

logger.info(f"Successfully patched {MATCHER_PATH} with diversity-promoting logic")

# Create a backup of the original file
backup_path = f"{MATCHER_PATH}.bak"
with open(backup_path, 'w') as f:
    f.write(original_method)
logger.info(f"Created backup of original method at {backup_path}")

print("Patch applied successfully!")
EOF

# Copy the patch file to the Docker container
echo "Copying patch file to Docker container..." | tee -a $LOG_FILE
docker cp /tmp/matcher_diversity_patch.py $CONTAINER_NAME:/app/matcher_diversity_patch.py

# Run the patch script in the Docker container
echo "Running patch script in Docker container..." | tee -a $LOG_FILE
docker exec $CONTAINER_NAME python /app/matcher_diversity_patch.py | tee -a $LOG_FILE

# Clean up
rm /tmp/matcher_diversity_patch.py

echo "Patch complete. Now run the Docker test script to verify the improvements." | tee -a $LOG_FILE
echo "You can run: ./backend/scripts/docker_test_speaker_attribution.sh" | tee -a $LOG_FILE
