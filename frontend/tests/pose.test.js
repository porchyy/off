import test from 'node:test';
import assert from 'node:assert/strict';
import { scorePose } from '../pose-utils.js';

test('scorePose returns null for empty or incomplete landmarks', () => {
  assert.equal(scorePose(null), null);
  assert.equal(scorePose([]), null);
  assert.equal(scorePose(new Array(10).fill({ visibility: 0.9 })), null);
});

test('scorePose returns null when key landmarks have low visibility', () => {
  const landmarks = new Array(33).fill({ x: 0.5, y: 0.5, z: 0, visibility: 0.9 });
  landmarks[0] = { x: 0.5, y: 0.5, z: 0, visibility: 0.2 }; // low nose visibility

  assert.equal(scorePose(landmarks), null);
});

test('scorePose calculates correct metrics for upright posture', () => {
  const landmarks = new Array(33).fill({ x: 0.5, y: 0.5, z: 0, visibility: 0.9 });

  // Perfectly aligned vertically
  landmarks[0] = { x: 0.5, y: 0.2, z: 0, visibility: 0.9 };  // nose
  landmarks[11] = { x: 0.4, y: 0.4, z: 0, visibility: 0.9 }; // left shoulder
  landmarks[12] = { x: 0.6, y: 0.4, z: 0, visibility: 0.9 }; // right shoulder
  landmarks[23] = { x: 0.4, y: 0.7, z: 0, visibility: 0.9 }; // left hip
  landmarks[24] = { x: 0.6, y: 0.7, z: 0, visibility: 0.9 }; // right hip

  const result = scorePose(landmarks);

  assert.notEqual(result, null);
  assert.equal(Math.round(result.score), 100);
  assert.equal(Math.round(result.shoulders), 0);
  assert.equal(Math.round(result.neck), 0);
  assert.equal(Math.round(result.torso), 0);
});

test('scorePose deducts points for forward neck tilt and uneven shoulders', () => {
  const landmarks = new Array(33).fill({ x: 0.5, y: 0.5, z: 0, visibility: 0.9 });

  // Slouching / neck tilted forward
  landmarks[0] = { x: 0.7, y: 0.3, z: 0, visibility: 0.9 };  // nose tilted to x=0.7
  landmarks[11] = { x: 0.4, y: 0.4, z: 0, visibility: 0.9 }; // left shoulder
  landmarks[12] = { x: 0.6, y: 0.45, z: 0, visibility: 0.9 };// right shoulder (uneven y)
  landmarks[23] = { x: 0.4, y: 0.7, z: 0, visibility: 0.9 }; // left hip
  landmarks[24] = { x: 0.6, y: 0.7, z: 0, visibility: 0.9 }; // right hip

  const result = scorePose(landmarks);

  assert.notEqual(result, null);
  assert.ok(result.score < 100, 'Score should be less than 100 for slouched pose');
  assert.ok(result.neck > 10, 'Neck angle should be non-zero');
  assert.ok(result.shoulders > 0, 'Shoulders tilt should be non-zero');
});
