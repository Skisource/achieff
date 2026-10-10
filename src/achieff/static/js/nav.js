document.addEventListener("DOMContentLoaded", () => {
  const burger = document.querySelector(".navbar-burger");
  const menu = document.getElementById("nav-menu");
  if (!burger || !menu) {
    return;
  }

  burger.addEventListener("click", () => {
    const open = !burger.classList.contains("is-active");
    burger.classList.toggle("is-active", open);
    menu.classList.toggle("is-active", open);
    burger.setAttribute("aria-expanded", open ? "true" : "false");
  });
});
