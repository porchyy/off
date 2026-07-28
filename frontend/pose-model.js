/**
 * PostureAI — Custom Posture Model Module (TensorFlow.js)
 * 
 * Provides dataset collection, local training, model serialization/loading,
 * and prediction logic that outputs a format compatible with scorePose().
 */

let dataset = [];
let model = null;
let isModelReady = false;

export const LABELS = ['good', 'caution', 'risk'];

/**
 * Gets the active TensorFlow.js instance (browser window.tf or npm package)
 */
export function getTf() {
  if (typeof window !== 'undefined' && window.tf) {
    return window.tf;
  }
  return null;
}

/**
 * Normalizes [neck, shoulders, torso] input features into array of float32
 */
export function extractFeatures(features) {
  if (!features) return null;
  const neck = Number(features.neck) || 0;
  const shoulders = Number(features.shoulders) || 0;
  const torso = Number(features.torso) || 0;
  return [neck, shoulders, torso];
}

/**
 * Adds a training sample
 * @param {Object} features { neck, shoulders, torso }
 * @param {string} label 'good' | 'caution' | 'risk'
 */
export function addExample(features, label) {
  if (!LABELS.includes(label)) {
    throw new Error(`Invalid label: ${label}. Must be one of ${LABELS.join(', ')}`);
  }
  const feats = extractFeatures(features);
  if (!feats) return false;
  dataset.push({ features: feats, label });
  return true;
}

/**
 * Returns count of collected samples per label
 */
export function getExampleCounts() {
  const counts = { good: 0, caution: 0, risk: 0, total: dataset.length };
  for (const item of dataset) {
    if (counts[item.label] !== undefined) {
      counts[item.label]++;
    }
  }
  return counts;
}

/**
 * Clears stored training dataset
 */
export function clearExamples() {
  dataset = [];
}

/**
 * Returns raw dataset array
 */
export function getExamples() {
  return [...dataset];
}

/**
 * Builds a lightweight Sequential Neural Network model
 */
export function buildModel(tf) {
  const net = tf.sequential();
  net.add(tf.layers.dense({ inputShape: [3], units: 16, activation: 'relu' }));
  net.add(tf.layers.dense({ units: 8, activation: 'relu' }));
  net.add(tf.layers.dense({ units: 3, activation: 'softmax' }));
  net.compile({
    optimizer: tf.train.adam(0.01),
    loss: 'categoricalCrossentropy',
    metrics: ['accuracy']
  });
  return net;
}

/**
 * Trains the neural network on collected dataset
 * @param {Object} [callbacks] Optional { onEpochEnd: (epoch, logs) => void }
 */
export async function trainModel(callbacks = {}) {
  const tf = getTf();
  if (!tf) {
    throw new Error('TensorFlow.js is not loaded.');
  }

  if (dataset.length === 0) {
    throw new Error('ยังไม่มีข้อมูลสำหรับเทรนโมเดล (กรุณาเก็บตัวอย่างอย่างน้อย label ละ 15-20 ตัวอย่าง)');
  }

  const xsData = dataset.map(d => d.features);
  const ysData = dataset.map(d => {
    const idx = LABELS.indexOf(d.label);
    const vec = [0, 0, 0];
    if (idx !== -1) vec[idx] = 1;
    return vec;
  });

  const xs = tf.tensor2d(xsData, [xsData.length, 3]);
  const ys = tf.tensor2d(ysData, [ysData.length, 3]);

  if (model) {
    model.dispose();
  }

  model = buildModel(tf);

  const epochs = Math.max(20, Math.min(60, Math.round(dataset.length * 1.2)));

  await model.fit(xs, ys, {
    epochs,
    batchSize: Math.min(16, dataset.length),
    shuffle: true,
    callbacks: {
      onEpochEnd: (epoch, logs) => {
        if (callbacks.onEpochEnd) {
          callbacks.onEpochEnd(epoch + 1, epochs, logs);
        }
      }
    }
  });

  xs.dispose();
  ys.dispose();

  isModelReady = true;
  return { model, epochs, samples: dataset.length };
}

/**
 * Predicts posture score and label for input features
 * @param {Object} features { neck, shoulders, torso }
 * @returns {Object|null} Output compatible with scorePose()
 */
