// Copies MediaPipe tasks-vision JS bundle + WASM engine and TensorFlow.js bundle
// from node_modules into public/, so app.js can load them as local static files
// instead of from external CDNs.
//
// Runs automatically via `postinstall` / before `dev` and `build`.

import { existsSync, mkdirSync, copyFileSync, readdirSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const root = join(here, '..');
const publicDir = join(root, 'public');

function findPkgDir(relativePkgPath) {
  const localPath = join(root, 'node_modules', ...relativePkgPath);
  if (existsSync(localPath)) return localPath;
  const parentPath = join(root, '..', 'node_modules', ...relativePkgPath);
  if (existsSync(parentPath)) return parentPath;
  return null;
}

// 1. Copy MediaPipe Assets
const pkgDir = findPkgDir(['@mediapipe', 'tasks-vision']);
const targetWasmDir = join(publicDir, 'wasm');

if (pkgDir) {
  mkdirSync(targetWasmDir, { recursive: true });
  const visionBundleSrc = existsSync(join(pkgDir, 'vision_bundle.js'))
    ? join(pkgDir, 'vision_bundle.js')
    : join(pkgDir, 'vision_bundle.mjs');
  copyFileSync(visionBundleSrc, join(publicDir, 'vision_bundle.js'));

  const wasmSrcDir = join(pkgDir, 'wasm');
  if (existsSync(wasmSrcDir)) {
    for (const file of readdirSync(wasmSrcDir)) {
      copyFileSync(join(wasmSrcDir, file), join(targetWasmDir, file));
    }
  }
  console.log('[copy-ai-assets] Copied MediaPipe vision_bundle.js + wasm/ into public/');
} else {
  console.warn('[copy-ai-assets] @mediapipe/tasks-vision not found in node_modules.');
}

// 2. Copy TensorFlow.js Bundle for Offline Custom Training
const tfPkgDir = findPkgDir(['@tensorflow', 'tfjs', 'dist']);
if (tfPkgDir && existsSync(join(tfPkgDir, 'tf.min.js'))) {
  copyFileSync(join(tfPkgDir, 'tf.min.js'), join(publicDir, 'tf.min.js'));
  console.log('[copy-ai-assets] Copied tf.min.js into public/');
} else {
  console.warn('[copy-ai-assets] @tensorflow/tfjs not found in node_modules.');
}

// 3. Ensure custom models directory exists
const customModelsDir = join(publicDir, 'models', 'custom');
mkdirSync(customModelsDir, { recursive: true });

if (!existsSync(join(publicDir, 'models', 'pose_landmarker_full.task'))) {
  console.warn(
    '[copy-ai-assets] NOTE: public/models/pose_landmarker_full.task is missing.\n' +
    '  The app will not be able to start pose detection until you download it once — see\n' +
    '  public/models/README.md for instructions.'
  );
}
