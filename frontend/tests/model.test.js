import test from 'node:test';
import assert from 'node:assert/strict';
import {
  extractFeatures,
  addExample,
  getExampleCounts,
  clearExamples,
  predict,
  isReady,
  LABELS
} from '../pose-model.js';
import { scorePose } from '../pose-utils.js';

test('extractFeatures correctly parses feature objects', () => {
  assert.deepEqual(extractFeatures({ neck: 15, shoulders: 5.2, torso: 8 }), [15, 5.2, 8]);
  assert.deepEqual(extractFeatures({ neck: '12', shoulders: null, torso: undefined }), [12, 0, 0]);
  assert.equal(extractFeatures(null), null);
});

test('dataset management tracks example counts correctly', () => {
  clearExamples();
  assert.deepEqual(getExampleCounts(), { good: 0, caution: 0, risk: 0, total: 0 });

  addExample({ neck: 5, shoulders: 2, torso: 3 }, 'good');
  addExample({ neck: 8, shoulders: 3, torso: 4 }, 'good');
  addExample({ neck: 18, shoulders: 8, torso: 12 }, 'caution');
  addExample({ neck: 30, shoulders: 15, torso: 22 }, 'risk');

  const counts = getExampleCounts();
  assert.equal(counts.good, 2);
  assert.equal(counts.caution, 1);
  assert.equal(counts.risk, 1);
  assert.equal(counts.total, 4);

  clearExamples();
  assert.equal(getExampleCounts().total, 0);
});

test('addExample throws on invalid label', () => {
  assert.throws(() => {
    addExample({ neck: 5, shoulders: 2, torso: 3 }, 'invalid_label');
  }, /Invalid label/);
});

test('predict returns null when model is not ready', () => {
  assert.equal(isReady(), false);
  assert.equal(predict({ neck: 10, shoulders: 5, torso: 5 }), null);
});

test('scorePose remains intact as fallback', () => {
  const landmarks = new Array(33).fill({ x: 0.5, y: 0.5, z: 0, visibility: 0.9 });
  landmarks[0] = { x: 0.5, y: 0.2, z: 0, visibility: 0.9 };  // nose
  landmarks[11] = { x: 0.4, y: 0.4, z: 0, visibility: 0.9 }; // left shoulder
  landmarks[12] = { x: 0.6, y: 0.4, z: 0, visibility: 0.9 }; // right shoulder
  landmarks[23] = { x: 0.4, y: 0.7, z: 0, visibility: 0.9 }; // left hip
  landmarks[24] = { x: 0.6, y: 0.7, z: 0, visibility: 0.9 }; // right hip

  const result = scorePose(landmarks);
  assert.notEqual(result, null);
  assert.equal(typeof result.score, 'number');
  assert.equal(typeof result.neck, 'number');
});
