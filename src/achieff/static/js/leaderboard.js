const BASE_COVERALL = [224, 122, 61];
const BASE_HAT = [242, 193, 78];
const MUGSHOT = 32;
const BADGE = 16;

document.addEventListener("DOMContentLoaded", () => {
  refreshBoard();
  listenForBoardChanges(refreshBoard);
});

async function refreshBoard() {
  const [response, mugshot, badges, variantFile] = await Promise.all([
    fetch("/api/leaderboard", { cache: "no-store" }),
    loadImage("/static/art/mugshot.png"),
    loadImage("/static/art/badges.png"),
    fetch("/static/art/variants.json").then((reply) => reply.json()),
  ]);
  if (!response.ok) {
    return;
  }
  const payload = await response.json();
  const hasRows = payload.rows.length > 0;
  document.getElementById("leaderboard-empty").classList.toggle("is-hidden", hasRows);
  document.getElementById("leaderboard-callouts").classList.toggle("is-hidden", !hasRows);
  document.getElementById("leaderboard-table").classList.toggle("is-hidden", !hasRows);
  if (!hasRows) {
    return;
  }
  paintCallout(document.getElementById("good-boy"), payload.good_boy, mugshot, variantFile.variants);
  paintCallout(document.getElementById("nasty"), payload.nasty, mugshot, variantFile.variants);
  paintTable(payload.rows, mugshot, badges, variantFile.variants);
}

function paintCallout(article, person, mugshot, variants) {
  const canvas = article.querySelector("canvas");
  drawMugshot(canvas, mugshot, person.sprite_variant, variants, 2);
  article.querySelector("[data-alias]").textContent = person.alias;
  article.querySelector("[data-score]").textContent = `Net ${person.net}`;
}

function paintTable(rows, mugshot, badges, variants) {
  const body = document.querySelector("#leaderboard-table tbody");
  body.replaceChildren();
  for (const person of rows) {
    const row = document.createElement("tr");
    row.append(
      cell(String(person.rank)),
      portraitCell(person, mugshot, variants),
      aliasCell(person),
      cell(String(person.net)),
      cell(String(person.merit)),
      cell(String(person.infamy)),
      badgeCell(person, badges),
    );
    body.append(row);
  }
}

function portraitCell(person, mugshot, variants) {
  const entry = document.createElement("td");
  const canvas = document.createElement("canvas");
  canvas.className = "leaderboard-portrait";
  drawMugshot(canvas, mugshot, person.sprite_variant, variants, 1);
  entry.append(canvas);
  return entry;
}

function aliasCell(person) {
  const entry = document.createElement("td");
  entry.textContent = person.alias;
  if (person.status === "retired") {
    const mark = document.createElement("span");
    mark.className = "tag is-light ml-2";
    mark.textContent = "Retired";
    entry.append(mark);
  }
  return entry;
}

function badgeCell(person, badges) {
  const entry = document.createElement("td");
  const row = document.createElement("div");
  row.className = "is-flex is-flex-wrap-wrap";
  for (const badge of person.badges) {
    const canvas = document.createElement("canvas");
    canvas.className = `leaderboard-badge m-1 badge-${badge.polarity}`;
    canvas.width = BADGE * 2;
    canvas.height = BADGE * 2;
    canvas.setAttribute("aria-label", badge.title);
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
    row.append(canvas);
  }
  entry.append(row);
  return entry;
}

function cell(text) {
  const entry = document.createElement("td");
  entry.textContent = text;
  return entry;
}

function drawMugshot(canvas, sheet, variantIndex, variants, scale) {
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
  canvas.width = MUGSHOT * scale;
  canvas.height = MUGSHOT * scale;
  const context = canvas.getContext("2d");
  context.imageSmoothingEnabled = false;
  context.drawImage(source, 0, 0, canvas.width, canvas.height);
}

function loadImage(url) {
  const image = new Image();
  image.src = url;
  return image.decode().then(() => image);
}

function hexColor(value) {
  return [
    Number.parseInt(value.slice(1, 3), 16),
    Number.parseInt(value.slice(3, 5), 16),
    Number.parseInt(value.slice(5, 7), 16),
  ];
}

function sameColor(data, index, color) {
  return (
    data[index] === color[0] &&
    data[index + 1] === color[1] &&
    data[index + 2] === color[2]
  );
}

function paintColor(data, index, color) {
  data[index] = color[0];
  data[index + 1] = color[1];
  data[index + 2] = color[2];
}