export function predict(features) {
  if (!isModelReady || !model) return null;
  const tf = getTf();
  if (!tf) return null;

  const feats = extractFeatures(features);
  if (!feats) return null;

  return tf.tidy(() => {
    const inputTensor = tf.tensor2d([feats], [1, 3]);
    const predTensor = model.predict(inputTensor);
    const probs = predTensor.dataSync();

    const pGood = probs[0] || 0;
    const pCaution = probs[1] || 0;
    const pRisk = probs[2] || 0;

    // Calculate score (0-100) based on weighted class probabilities
    const rawScore = pGood * 92 + pCaution * 68 + pRisk * 25;
    const score = Math.max(0, Math.min(100, Math.round(rawScore)));

    let maxIdx = 0;
    let maxProb = pGood;
    if (pCaution > maxProb) {
      maxProb = pCaution;
      maxIdx = 1;
    }
    if (pRisk > maxProb) {
      maxProb = pRisk;
      maxIdx = 2;
    }

    const label = LABELS[maxIdx];

    return {
      neck: feats[0],
      shoulders: feats[1],
      torso: feats[2],
      score,
      label,
      probs: { good: pGood, caution: pCaution, risk: pRisk },
      isCustomModel: true
    };
  });
}

/**
 * Downloads model files (model.json, model.weights.bin)
 */
export async function saveModel(filename = 'custom-posture-model') {
  if (!model || !isModelReady) {
    throw new Error('ยังไม่มีโมเดลที่เทรนสำเร็จเพื่อบันทึก');
  }
  const tf = getTf();
  if (!tf) throw new Error('TensorFlow.js is not loaded');

  await model.save(`downloads://${filename}`);
  return true;
}

/**
 * Loads model from uploaded files (HTML input files)
 * @param {FileList|Array<File>} files 
 */
export async function loadModel(files) {
  const tf = getTf();
  if (!tf) throw new Error('TensorFlow.js is not loaded');

  if (!files || files.length === 0) {
    throw new Error('กรุณาเลือกไฟล์โมเดล (model.json และ model.weights.bin)');
  }

  const loadedModel = await tf.loadLayersModel(tf.io.browserFiles(files));
  if (model) {
    model.dispose();
  }
  model = loadedModel;
  isModelReady = true;
  return model;
}

/**
 * Loads model from local static path
 * @param {string} url 
 */
export async function loadModelFromUrl(url) {
  const tf = getTf();
  if (!tf) return false;

  try {
    const loadedModel = await tf.loadLayersModel(url);
    if (model) {
      model.dispose();
    }
    model = loadedModel;
    isModelReady = true;
    return true;
  } catch (e) {
    console.warn('[pose-model] Failed to load custom model from URL:', url, e);
    return false;
  }
}

/**
 * Returns true if model is loaded and ready
 */
export function isReady() {
  return isModelReady && model !== null;
}

/**
 * Reset model instance
 */
export function resetModel() {
  if (model) {
    model.dispose();
    model = null;
  }
  isModelReady = false;
}

/**
 * Uploads current trained model to user's cloud account
 */
export async function syncModelToCloud(token) {
  if (!model || !isModelReady || !token) return false;
  const tf = getTf();
  if (!tf) return false;

  let savedJson = null;
  let savedWeightsB64 = null;

  try {
    await model.save(tf.io.withSaveHandler(async (artifacts) => {
      savedJson = JSON.stringify(artifacts.modelTopology);
      if (artifacts.weightData) {
        const bytes = new Uint8Array(artifacts.weightData);
        let binary = '';
        for (let i = 0; i < bytes.byteLength; i++) {
          binary += String.fromCharCode(bytes[i]);
        }
        savedWeightsB64 = btoa(binary);
      }
      return { modelArtifactsInfo: { dateSaved: new Date(), modelTopologyBytes: savedJson ? savedJson.length : 0 } };
    }));

    if (!savedJson || !savedWeightsB64) return false;

    const resp = await fetch('/api/user/model', {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify({
        modelJson: savedJson,
        weightsBase64: savedWeightsB64
      })
    });
    return resp.ok;
  } catch (e) {
    console.warn('[pose-model] Failed to sync model to cloud:', e);
    return false;
  }
}

/**
 * Downloads user's personal model from cloud and loads it into memory
 */
export async function syncModelFromCloud(token) {
  if (!token) return false;
  const tf = getTf();
  if (!tf) return false;

  try {
    const resp = await fetch('/api/user/model', {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    if (!resp.ok) return false;
    const data = await resp.json();

    const modelTopology = JSON.parse(data.modelJson);
    const binary = atob(data.weightsBase64);
    const bytes = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i++) {
      bytes[i] = binary.charCodeAt(i);
    }

    const loadedModel = await tf.loadLayersModel(tf.io.fromMemory({
      modelTopology,
      weightData: bytes.buffer
    }));

    if (model) model.dispose();
    model = loadedModel;
    isModelReady = true;
    return true;
  } catch (e) {
    console.warn('[pose-model] Failed to sync model from cloud:', e);
    return false;
  }
}
