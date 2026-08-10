import test from 'node:test';
import assert from 'node:assert/strict';
import { isPostureRisk } from '../pose-utils.js';

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
