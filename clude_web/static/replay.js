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

  /* suspect -> its circle on the board, looked up once. */
  var tokens = {};
  Array.prototype.forEach.call(
    document.querySelectorAll(".board-token"),
    function (circle) {
      tokens[circle.getAttribute("data-suspect")] = circle;
    }
  );

  /* seat index -> { card -> {fill, row, mark} }, looked up once so a
     step is a few hundred style writes and no DOM searching. */
  var seats = {};
  Array.prototype.forEach.call(
    document.querySelectorAll(".seat"),
    function (block) {
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
    });

    stepLine.textContent = frame.text;
    stepLine.className = "step-line kind-" + frame.kind;
    counter.textContent = index + 1 + " / " + frames.length;

    var belief = beliefAt(frame.k);
    if (!belief) return;

    belief.seats.forEach(function (seat) {
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

  scrub.addEventListener("input", function () {
    draw(Number(scrub.value));
  });
  document.getElementById("first").addEventListener("click", function () {
    go(0);
  });
  document.getElementById("prev").addEventListener("click", function () {
    go(Number(scrub.value) - 1);
  });
  document.getElementById("next").addEventListener("click", function () {
    go(Number(scrub.value) + 1);
  });
  document.getElementById("last").addEventListener("click", function () {
    go(frames.length - 1);
  });

  document.addEventListener("keydown", function (event) {
    if (event.target && event.target.tagName === "INPUT" && event.target !== scrub) {
      return;
    }
    if (event.key === "ArrowLeft") {
      go(Number(scrub.value) - 1);
      event.preventDefault();
    } else if (event.key === "ArrowRight") {
      go(Number(scrub.value) + 1);
      event.preventDefault();
    } else if (event.key === "Home") {
      go(0);
      event.preventDefault();
    } else if (event.key === "End") {
      go(frames.length - 1);
      event.preventDefault();
    }
  });

  go(0);
})();
