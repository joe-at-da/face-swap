// Hardcoded processing run IDs for evaluation
// Add UUIDs of processing runs to evaluate here
export const EVALUATION_PROCESSING_RUN_IDS: string[] = [
  // Example: "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
  "041e6474-ff82-481f-9353-a3819c0d8c9c",
  "0c271b8b-8752-42b6-9161-ad8a0b168b84",
  "34402e42-fd15-433a-81b5-368bcc091075",
  "37862f0f-3361-4520-8001-e3dd314b0512",
  "37da97b9-ac15-438e-88bc-14549d0b123c",
  "3b8fc9b8-0e60-494e-a0dd-978e6b8a5e9a",
  "404a915e-9929-480a-a38a-8aba0a997bfe",
  "45b3fb18-8def-4437-9c7e-a37f41c94c96",
  "4b893fbf-c68f-4c1a-88eb-268c8ddcb4c9",
  "5a1fddf8-e569-4e29-a1a2-3c8006c09880",
  "6f74ea2b-36ce-4c0b-aee1-5072a3e139ef",
  "746cf7c9-5af3-4a5c-b8bd-53642fd99ead",
  "7497ba5d-3810-4a25-a812-5723b5d8c6ea",
  "82b3b2d1-4193-4855-a9e0-8dc1942c77b1",
  "85ba66a8-627e-4746-9207-7f6673e72e7a",
  "8b860683-030e-4992-93c7-7d778962638e",
  "930dc4ec-b7f3-43c7-93f1-fd80b405961c",
  "936ed701-fe6c-4be0-909d-785820302ef9",
  "94f2ad58-763c-4747-9a4c-cb63bde02d7a",
  "95455bd1-fac7-479f-9238-686cd272bb14",
  "994b98e2-f505-48a5-8afd-5e137772711c",
  "9abb71c0-6ca0-4b07-bf1e-4fbfbf24040e",
  "b0b736a2-1512-4cb1-98d9-337699eaab88",
  "c63eb2c5-eea1-42bb-b0bb-4c7f5b7d9021",
  "cc0b8ac7-4dcb-474a-9d55-71911f2fc129",
  "ce79e471-d9b6-43d7-86ea-5999e70c2c09",
  "d56dcd91-cb3d-40c4-97e3-cb4271029b96",
  "e3648bd5-06ae-4bef-b4f8-f7e93f383447",
  "e5af742c-9e5c-40f1-848b-351b0a66659a",
  "e74c7ad5-82fc-4c80-9750-8da5ffc2f9d2",
  "ead7280c-3725-4907-b1c3-352a3c964f63",
  "eb18277f-d85c-4c5e-a6eb-b7e3037da29d",
  "ec3d5ff8-ff0d-47ac-b5ec-3a9816f22392",
  "ed4fa719-262e-4571-b2f1-ff45e4743790",
  "eef76bd6-550b-4669-9649-4fbe150e2531",
  "f6aa20b4-333c-4d54-bdd4-32e9963fbd24",
];

// Lock timeout in minutes - segments locked longer than this can be taken by others
export const LOCK_TIMEOUT_MINUTES = 2;

// Error reason options with labels and descriptions
export const ERROR_REASONS = {
  wrong_speaker_detected: {
    label: "Wrong Speaker Detected",
    description:
      "The face detection picked a different person in the video, not the actual speaker",
  },
  wrong_mp_matched: {
    label: "Wrong MP Matched",
    description:
      "The correct speaker was detected, but matched to the wrong MP's portrait",
  },
} as const;

export type ErrorReason = keyof typeof ERROR_REASONS;

// Types for segment evaluation
export interface SpeakerFace {
  id: string;
  s3Url: string;
  faceIndex: number;
  qualityScore: number | null;
}

export interface MPPortrait {
  id: string;
  imageUrl: string;
  fallbackUrl: string | null;
  cropType: number;
  isPrimary: boolean | null;
}

export interface EvaluableSegment {
  segmentId: string;
  clipUrl: string | null;
  thumbnailUrl: string | null;
  memberId: number;
  memberName: string | null;
  partyName: string | null;
  constituencyName: string | null;
  transcript: string | null;
  speakerFaces: SpeakerFace[];
  mpPortraits: MPPortrait[];
  processingRunId: string;
  eventUrl: string | null;
  startSeconds: number | null;
  sessionStartTime: string | null;
}

export interface EvaluationStats {
  totalSegments: number;
  evaluatedCount: number;
  correctCount: number;
  wrongSpeakerCount: number;
  wrongMpCount: number;
  remainingCount: number;
  accuracyPercentage: number;
}
