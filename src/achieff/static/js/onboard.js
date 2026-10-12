const BASE_COVERALL = [224, 122, 61];
const BASE_HAT = [242, 193, 78];
const FRAME_MS = 140;
const IDLE_MS = 420;
const REFRESH_MS = 15000;
const WALK_SPEED = 1.6;

const state = {
  map: null,
  ship: null,
  walk: null,
  idle: null,
  variants: [],
  mapCanvas: null,
  crew: [],
  sprites: [],
  pointer: null,
  pinned: null,
  last: 0,
  frames: new Map(),
};

document.addEventListener("DOMContentLoaded", () => {
  const canvas = document.getElementById("onboard-canvas");
  canvas.addEventListener("pointermove", (event) => {
    state.pointer = eventPoint(canvas, event);
    state.pinned = null;
  });
  canvas.addEventListener("pointerdown", (event) => {
    state.pointer = eventPoint(canvas, event);
    state.pinned = spriteAt(state.pointer);
  });
  startScene(canvas);
});

async function startScene(canvas) {
  const [map, ship, walk, idle, variantFile] = await Promise.all([
    fetch("/static/art/ship_map.json").then((response) => response.json()),
    loadImage("/static/art/ship.png"),
    loadImage("/static/art/walk.png"),
    loadImage("/static/art/idle.png"),
    fetch("/static/art/variants.json").then((response) => response.json()),
  ]);
  state.map = map;
  state.ship = ship;
  state.walk = walk;
  state.idle = idle;
  state.variants = variantFile.variants;
  state.mapCanvas = drawMap(map, ship);
  canvas.width = state.mapCanvas.width;
  canvas.height = state.mapCanvas.height;
  await refreshCrew();
  window.setInterval(refreshCrew, REFRESH_MS);
  requestAnimationFrame((now) => {
    state.last = now;
    tick(now);
  });
}

function tick(now) {
  const dt = Math.min(0.05, (now - state.last) / 1000);
  state.last = now;
  for (const sprite of state.sprites) {
    stepSprite(sprite, dt, now);
  }
  paint();
  showCard();
  requestAnimationFrame(tick);
}

async function refreshCrew() {
  const response = await fetch("/api/onboard", { cache: "no-store" });
  if (!response.ok) {
    return;
  }
  const payload = await response.json();
  const next = new Map(payload.crew.map((person) => [person.alias, person]));
  state.sprites = state.sprites.filter((sprite) => next.has(sprite.alias));
  for (const sprite of state.sprites) {
    const person = next.get(sprite.alias);
    sprite.merit = person.merit;
    sprite.infamy = person.infamy;
    sprite.variant = person.sprite_variant;
    next.delete(sprite.alias);
  }
  for (const person of next.values()) {
    state.sprites.push(spawn(person));
  }
  state.crew = payload.crew;
  renderRoster(payload.crew);
  const empty = document.getElementById("onboard-empty");
  empty.classList.toggle("is-hidden", payload.crew.length > 0);
}

function spawn(person) {
  const waypoint = randomItem(state.map.waypoints);
  return {
    alias: person.alias,
    variant: person.sprite_variant,
    merit: person.merit,
    infamy: person.infamy,
    x: waypoint.x,
    y: waypoint.y,
    waypoint: waypoint.id,
    target: null,
    mode: "idle",
    until: performance.now() + 600 + Math.random() * 1400,
    facing: "right",
  };
}

function stepSprite(sprite, dt, now) {
  if (sprite.mode === "idle") {
    if (now >= sprite.until) {
      const next = randomItem(neighbors(sprite.waypoint));
      if (next === undefined) {
        sprite.until = now + 1000;
        return;
      }
      const point = waypoint(next);
      sprite.target = point;
      sprite.mode = "walk";
      if (point.x !== sprite.x) {
        sprite.facing = point.x > sprite.x ? "right" : "left";
      }
    }
    return;
  }
  const point = sprite.target;
  const dx = point.x - sprite.x;
  const dy = point.y - sprite.y;
  const distance = Math.hypot(dx, dy);
  const step = WALK_SPEED * dt;
  if (distance <= step) {
    sprite.x = point.x;
    sprite.y = point.y;
    sprite.waypoint = point.id;
    sprite.target = null;
    sprite.mode = "idle";
    sprite.until = now + 700 + Math.random() * 1600;
    return;
  }
  sprite.x += (dx / distance) * step;
  sprite.y += (dy / distance) * step;
}

function paint() {
  const canvas = document.getElementById("onboard-canvas");
  const context = canvas.getContext("2d");
  context.imageSmoothingEnabled = false;
  context.drawImage(state.mapCanvas, 0, 0);
  for (const sprite of state.sprites) {
    drawCrew(context, sprite);
  }
}

