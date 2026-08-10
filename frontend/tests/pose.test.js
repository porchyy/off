import test from 'node:test';
import assert from 'node:assert/strict';
import { isPostureRisk, scorePose } from '../pose-utils.js';

test('isPostureRisk alerts immediately at zero delay only for a low score', () => {
  assert.equal(isPostureRisk(59, 60, 0, 0), true);
  assert.equal(isPostureRisk(60, 60, 0, 0), false);
  assert.equal(isPostureRisk(90, 60, 0, 0), false);
});

test('isPostureRisk keeps the configured delay for mildly low scores', () => {
  assert.equal(isPostureRisk(55, 60, 4_999, 5), false);
  assert.equal(isPostureRisk(55, 60, 5_000, 5), true);
  assert.equal(isPostureRisk(49, 60, 0, 5), true);
});

test('scorePose returns null for empty or incomplete landmarks', () => {
  assert.equal(scorePose(null), null);
  assert.equal(scorePose([]), null);
  assert.equal(scorePose(new Array(10).fill({ visibility: 0.9 })), null);
});

test('scorePose returns null when key landmarks have low visibility', () => {
  const landmarks = new Array(13).fill({ x: 0.5, y: 0.5, z: 0, visibility: 0.9 });
  landmarks[0] = { x: 0.5, y: 0.5, z: 0, visibility: 0.2 }; // low nose visibility

  assert.equal(scorePose(landmarks), null);
});

test('scorePose calculates correct metrics for upright posture', () => {
  const landmarks = new Array(13).fill({ x: 0.5, y: 0.5, z: 0, visibility: 0.9 });

  // Perfectly aligned vertically
  landmarks[0] = { x: 0.5, y: 0.2, z: 0, visibility: 0.9 };  // nose
  landmarks[7] = { x: 0.48, y: 0.25, z: 0, visibility: 0.9 }; // left ear
  landmarks[8] = { x: 0.52, y: 0.25, z: 0, visibility: 0.9 }; // right ear
  landmarks[11] = { x: 0.4, y: 0.4, z: 0, visibility: 0.9 }; // left shoulder
  landmarks[12] = { x: 0.6, y: 0.4, z: 0, visibility: 0.9 }; // right shoulder

  const result = scorePose(landmarks);

  assert.notEqual(result, null);
  assert.equal(Math.round(result.score), 100);
  assert.equal(Math.round(result.shoulders), 0);
  assert.equal(Math.round(result.neck), 0);
  assert.equal(Math.round(result.upper_body), 0);
});

test('scorePose scores an upper body without any hip landmarks', () => {
  const landmarks = new Array(13).fill({ x: 0.5, y: 0.5, z: 0, visibility: 0.9 });

  // Head tilted sideways and uneven shoulders.
  landmarks[0] = { x: 0.7, y: 0.3, z: 0, visibility: 0.9 };  // nose tilted to x=0.7
  landmarks[7] = { x: 0.68, y: 0.3, z: 0, visibility: 0.9 };
  landmarks[8] = { x: 0.72, y: 0.3, z: 0, visibility: 0.9 };
  landmarks[11] = { x: 0.4, y: 0.4, z: 0, visibility: 0.9 }; // left shoulder
  landmarks[12] = { x: 0.6, y: 0.45, z: 0, visibility: 0.9 };// right shoulder (uneven y)

  const result = scorePose(landmarks);

  assert.notEqual(result, null);
  assert.ok(result.score < 100, 'Score should be less than 100 for slouched pose');
  assert.ok(result.neck > 10, 'Neck angle should be non-zero');
  assert.ok(result.shoulders > 0, 'Shoulders tilt should be non-zero');
  assert.equal(Math.round(result.upper_body), 0, 'Side tilt alone is not forward slouching');
});

test('scorePose deducts points for forward slouching without hip landmarks', () => {
  const landmarks = new Array(13).fill({ x: 0.5, y: 0.5, z: 0, visibility: 0.9 });
  landmarks[0] = { x: 0.5, y: 0.2, z: -0.4, visibility: 0.9 };
  landmarks[7] = { x: 0.48, y: 0.25, z: -0.4, visibility: 0.9 };
  landmarks[8] = { x: 0.52, y: 0.25, z: -0.4, visibility: 0.9 };
  landmarks[11] = { x: 0.4, y: 0.4, z: 0, visibility: 0.9 };
  landmarks[12] = { x: 0.6, y: 0.4, z: 0, visibility: 0.9 };

  const result = scorePose(landmarks);

  assert.notEqual(result, null);
  assert.ok(result.upper_body > 7, 'Forward head depth should register as slouching');
  assert.ok(result.score < 100, 'Slouching should deduct points');
});
