// Re-export constants from pipeline-evaluation for consistency
export {
  EVALUATION_PROCESSING_RUN_IDS,
  LOCK_TIMEOUT_MINUTES,
} from "@/app/(privatePages)/dashboard/pipeline-evaluation/constants";

// Speaker face data with selection state
export interface SpeakerFace {
  id: string;
  s3Url: string;
  faceIndex: number;
  qualityScore: number | null;
  confidence: number | null;
  isFrontal: boolean | null;
  occlusionScore: number | null;
  faceSize: number | null;
}

// MP candidate with portraits and similarity score
export interface MPCandidate {
  memberId: number;
  displayName: string;
  partyName: string | null;
  partyAbbreviation: string;
  constituencyName: string | null;
  similarity: number; // 0-1 cosine similarity score
  portraits: {
    id: string;
    imageUrl: string;
    fallbackUrl: string | null;
    isPrimary: boolean | null;
  }[];
}

// Selected MP data (without similarity - used when MP is selected manually or via AI)
export interface SelectedMPData {
  memberId: number;
  displayName: string;
  partyName: string | null;
  partyAbbreviation: string;
  constituencyName: string | null;
  portraits: {
    id: string;
    imageUrl: string;
    fallbackUrl: string | null;
    isPrimary: boolean | null;
  }[];
}

// Complete segment data for evaluation
export interface UnidentifiedSegment {
  segmentId: string;
  processingRunId: string;
  clipUrl: string | null;
  verticalClipUrl: string | null;
  thumbnailUrl: string | null;
  transcript: string | null;
  durationSeconds: number | null;
  speaker: string | null;
  sessionDate: string | null;
  sessionStartTime: string | null;
  startSeconds: number | null;
  endSeconds: number | null;
  eventUrl: string | null;
  speakerFaces: SpeakerFace[];
  topCandidates: MPCandidate[];
}

// Stats for portrait collection progress
export interface PortraitCollectionStats {
  totalUnidentified: number;
  evaluatedCount: number;
  portraitsAddedCount: number;
  remainingCount: number;
  activeEvaluators: number;
  completionPercentage: number;
}

// API request types
export interface SubmitIdentificationRequest {
  segmentId: string;
  selectedMemberId: number;
  selectedFaceIndices: number[];
  rejectedFaceIndices: number[];
}

export interface SubmitIdentificationResponse {
  portraitIds: string[];
  portraitCount: number;
}

export interface NextSegmentResponse {
  segment: UnidentifiedSegment | null;
  complete: boolean;
}

// Skip reason types
export type SkipReason =
  | "bad_quality"
  | "no_speaker_faces"
  | "already_added_similar_pictures";

export const SKIP_REASONS = {
  bad_quality: {
    label: "All faces are bad quality",
    description:
      "The detected faces are too blurry, dark, or otherwise unusable for identification",
  },
  no_speaker_faces: {
    label: "No faces are of the speaker",
    description:
      "None of the detected faces belong to the person speaking in this segment",
  },
  already_added_similar_pictures: {
    label: "Already added similar pictures to this MP",
    description:
      "We already have similar pictures of this MP in our collection, so this segment can be skipped",
  },
} as const;

export interface SkipSegmentRequest {
  segmentId: string;
  skipReason: SkipReason;
}

export interface SkipSegmentResponse {
  success: boolean;
  segmentId: string;
  skipReason: SkipReason;
}
