/**
 * Pose scoring utility module.
 * Evaluates MediaPipe pose landmarks and returns posture metrics.
 */

export function isPostureRisk(score, threshold, poorPostureMs, riskSeconds) {
  if (score >= threshold) return false;
  const delayMs = Math.max(0, Number(riskSeconds) || 0) * 1000;
  return score < threshold - 10 || poorPostureMs >= delayMs;
}

export function scorePose(landmarks) {
  if (!landmarks || landmarks.length < 13) return null;

  const nose = landmarks[0];
  const le = landmarks[7] || nose, re = landmarks[8] || nose; // Fallback to nose if ears missing
  const ls = landmarks[11], rs = landmarks[12];

  if (![nose, le, re, ls, rs].every(x => x && x.visibility > 0.45)) return null;

  // Midpoints (x, y, z)
  const midEar = {
    x: (le.x + re.x) / 2,
    y: (le.y + re.y) / 2,
    z: ((le.z || 0) + (re.z || 0)) / 2
  };
  const midShoulder = {
    x: (ls.x + rs.x) / 2,
    y: (ls.y + rs.y) / 2,
    z: ((ls.z || 0) + (rs.z || 0)) / 2
  };
  // This is intentionally upper-body only: desks hide hips and legs in a
  // front-facing seated camera. "torso" is a hunch/rotation proxy, not a
  // measurement of physical spinal curvature from a single RGB camera.
  const vertical = Math.max(0.001, midShoulder.y - midEar.y);
  const shoulderWidth = Math.max(0.001, Math.hypot(ls.x - rs.x, ls.y - rs.y));
  const degrees = 180 / Math.PI;
  const neckForward = Math.atan2(Math.abs(midEar.z - midShoulder.z), vertical) * degrees;
  const neckSideTilt = Math.atan2(Math.abs(midEar.x - midShoulder.x), vertical) * degrees;
  let neck = Math.hypot(neckForward, neckSideTilt);
  const shoulderTilt = Math.atan2(Math.abs(ls.y - rs.y), Math.max(0.001, Math.abs(ls.x - rs.x))) * degrees;
  const shoulderDepth = Math.atan2(Math.abs((ls.z || 0) - (rs.z || 0)), shoulderWidth) * degrees;
  let shoulders = Math.hypot(shoulderTilt, shoulderDepth);
  let torso = neckForward * 0.7 + shoulderDepth * 0.3;

  // Graceful 2-D fallback for a webcam or test landmarks without depth.
  if (Math.abs(midEar.z - midShoulder.z) < 0.0001 && Math.abs((ls.z || 0) - (rs.z || 0)) < 0.0001) {
    neck = Math.abs(Math.atan2(nose.x - midShoulder.x, Math.max(0.001, midShoulder.y - nose.y)) * degrees);
    shoulders = shoulderTilt;
    torso = neck * 0.7 + shoulders * 0.3;
  }

  // Camera roll and a small body rotation can make the shoulder angle noisy.
  // Cap each contribution so one landmark estimate cannot force 0/100.
  const neckPenalty = Math.min(30, Math.max(0, neck - 20) * 1.0);
  const shoulderPenalty = Math.min(35, Math.max(0, shoulders - 20) * 0.7);
  const torsoPenalty = Math.min(30, Math.max(0, torso - 25) * 0.7);

  const score = Math.max(0, Math.min(100, 100 - neckPenalty - shoulderPenalty - torsoPenalty));

  return { neck, shoulders, torso, score };
}
