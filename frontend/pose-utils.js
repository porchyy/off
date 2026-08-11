/**
 * Pose scoring utility module.
 * Evaluates MediaPipe pose landmarks for the fixed frontal desk camera.
 */

export function isPostureRisk(score, threshold, poorPostureMs, riskSeconds) {
  if (score >= threshold) return false;
  const delayMs = Math.max(0, Number(riskSeconds) || 0) * 1000;
  return score < threshold - 10 || poorPostureMs >= delayMs;
}

export function scorePose(landmarks) {
  if (!landmarks || landmarks.length < 13) return null;

  const nose = landmarks[0];
  const leftEar = landmarks[7] || nose;
  const rightEar = landmarks[8] || nose;
  const leftShoulder = landmarks[11];
  const rightShoulder = landmarks[12];
  if (![nose, leftEar, rightEar, leftShoulder, rightShoulder].every(point => point && point.visibility > 0.45)) return null;

  const midEar = {
    x: (leftEar.x + rightEar.x) / 2,
    y: (leftEar.y + rightEar.y) / 2
  };
  const midShoulder = {
    x: (leftShoulder.x + rightShoulder.x) / 2,
    y: (leftShoulder.y + rightShoulder.y) / 2
  };

  // This camera is fixed in front of the seated user. Use only X/Y landmark
  // positions: MediaPipe's relative Z changes with small camera offsets and
  // made normal shoulders falsely appear 50-60 degrees uneven. This view
  // assesses head/shoulder alignment, not physical spinal curvature.
  const head = {
    x: (nose.x + midEar.x) / 2,
    y: (nose.y + midEar.y) / 2
  };
  const vertical = Math.max(0.001, midShoulder.y - head.y);
  const degrees = 180 / Math.PI;
  const headOffset = Math.atan2(Math.abs(head.x - midShoulder.x), vertical) * degrees;
  const headRoll = Math.atan2(Math.abs(leftEar.y - rightEar.y), Math.max(0.001, Math.abs(leftEar.x - rightEar.x))) * degrees;
  const neck = Math.hypot(headOffset, headRoll);
  const shoulders = Math.atan2(
    Math.abs(leftShoulder.y - rightShoulder.y),
    Math.max(0.001, Math.abs(leftShoulder.x - rightShoulder.x))
  ) * degrees;
  // The Pi adds a calibrated signed lean trend to this value. Browser-only
  // analysis has no shared per-person baseline, so it intentionally reports 0.
  const torso = 0;

  const neckPenalty = Math.min(30, Math.max(0, neck - 12) * 1.2);
  const shoulderPenalty = Math.min(30, Math.max(0, shoulders - 10) * 1.0);
  const forwardLeanPenalty = Math.min(35, Math.max(0, torso - 6) * 1.4);
  const backwardLeanPenalty = Math.min(20, Math.max(0, -torso - 18) * 0.8);
  const score = Math.max(0, Math.min(100, 100 - neckPenalty - shoulderPenalty - forwardLeanPenalty - backwardLeanPenalty));

  return { neck, shoulders, torso, score };
}
