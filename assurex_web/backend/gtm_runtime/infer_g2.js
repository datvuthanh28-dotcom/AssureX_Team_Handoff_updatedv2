const fs = require("fs");
const path = require("path");
const tf = require("@tensorflow/tfjs");
const { PNG } = require("pngjs");

async function loadModel(modelJsonPath) {
  const dir = path.dirname(modelJsonPath);
  const modelJson = JSON.parse(fs.readFileSync(modelJsonPath, "utf8"));

  const specs = [];
  const buffers = [];

  for (const group of modelJson.weightsManifest || []) {
    for (const spec of group.weights || []) {
      specs.push(spec);
    }
    for (const rel of group.paths || []) {
      buffers.push(fs.readFileSync(path.join(dir, rel)));
    }
  }

  const merged = Buffer.concat(buffers);
  const weightData = merged.buffer.slice(
    merged.byteOffset,
    merged.byteOffset + merged.byteLength
  );

  const handler = tf.io.fromMemory({
    modelTopology: modelJson.modelTopology,
    weightSpecs: specs,
    weightData: weightData,
  });

  return await tf.loadLayersModel(handler);
}

function pngToTensor(pngPath, imageSize) {
  const decoded = PNG.sync.read(fs.readFileSync(pngPath));
  const { width, height, data } = decoded;

  const rgb = new Float32Array(width * height * 3);

  let j = 0;

  for (let i = 0; i < data.length; i += 4) {
    rgb[j++] = data[i];
    rgb[j++] = data[i + 1];
    rgb[j++] = data[i + 2];
  }

  const input = tf.tensor3d(
    rgb,
    [height, width, 3],
    "float32"
  );

  /*
   * Match @teachablemachine/image cropTo():
   *
   * 1. Scale so the SHORTER side becomes imageSize.
   * 2. Centre-crop the resulting image to imageSize x imageSize.
   */
  const minSide = Math.min(width, height);
  const scale = imageSize / minSide;

  const scaledW = Math.ceil(width * scale);
  const scaledH = Math.ceil(height * scale);

  const resized = tf.image.resizeBilinear(
    input,
    [scaledH, scaledW],
    false
  );

  const dx = scaledW - imageSize;
  const dy = scaledH - imageSize;

  const left = Math.trunc(dx / 2);
  const top = Math.trunc(dy / 2);

  const cropped = resized.slice(
    [top, left, 0],
    [imageSize, imageSize, 3]
  );

  /*
   * Match Teachable Machine capture():
   * normalize [0,255] using /127 - 1.
   */
  const normalized = cropped
    .toFloat()
    .div(tf.scalar(127))
    .sub(tf.scalar(1));

  const batched = normalized.expandDims(0);

  input.dispose();
  resized.dispose();
  cropped.dispose();
  normalized.dispose();

  return batched;
}

async function main() {
  const [modelJsonPath, metadataPath, pngPath] = process.argv.slice(2);

  if (!modelJsonPath || !metadataPath || !pngPath) {
    throw new Error(
      "usage: node infer_g2.js model.json metadata.json card.png"
    );
  }

  const metadata = JSON.parse(fs.readFileSync(metadataPath, "utf8"));
  const labels = metadata.labels;
  const imageSize = Number(metadata.imageSize || 224);

  const model = await loadModel(modelJsonPath);
  const input = pngToTensor(pngPath, imageSize);

  let output = model.predict(input);
  if (Array.isArray(output)) {
    output = output[0];
  }

  const values = Array.from(await output.data());

  const probabilities = {};
  labels.forEach((label, i) => {
    probabilities[label] = Number(values[i]);
  });

  let bestIndex = 0;
  for (let i = 1; i < values.length; i++) {
    if (values[i] > values[bestIndex]) {
      bestIndex = i;
    }
  }

  process.stdout.write(JSON.stringify({
    predicted_class: labels[bestIndex],
    confidence: Number(values[bestIndex]),
    probabilities,
  }));

  input.dispose();
  output.dispose();
  model.dispose();
}

main().catch((err) => {
  process.stderr.write(String(err.stack || err));
  process.exit(1);
});
