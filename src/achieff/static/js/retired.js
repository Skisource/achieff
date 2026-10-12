const BASE_COVERALL = [224, 122, 61];
const BASE_HAT = [242, 193, 78];
const REFRESH_MS = 15000;
const MUGSHOT = 32;
const BADGE = 16;
const SCALE = 3;

document.addEventListener("DOMContentLoaded", () => {
  refreshRoll();
  window.setInterval(refreshRoll, REFRESH_MS);
});

async function refreshRoll() {
  const [response, mugshot, badges] = await Promise.all([
    fetch("/api/retired", { cache: "no-store" }),
    loadImage("/static/art/mugshot.png"),
    loadImage("/static/art/badges.png"),
  ]);
  if (!response.ok) {
    return;
  }
  const payload = await response.json();
  const variants = await loadVariants();
  const roll = document.getElementById("retired-roll");
  roll.replaceChildren();
  for (const person of payload.crew) {
    roll.append(card(person, mugshot, badges, variants));
  }
  document
    .getElementById("retired-empty")
    .classList.toggle("is-hidden", payload.crew.length > 0);
}

function card(person, mugshot, badges, variants) {
  const column = document.createElement("div");
  column.className = "column is-one-quarter-desktop is-half-tablet";
  const article = document.createElement("article");
  article.className = "box has-text-centered";
  const portrait = document.createElement("canvas");
  portrait.className = "retired-portrait";
  portrait.setAttribute("aria-label", person.alias);
  drawMugshot(portrait, mugshot, person.sprite_variant, variants);
  const name = document.createElement("p");
  name.className = "title is-5";
  name.textContent = person.alias;
  article.append(portrait, name, badgeRow(person, badges));
  column.append(article);
  return column;
}

function badgeRow(person, badges) {
  const row = document.createElement("div");
  row.className = "is-flex is-flex-wrap-wrap is-justify-content-center";
  if (person.badges.length === 0) {
    const empty = document.createElement("p");
    empty.textContent = "No badges yet.";
    row.append(empty);
    return row;
  }
  for (const badge of person.badges) {
    const item = document.createElement("div");
    item.className = "m-1";
    const canvas = document.createElement("canvas");
    canvas.className = "retired-badge";
    canvas.width = BADGE * 2;
    canvas.height = BADGE * 2;
    const context = canvas.getContext("2d");
    context.imageSmoothingEnabled = false;
    context.drawImage(
      badges,
      badge.icon * BADGE,
      0,
      BADGE,
      BADGE,
      0,
      0,
      canvas.width,
      canvas.height,
    );
    const title = document.createElement("p");
    title.className = "is-size-7";
    title.textContent = badge.title;
    item.append(canvas, title);
    row.append(item);
  }
  return row;
}

function drawMugshot(canvas, sheet, variantIndex, variants) {
  const variant = variants[variantIndex % variants.length];
  const source = document.createElement("canvas");
  source.width = MUGSHOT;
  source.height = MUGSHOT;
  const sourceContext = source.getContext("2d");
  sourceContext.drawImage(sheet, 0, 0);
  const pixels = sourceContext.getImageData(0, 0, MUGSHOT, MUGSHOT);
  const coverall = hexColor(variant.coverall);
  const hat = hexColor(variant.hat);
  for (let index = 0; index < pixels.data.length; index += 4) {
    if (sameColor(pixels.data, index, BASE_COVERALL)) {
      paintColor(pixels.data, index, coverall);
    } else if (sameColor(pixels.data, index, BASE_HAT)) {
      paintColor(pixels.data, index, hat);
    }
  }
  sourceContext.putImageData(pixels, 0, 0);
  canvas.width = MUGSHOT * SCALE;
  canvas.height = MUGSHOT * SCALE;
  const context = canvas.getContext("2d");
  context.imageSmoothingEnabled = false;
  context.drawImage(source, 0, 0, canvas.width, canvas.height);
}

function loadImage(url) {
  const image = new Image();
  image.src = url;
  return image.decode().then(() => image);
}

function loadVariants() {
  return fetch("/static/art/variants.json").then((response) => response.json()).then(
    (payload) => payload.variants,
  );
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

function paintColor(data, index, color) {
  data[index] = color[0];
  data[index + 1] = color[1];
  data[index + 2] = color[2];
}
