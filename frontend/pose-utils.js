/**
 * Pose scoring utility module.
 * Evaluates MediaPipe pose landmarks and returns posture metrics.
 */

export function scorePose(landmarks) {
  if (!landmarks || landmarks.length < 25) return null;
  const nose = landmarks[0], ls = landmarks[11], rs = landmarks[12], lh = landmarks[23], rh = landmarks[24];
  if (![nose, ls, rs, lh, rh].every(x => x?.visibility > 0.45)) return null;

  const sh = { x: (ls.x + rs.x) / 2, y: (ls.y + rs.y) / 2 };
  const hip = { x: (lh.x + rh.x) / 2, y: (lh.y + rh.y) / 2 };

  // Angle relative to vertical axis (upward vector)
  const neck = Math.abs(Math.atan2(nose.x - sh.x, Math.max(0.001, sh.y - nose.y)) * 180 / Math.PI);
  const shoulders = Math.abs(ls.y - rs.y) * 100;
  const torso = Math.abs(Math.atan2(sh.x - hip.x, Math.max(0.001, hip.y - sh.y)) * 180 / Math.PI);

  const score = Math.max(0, Math.min(100, 100 - Math.max(0, neck - 12) * 2.3 - shoulders * 1.4 - Math.max(0, torso - 7) * 2));

  return { neck, shoulders, torso, score };
}
