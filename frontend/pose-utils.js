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
  // 1. Neck metric (visible side tilt).
  // Absolute MediaPipe Z includes normal head-to-shoulder depth.  Using it
  // directly makes a healthy seated person look severely bent, so scoring
  // uses the stable 2D alignment available from a single camera.
  const dxNeck = head.x - midShoulder.x;
  const dyNeck = midShoulder.y - head.y;
  const neckRoll = Math.atan2(Math.abs(dxNeck), Math.max(0.001, dyNeck)) * 180 / Math.PI;
  const neck = neckRoll;

  // 2. Shoulder alignment.  Use angles, not screen distances, so the same
  // posture gets a comparable result at different camera distances.
  const dxShoulder = rs.x - ls.x;
  const dyShoulder = rs.y - ls.y;
  const shoulderRoll = Math.atan2(Math.abs(dyShoulder), Math.max(0.001, Math.abs(dxShoulder))) * 180 / Math.PI;
  const shoulders = shoulderRoll;
  const shoulderSpan = Math.max(0.001, Math.hypot(dxShoulder, dyShoulder));

  // A forward-slouched head is deeper than the shoulders.  A small natural
  // head-depth offset is expected, so ignore the first 35% of shoulder width.
  // This normalisation keeps the angle stable across camera distances.
  // MediaPipe Z decreases toward the camera; only forward head movement is
  // counted as slouching.
  const headDepth = Math.max(0, midShoulder.z - head.z);
  const excessHeadDepth = Math.max(0, headDepth - shoulderSpan * 0.35);
  const upper_body = Math.atan2(excessHeadDepth, shoulderSpan) * 180 / Math.PI;

  const neckPenalty = Math.max(0, neck - 12) * 1.2;
  const shoulderPenalty = Math.max(0, shoulders - 6) * 1.0;
  const slouchPenalty = Math.max(0, upper_body - 7) * 1.6;

  const score = Math.max(0, Math.min(100, 100 - neckPenalty - shoulderPenalty - slouchPenalty));

  return { neck, shoulders, upper_body, score };
}
