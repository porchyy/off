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
  const ls = landmarks[11], rs = landmarks[12];
  if (![nose, ls, rs].every(x => x && x.visibility > 0.45)) return null;

  const ears = [landmarks[7], landmarks[8]].filter(point => point && point.visibility > 0.45);
  const headPoints = ears.length ? ears : [nose];

  // Head and shoulder midpoints.  The lower body is intentionally not used:
  // this keeps scoring available when the camera only sees a seated upper body.
  const head = {
    x: headPoints.reduce((sum, point) => sum + point.x, 0) / headPoints.length,
    y: headPoints.reduce((sum, point) => sum + point.y, 0) / headPoints.length,
    z: headPoints.reduce((sum, point) => sum + (point.z || 0), 0) / headPoints.length
  };
  const midShoulder = {
    x: (ls.x + rs.x) / 2,
    y: (ls.y + rs.y) / 2,
    z: ((ls.z || 0) + (rs.z || 0)) / 2
  };
  // 1. Neck metric (forward head and side tilt).
  const dxNeck = head.x - midShoulder.x;
  const dyNeck = midShoulder.y - head.y;
  const dzNeck = head.z - midShoulder.z;

  const neckPitch = Math.atan2(Math.abs(dzNeck), Math.max(0.001, dyNeck)) * 180 / Math.PI;
  const neckRoll = Math.atan2(Math.abs(dxNeck), Math.max(0.001, dyNeck)) * 180 / Math.PI;
  let neck = Math.hypot(neckPitch, neckRoll);

  // 2. Shoulder alignment.  Use angles, not screen distances, so the same
  // posture gets a comparable result at different camera distances.
  const dxShoulder = rs.x - ls.x;
  const dyShoulder = rs.y - ls.y;
  const dzShoulder = (rs.z || 0) - (ls.z || 0);
  const shoulderRoll = Math.atan2(Math.abs(dyShoulder), Math.max(0.001, Math.abs(dxShoulder))) * 180 / Math.PI;
  const shoulderDepth = Math.atan2(Math.abs(dzShoulder), Math.max(0.001, Math.hypot(dxShoulder, dyShoulder))) * 180 / Math.PI;
  const shoulders = shoulderRoll;
  let upper_body = Math.hypot(shoulderRoll, shoulderDepth);

  // 2D fallback for MediaPipe outputs that do not contain reliable depth.
  if (Math.abs(dzNeck) < 0.0001 && Math.abs(dzShoulder) < 0.0001) {
      neck = Math.abs(Math.atan2(head.x - midShoulder.x, Math.max(0.001, midShoulder.y - head.y)) * 180 / Math.PI);
      upper_body = shoulderRoll;
  }

  const neckPenalty = Math.max(0, neck - 8) * 2.8;
  const shoulderPenalty = Math.max(0, upper_body - 4) * 3.3;

  const score = Math.max(0, Math.min(100, 100 - neckPenalty - shoulderPenalty));

  return { neck, shoulders, upper_body, score };
}
