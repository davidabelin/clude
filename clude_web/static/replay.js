/* The replay scrubber.
 *
 * The whole game arrives with the page, so stepping is local: no request
 * per step, and the arrow keys feel immediate. Nothing here knows the
 * board's geometry -- token positions come as coordinates worked out
 * server-side from `clude_core.board` (see replay_data.screen_payload),
 * so the drawing and the rules stay in one place.
 */
(function () {
  "use strict";

  var node = document.getElementById("replay-data");
  if (!node) return;
  var data = JSON.parse(node.textContent);

  var frames = data.frames || [];
  if (!frames.length) return;

  var scrub = document.getElementById("scrub");
  var stepLine = document.getElementById("step-line");
  var counter = document.getElementById("counter");
  var playButton = document.getElementById("play");
  var speed = document.getElementById("speed");

  /* suspect -> its circle on the board, and its initial on a dressed
     board (Phase 10f), looked up once. */
  var tokens = {};
  var initials = {};
  Array.prototype.forEach.call(
    document.querySelectorAll(".board-token"),
    function (circle) {
      tokens[circle.getAttribute("data-suspect")] = circle;
    }
  );
  Array.prototype.forEach.call(
    document.querySelectorAll(".board-initial"),
    function (text) {
      initials[text.getAttribute("data-suspect")] = text;
    }
  );

  /* seat index -> { card -> {fill, row, mark} }, looked up once so a
     step is a few hundred style writes and no DOM searching. */
  var seats = {};
  var headings = {};
  Array.prototype.forEach.call(
    document.querySelectorAll(".seat"),
    function (block) {
      headings[block.getAttribute("data-seat")] = block.querySelector("h2");
      var rows = {};
      Array.prototype.forEach.call(
        block.querySelectorAll(".row"),
        function (row) {
          rows[row.getAttribute("data-card")] = {
            row: row,
            fill: row.querySelector(".fill"),
            mark: row.querySelector(".mark")
          };
        }
      );
      seats[block.getAttribute("data-seat")] = rows;
    }
  );

  var truth = {};
  (data.envelope || []).forEach(function (card) {
    truth[card] = true;
  });

  /* The belief frame at or just before k: the trace may be sampled
     coarsely while the scrubber moves per event. Mirrors
     replay_data.belief_at. */
  function beliefAt(k) {
    var best = data.beliefs[0];
    for (var i = 0; i < data.beliefs.length; i += 1) {
      if (data.beliefs[i].k <= k) best = data.beliefs[i];
      else break;
    }
    return best;
  }

  function draw(index) {
    var frame = frames[index];

    Object.keys(frame.tokens).forEach(function (suspect) {
      var circle = tokens[suspect];
      if (!circle) return;
      circle.setAttribute("cx", frame.tokens[suspect][0]);
      circle.setAttribute("cy", frame.tokens[suspect][1]);
      /* An initial moves by transform, so it glides with its disc. */
      var letter = initials[suspect];
      if (letter) letter.style.transform = "translate(" + frame.tokens[suspect][0] + "px, " + frame.tokens[suspect][1] + "px)";
    });

    stepLine.textContent = frame.text;
    stepLine.className = "step-line kind-" + frame.kind;
    counter.textContent = index + 1 + " / " + frames.length;

    var belief = beliefAt(frame.k);
    if (!belief) return;

    belief.seats.forEach(function (seat) {
      var h2 = headings[String(seat.seat)];
      if (h2 && typeof seat.certainty === "number") {
        /* The certainty tag (Phase 9h), as on the table screen. */
        var c = Math.max(0, Math.min(1, seat.certainty));
        h2.style.setProperty("--certainty", c.toFixed(3));
        h2.title = "certainty " + Math.round(c * 100) + "%";
      }
      var rows = seats[String(seat.seat)];
      if (!rows) return;
      Object.keys(rows).forEach(function (card) {
        var cell = rows[card];
        var holder = Object.prototype.hasOwnProperty.call(seat.proven, card)
          ? seat.proven[card]
          : null;
        var probability = seat.p[card];

        cell.mark.className = truth[card] ? "mark truth" : "mark";

        if (holder === "envelope") {
          /* Proven to be the envelope's: the strongest thing a seat can
             know, and not the same claim as a high probability. */
          cell.row.className = "row proven-envelope";
          cell.fill.style.width = "100%";
        } else if (holder !== null && holder !== undefined) {
          /* Proven to sit in someone's hand, so it is settled and out. */
          cell.row.className = "row proven-held";
          cell.fill.style.width = "0%";
        } else {
          cell.row.className = "row open";
          var width = typeof probability === "number" ? probability : 0;
          cell.fill.style.width = (width * 100).toFixed(1) + "%";
        }
      });
    });
  }

  function go(index) {
    var clamped = Math.max(0, Math.min(frames.length - 1, index));
    scrub.value = clamped;
    draw(clamped);
  }

  /* Play (Phase 9h): one step per tick, the tick set by the slider on a
     log scale -- 2 s a step at its slowest, about 350 ms in the middle,
     60 ms flat out -- and re-read at every step so a nudge takes at
     once. Reaching the end pauses; Play at the end starts over; any hand
     on the scrubber pauses. `scrub.value` stays the one source of truth. */
  var playing = false;
  var playTimer = null;

  function stepMs() {
    var v = speed ? Number(speed.value) : 50;
    return 2000 * Math.pow(0.03, v / 100);
  }

  function showPlaying() {
    if (!playButton) return;
    playButton.textContent = playing ? "Pause" : "Play";
    playButton.setAttribute("aria-pressed", playing ? "true" : "false");
  }

  function pause() {
    playing = false;
    if (playTimer) { window.clearTimeout(playTimer); playTimer = null; }
    showPlaying();
  }

  function stepForward() {
    playTimer = null;
    if (!playing) return;
    var next = Number(scrub.value) + 1;
    if (next >= frames.length) { pause(); return; }
    go(next);
    /* Sound (Phase 10g): only Play reaching a step makes one; the
       scrubber, the arrow keys and the first paint stay silent. */
    if (window.cludeSound && frames[next].cue) window.cludeSound.play(frames[next].cue);
    if (next >= frames.length - 1) { pause(); return; }
    playTimer = window.setTimeout(stepForward, stepMs());
  }

  function play() {
    if (playing) return;
    if (Number(scrub.value) >= frames.length - 1) go(0);
    playing = true;
    showPlaying();
    playTimer = window.setTimeout(stepForward, stepMs());
  }

  function toggle() {
    if (playing) pause(); else play();
  }

  if (playButton) playButton.addEventListener("click", toggle);

  function byHand(fn) {
    return function () { pause(); fn(); };
  }

  scrub.addEventListener("input", byHand(function () {
    draw(Number(scrub.value));
  }));
  document.getElementById("first").addEventListener("click", byHand(function () {
    go(0);
  }));
  document.getElementById("prev").addEventListener("click", byHand(function () {
    go(Number(scrub.value) - 1);
  }));
  document.getElementById("next").addEventListener("click", byHand(function () {
    go(Number(scrub.value) + 1);
  }));
  document.getElementById("last").addEventListener("click", byHand(function () {
    go(frames.length - 1);
  }));

  document.addEventListener("keydown", function (event) {
    if (event.target && event.target.tagName === "INPUT" && event.target !== scrub && event.target !== speed) {
      return;
    }
    if (event.key === " " || event.key === "Spacebar") {
      if (event.target === playButton) return;  /* the button's own click follows */
      toggle();
      event.preventDefault();
      return;
    }
    if (event.target === speed) return;
    if (event.key === "ArrowLeft") {
      pause();
      go(Number(scrub.value) - 1);
      event.preventDefault();
    } else if (event.key === "ArrowRight") {
      pause();
      go(Number(scrub.value) + 1);
      event.preventDefault();
    } else if (event.key === "Home") {
      pause();
      go(0);
      event.preventDefault();
    } else if (event.key === "End") {
      pause();
      go(frames.length - 1);
      event.preventDefault();
    }
  });

  go(0);
})();
