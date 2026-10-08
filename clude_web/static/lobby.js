/* Show the selected character's method and its optional LLM memory dial.
   The remember checkbox is Developer-only; without it they remember. */
(function () {
  "use strict";
  var form = document.getElementById("table-form");
  if (!form) return;
  var remember = document.getElementById("remember");
  function remembering() { return !remember || remember.checked; }
  form.querySelectorAll(".seat-pick").forEach(function (card) {
    var select = card.querySelector("select");
    var method = card.querySelector(".method");
    var memory = card.querySelector(".seat-memory");
    var dial = memory && memory.querySelector("input");
    var output = memory && memory.querySelector("output");
    function update() {
      method.hidden = select.value !== "llm" && select.value !== "character";
      if (memory) {
        memory.hidden = select.value !== "llm" || !remembering();
        output.textContent = dial.value;
      }
    }
    select.addEventListener("change", update);
    if (remember) remember.addEventListener("change", update);
    if (dial) dial.addEventListener("input", update);
    update();
  });
}());
