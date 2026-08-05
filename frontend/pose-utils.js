/**
 * Pose scoring utility module.
 * Evaluates MediaPipe pose landmarks and returns posture metrics.
 */

export function scorePose(landmarks) {
  if (!landmarks || landmarks.length < 25) return null;

  const nose = landmarks[0];
  const le = landmarks[7] || nose, re = landmarks[8] || nose; // Fallback to nose if ears missing
  const ls = landmarks[11], rs = landmarks[12];
  const lh = landmarks[23], rh = landmarks[24];

  if (![nose, le, re, ls, rs, lh, rh].every(x => x && x.visibility > 0.45)) return null;

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
  const midHip = {
    x: (lh.x + rh.x) / 2,
    y: (lh.y + rh.y) / 2,
    z: ((lh.z || 0) + (rh.z || 0)) / 2
  };

  // 1. Neck metric (Forward Head Posture & 2D Tilt)
  const dxNeck = midEar.x - midShoulder.x;
  const dyNeck = midShoulder.y - midEar.y;
  // MediaPipe Z is relative to hips. If head is forward, Z is significantly smaller (more negative)
  const dzNeck = midEar.z - midShoulder.z;

  const neckPitch = Math.atan2(Math.abs(dzNeck), Math.max(0.001, dyNeck)) * 180 / Math.PI;
  const neckRoll = Math.atan2(Math.abs(dxNeck), Math.max(0.001, dyNeck)) * 180 / Math.PI;
  // Combine 3D pitch and 2D tilt for comprehensive neck score
  let neck = Math.sqrt(neckPitch * neckPitch + neckRoll * neckRoll);

  // 2. Shoulders metric (Imbalance and Rounding)
  const shoulderRoll = Math.abs(ls.y - rs.y) * 100; // Y imbalance (0-10)
  const dzShoulders = midShoulder.z - midHip.z;
  const dyShoulders = midHip.y - midShoulder.y;
  // Shoulder pitch detects slouching forward
  const shoulderPitch = Math.atan2(Math.abs(dzShoulders), Math.max(0.001, dyShoulders)) * 180 / Math.PI;
  let shoulders = shoulderRoll * 1.2 + shoulderPitch * 0.8;

  // 3. Torso metric (Leaning back/forward or sideways)
  const dxTorso = midShoulder.x - midHip.x;
  const dyTorso = midHip.y - midShoulder.y;
  const dzTorso = midShoulder.z - midHip.z;

  const torsoRoll = Math.atan2(Math.abs(dxTorso), Math.max(0.001, dyTorso)) * 180 / Math.PI;
  const torsoPitch = Math.atan2(Math.abs(dzTorso), Math.max(0.001, dyTorso)) * 180 / Math.PI;
  let torso = Math.sqrt(torsoRoll * torsoRoll + torsoPitch * torsoPitch);

  // To maintain backward compatibility with tests/models if Z is 0 (2D only)
  if (Math.abs(dzNeck) < 0.0001 && Math.abs(dzShoulders) < 0.0001) {
      neck = Math.abs(Math.atan2(nose.x - midShoulder.x, Math.max(0.001, midShoulder.y - nose.y)) * 180 / Math.PI);
      shoulders = Math.abs(ls.y - rs.y) * 100;
      torso = Math.abs(Math.atan2(midShoulder.x - midHip.x, Math.max(0.001, midHip.y - midShoulder.y)) * 180 / Math.PI);
  }

  // Strict Scoring
  const neckPenalty = Math.max(0, neck - 10) * 2.5;
  const shoulderPenalty = Math.max(0, shoulders - 5) * 2.0;
  const torsoPenalty = Math.max(0, torso - 8) * 1.8;

  const score = Math.max(0, Math.min(100, 100 - neckPenalty - shoulderPenalty - torsoPenalty));

  return { neck, shoulders, torso, score };
}