function drawCrew(context, sprite) {
  const scale = state.map.scale;
  const tile = state.map.tileSize;
  const frame = spriteFrame(sprite);
  const sheet = sprite.mode === "walk" ? state.walk : state.idle;
  const colored = recolorFrame(sheet, frame, sprite.variant);
  const foot = 22;
  const dx = sprite.x * tile * scale;
  const dy = (sprite.y + 1) * tile * scale - foot * scale;
  context.drawImage(colored, dx, dy);
  sprite.screen = { x: dx, y: dy, width: colored.width, height: colored.height };
}

function spriteFrame(sprite) {
  const left = sprite.facing === "left";
  if (sprite.mode === "walk") {
    const column = Math.floor(performance.now() / FRAME_MS) % 4;
    return { column, row: left ? 1 : 0, width: 16, height: 24 };
  }
  const column = Math.floor(performance.now() / IDLE_MS) % 2;
  return { column, row: left ? 1 : 0, width: 16, height: 24 };
}

function recolorFrame(sheet, frame, variantIndex) {
  const variant = state.variants[variantIndex % state.variants.length];
  const key = `${sheet.src}:${frame.column}:${frame.row}:${variant.coverall}:${variant.hat}`;
  const cached = state.frames.get(key);
  if (cached) {
    return cached;
  }
  const source = document.createElement("canvas");
  source.width = frame.width;
  source.height = frame.height;
  const sourceContext = source.getContext("2d");
  sourceContext.imageSmoothingEnabled = false;
  sourceContext.drawImage(
    sheet,
    frame.column * frame.width,
    frame.row * frame.height,
    frame.width,
    frame.height,
    0,
    0,
    frame.width,
    frame.height,
  );
  const pixels = sourceContext.getImageData(0, 0, frame.width, frame.height);
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
  const scale = state.map.scale;
  const scaled = document.createElement("canvas");
  scaled.width = frame.width * scale;
  scaled.height = frame.height * scale;
  const scaledContext = scaled.getContext("2d");
  scaledContext.imageSmoothingEnabled = false;
  scaledContext.drawImage(source, 0, 0, scaled.width, scaled.height);
  state.frames.set(key, scaled);
  return scaled;
}

function drawMap(map, ship) {
  const canvas = document.createElement("canvas");
  const scale = map.scale;
  const tile = map.tileSize;
  canvas.width = map.columns * tile * scale;
  canvas.height = map.rows * tile * scale;
  const context = canvas.getContext("2d");
  context.imageSmoothingEnabled = false;
  map.tiles.forEach((tileId, index) => {
    if (tileId < 0) {
      return;
    }
    const column = index % map.columns;
    const row = Math.floor(index / map.columns);
    context.drawImage(
      ship,
      tileId * tile,
      0,
      tile,
      tile,
      column * tile * scale,
      row * tile * scale,
      tile * scale,
      tile * scale,
    );
  });
  return canvas;
}

function showCard() {
  const card = document.getElementById("crew-card");
  const sprite = state.pinned || spriteAt(state.pointer);
  if (!sprite || !state.pointer) {
    card.classList.remove("is-visible");
    card.hidden = true;
    return;
  }
  document.getElementById("crew-card-alias").textContent = sprite.alias;
  document.getElementById("crew-card-badges").textContent =
    `Good ${sprite.merit} · Nasty ${sprite.infamy}`;
  card.hidden = false;
  card.classList.add("is-visible");
  card.style.left = `${state.pointer.clientX + 12}px`;
  card.style.top = `${state.pointer.clientY + 12}px`;
}

function spriteAt(pointer) {
  if (!pointer) {
    return null;
  }
  return state.sprites.find((sprite) => {
    const box = sprite.screen;
    if (!box) {
      return false;
    }
    return (
      pointer.x >= box.x &&
      pointer.x <= box.x + box.width &&
      pointer.y >= box.y &&
      pointer.y <= box.y + box.height
    );
  });
}

function eventPoint(canvas, event) {
  const bounds = canvas.getBoundingClientRect();
  const scaleX = canvas.width / bounds.width;
  const scaleY = canvas.height / bounds.height;
  return {
    x: (event.clientX - bounds.left) * scaleX,
    y: (event.clientY - bounds.top) * scaleY,
    clientX: event.clientX,
    clientY: event.clientY,
  };
}

function renderRoster(crew) {
  const list = document.getElementById("onboard-roster");
  list.replaceChildren();
  for (const person of crew) {
    const item = document.createElement("li");
    item.textContent = person.alias;
    list.append(item);
  }
}

function neighbors(id) {
  const found = [];
  for (const [left, right] of state.map.edges) {
    if (left === id) {
      found.push(right);
    } else if (right === id) {
      found.push(left);
    }
  }
  return found;
}

function waypoint(id) {
  return state.map.waypoints.find((point) => point.id === id);
}

function randomItem(items) {
  return items[Math.floor(Math.random() * items.length)];
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
  return data[index] === color[0] && data[index + 1] === color[1] && data[index + 2] === color[2];
}

function paintColor(data, index, color) {
  data[index] = color[0];
  data[index + 1] = color[1];
  data[index + 2] = color[2];
}
