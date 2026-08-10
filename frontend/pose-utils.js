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
  if (!landmarks || landmarks.length < 25) return null;

  const nose = landmarks[0];
  const le = landmarks[7] || nose, re = landmarks[8] || nose; // Fallback to nose if ears missing
  const ls = landmarks[11], rs = landmarks[12];
  // MediaPipe's hip joints are the closest stable landmarks to the waist
  // line; use them as a waist reference without requiring knees or feet.
  const lw = landmarks[23], rw = landmarks[24];

  if (![nose, le, re, ls, rs, lw, rw].every(x => x && x.visibility > 0.45)) return null;

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
  const midWaist = {
    x: (lw.x + rw.x) / 2,
    y: (lw.y + rw.y) / 2,
    z: ((lw.z || 0) + (rw.z || 0)) / 2
  };

  // 1. Neck metric (forward head and side tilt).  Z gets smaller toward the
  // camera, so leave a natural head-depth allowance before scoring slouching.
  const dxNeck = midEar.x - midShoulder.x;
  const neckHeight = Math.max(0.001, Math.abs(midShoulder.y - midEar.y));
  const shoulderWidth = Math.max(0.001, Math.hypot(rs.x - ls.x, rs.y - ls.y));
  const forwardHeadDepth = Math.max(0, midShoulder.z - midEar.z - shoulderWidth * 0.45);

  const neckPitch = Math.atan2(forwardHeadDepth, neckHeight) * 180 / Math.PI;
  const neckRoll = Math.atan2(Math.abs(dxNeck), neckHeight) * 180 / Math.PI;
  // Combine 3D pitch and 2D tilt for comprehensive neck score
  let neck = Math.sqrt(neckPitch * neckPitch + neckRoll * neckRoll);

  // 2. Shoulder level.
  const shoulderRoll = Math.atan2(Math.abs(ls.y - rs.y), Math.max(0.001, Math.abs(ls.x - rs.x))) * 180 / Math.PI;
  let shoulders = shoulderRoll;

  // 3. Shoulder-to-waist alignment: forward shoulder depth and sideways lean.
  const dxTorso = midShoulder.x - midWaist.x;
  const torsoVertical = Math.max(0.001, Math.abs(midWaist.y - midShoulder.y));
  const torsoHeight = Math.hypot(dxTorso, torsoVertical);
  const forwardTorsoDepth = Math.max(0, midWaist.z - midShoulder.z - torsoHeight * 0.15);

  const torsoRoll = Math.atan2(Math.abs(dxTorso), torsoVertical) * 180 / Math.PI;
  const torsoPitch = Math.atan2(forwardTorsoDepth, torsoHeight) * 180 / Math.PI;
  let torso = Math.hypot(torsoRoll, torsoPitch);

  // To maintain backward compatibility with tests/models if Z is 0 (2D only)
  if (Math.abs(midShoulder.z - midEar.z) < 0.0001 && Math.abs(midShoulder.z - midWaist.z) < 0.0001) {
      neck = Math.abs(Math.atan2(nose.x - midShoulder.x, Math.max(0.001, Math.abs(midShoulder.y - nose.y))) * 180 / Math.PI);
      shoulders = shoulderRoll;
      torso = torsoRoll;
  }

  const neckPenalty = Math.max(0, neck - 12) * 1.5;
  const shoulderPenalty = Math.max(0, shoulders - 6) * 1.5;
  const torsoPenalty = Math.max(0, torso - 8) * 1.8;

  const score = Math.max(0, Math.min(100, 100 - neckPenalty - shoulderPenalty - torsoPenalty));

  return { neck, shoulders, torso, score };
}
