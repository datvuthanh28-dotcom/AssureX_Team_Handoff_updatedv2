const fs = require("fs");
const path = require("path");
const http = require("http");

const {
  createCanvas,
  loadImage,
  Image,
} = require("canvas");

global.Image = Image;
global.HTMLImageElement = Image;

const testCanvas = createCanvas(1, 1);

global.HTMLCanvasElement =
  testCanvas.constructor;

global.HTMLVideoElement =
  class HTMLVideoElement {};

global.document = {
  createElement(tag) {
    if (tag === "canvas") {
      return createCanvas(1, 1);
    }

    throw new Error(
      `Unsupported document.createElement("${tag}")`
    );
  },
};

const tmImage =
  require("@teachablemachine/image");


function contentType(filePath) {
  if (filePath.endsWith(".json")) {
    return "application/json";
  }

  if (filePath.endsWith(".bin")) {
    return "application/octet-stream";
  }

  return "application/octet-stream";
}


function startModelServer(modelDir) {
  return new Promise((resolve, reject) => {

    const server = http.createServer(
      (req, res) => {

        try {
          const requestPath =
            decodeURIComponent(
              req.url.split("?")[0]
            );

          const relative =
            requestPath.replace(/^\/+/, "");

          const filePath =
            path.join(
              modelDir,
              relative
            );

          if (
            !filePath.startsWith(
              path.resolve(modelDir)
            )
          ) {
            res.statusCode = 403;
            res.end("Forbidden");
            return;
          }

          if (!fs.existsSync(filePath)) {
            res.statusCode = 404;
            res.end("Not Found");
            return;
          }

          res.setHeader(
            "Content-Type",
            contentType(filePath)
          );

          res.setHeader(
            "Access-Control-Allow-Origin",
            "*"
          );

          fs.createReadStream(
            filePath
          ).pipe(res);

        } catch (err) {
          res.statusCode = 500;
          res.end(String(err));
        }
      }
    );

    server.on("error", reject);

    server.listen(
      0,
      "127.0.0.1",
      () => {
        const address =
          server.address();

        resolve({
          server,
          baseURL:
            `http://127.0.0.1:${address.port}`
        });
      }
    );
  });
}


async function main() {

  const [
    modelJsonPath,
    metadataPath,
    pngPath,
  ] = process.argv.slice(2);

  if (
    !modelJsonPath ||
    !metadataPath ||
    !pngPath
  ) {
    throw new Error(
      "usage: node infer_g2.js model.json metadata.json card.png"
    );
  }

  const absoluteModel =
    path.resolve(modelJsonPath);

  const absoluteMetadata =
    path.resolve(metadataPath);

  const modelDir =
    path.dirname(
      absoluteModel
    );

  if (
    path.dirname(
      absoluteMetadata
    ) !== modelDir
  ) {
    throw new Error(
      "model.json and metadata.json must be in same directory"
    );
  }

  const {
    server,
    baseURL,
  } =
    await startModelServer(
      modelDir
    );

  try {

    const modelURL =
      baseURL +
      "/" +
      path.basename(
        absoluteModel
      );

    const metadataURL =
      baseURL +
      "/" +
      path.basename(
        absoluteMetadata
      );

    const image =
      await loadImage(
        path.resolve(
          pngPath
        )
      );

    const model =
      await tmImage.load(
        modelURL,
        metadataURL
      );

    const predictions =
      await model.predict(
        image,
        false
      );

    const probabilities = {};

    let predictedClass = null;
    let confidence = -1;

    for (
      const item
      of predictions
    ) {
      probabilities[
        item.className
      ] =
        Number(
          item.probability
        );

      if (
        item.probability >
        confidence
      ) {
        predictedClass =
          item.className;

        confidence =
          Number(
            item.probability
          );
      }
    }

    process.stdout.write(
      JSON.stringify({
        predicted_class:
          predictedClass,

        confidence:
          confidence,

        probabilities:
          probabilities,
      })
    );

  } finally {
    server.close();
  }
}


main().catch((err) => {

  process.stderr.write(
    String(
      err.stack || err
    )
  );

  process.exit(1);
});
