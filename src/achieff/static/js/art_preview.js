const SCALE = 4;
const BASE_COVERALL = [224, 122, 61];
const BASE_HAT = [242, 193, 78];

document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll("[data-art-player]").forEach((player) => {
    startPlayer(player);
  });
});

async function startPlayer(player) {
  const canvas = player.querySelector("canvas");
  const sheet = await loadImage(player.dataset.sheet);
  const variants = await loadVariants(player.dataset.variants);
  const frameWidth = Number(player.dataset.frameWidth);
  const frameHeight = Number(player.dataset.frameHeight);
  const columns = Number(player.dataset.columns);
  const frameCount = Number(player.dataset.frames);
  const label = player.querySelector("[data-frame-label]");
  let frame = 0;

  const show = () => {
    drawFrame(canvas, sheet, frame, columns, frameWidth, frameHeight);
    drawVariants(player, sheet, frame, columns, frameWidth, frameHeight, variants);
    if (label) {
      label.textContent = frameLabel(player.dataset.kind, frame);
    }
  };

  const next = player.querySelector("[data-next]");
  const previous = player.querySelector("[data-prev]");
  if (next && previous) {
    next.addEventListener("click", () => {
      frame = (frame + 1) % frameCount;
      show();
    });
    previous.addEventListener("click", () => {
      frame = (frame - 1 + frameCount) % frameCount;
      show();
    });
  }
  show();
}

function frameLabel(kind, frame) {
  const direction = frame < 4 ? "Right" : "Left";
  const step = (frame % 4) + 1;
  if (kind === "idle") {
    const idleDirection = frame < 2 ? "Right" : "Left";
    return `${idleDirection} ${frame % 2 === 0 ? "stand" : "bob"}`;
  }
  return `${direction} ${step}`;
}

function drawFrame(canvas, sheet, frame, columns, frameWidth, frameHeight) {
  canvas.width = frameWidth * SCALE;
  canvas.height = frameHeight * SCALE;
  const context = canvas.getContext("2d");
  context.imageSmoothingEnabled = false;
  const column = frame % columns;
  const row = Math.floor(frame / columns);
  context.drawImage(
    sheet,
    column * frameWidth,
    row * frameHeight,
    frameWidth,
    frameHeight,
    0,
    0,
    canvas.width,
    canvas.height,
  );
}

function drawVariants(player, sheet, frame, columns, frameWidth, frameHeight, variants) {
  const row = player.querySelector("[data-variants]");
  if (!row) {
    return;
  }
  row.replaceChildren();
  variants.forEach((variant) => {
    const canvas = document.createElement("canvas");
    row.append(canvas);
    paintVariant(canvas, sheet, frame, columns, frameWidth, frameHeight, variant);
  });
}

function paintVariant(canvas, sheet, frame, columns, frameWidth, frameHeight, variant) {
  const source = document.createElement("canvas");
  source.width = frameWidth;
  source.height = frameHeight;
  const sourceContext = source.getContext("2d");
  sourceContext.imageSmoothingEnabled = false;
  const column = frame % columns;
  const row = Math.floor(frame / columns);
  sourceContext.drawImage(
    sheet,
    column * frameWidth,
    row * frameHeight,
    frameWidth,
    frameHeight,
    0,
    0,
    frameWidth,
    frameHeight,
  );
  const pixels = sourceContext.getImageData(0, 0, frameWidth, frameHeight);
  const coverall = hexColor(variant.coverall);
  const hat = hexColor(variant.hat);
  for (let index = 0; index < pixels.data.length; index += 4) {
    if (sameColor(pixels.data, index, BASE_COVERALL)) {
      paint(pixels.data, index, coverall);
    } else if (sameColor(pixels.data, index, BASE_HAT)) {
      paint(pixels.data, index, hat);
    }
  }
  sourceContext.putImageData(pixels, 0, 0);
  canvas.width = frameWidth * SCALE;
  canvas.height = frameHeight * SCALE;
  const context = canvas.getContext("2d");
  context.imageSmoothingEnabled = false;
  context.drawImage(source, 0, 0, canvas.width, canvas.height);
}

function loadImage(url) {
  const image = new Image();
  image.src = url;
  return image.decode().then(() => image);
}

async function loadVariants(url) {
  const response = await fetch(url);
  const payload = await response.json();
  return payload.variants;
}

function hexColor(value) {
  return [
    Number.parseInt(value.slice(1, 3), 16),
    Number.parseInt(value.slice(3, 5), 16),
    Number.parseInt(value.slice(5, 7), 16),
  ];
}

function sameColor(data, index, color) {
  return data[index] === color[0] && data[index + 1] === color[1] && data[index + 2] === color[2];
}

function paint(data, index, color) {
  data[index] = color[0];
  data[index + 1] = color[1];
  data[index + 2] = color[2];
}
