/* The table screen (Phase 8.2; Phase 10d-10g).
 *
 * The page arrives with the viewer's view of the game embedded; from then
 * on it polls for what changed, fires one unit of bot work whenever the
 * server says work is due, and posts the viewer's answers. Everything
 * the server sends is written into the page as text (textContent) or as
 * DOM nodes, never as markup: table talk and names are text from outside
 * the app.
 *
 * Nothing here knows the board's geometry: token positions and the legal
 * destinations of a move come as coordinates worked out server-side from
 * `clude_core.board`, as the replay's do.
 *
 * Every look shares this script (`clude_web.styles`). Developer keeps
 * the screen Legacy was frozen with; an Engraved look (`<html
 * data-style>` other than "developer") wears Phase 10's: Talk as balloons and the Record with
 * its turn margin (10d), the stage that the focus ladder hands to
 * whatever matters most and the rail's tabs (10e), the dressed board
 * (10f). Sound (10g) is the same in both.
 */
(function () {
  "use strict";

  var node = document.getElementById("table-data");
  if (!node) return;
  var data = JSON.parse(node.textContent);
  var urls = data.urls || {};
  var csrfMeta = document.querySelector('meta[name="csrf"]');
  var csrf = csrfMeta ? csrfMeta.getAttribute("content") : "";
  var engraved = document.documentElement.getAttribute("data-style") !== "developer";

  var status = document.getElementById("status");
  var title = document.getElementById("title");
  var decision = document.getElementById("decision");
  var decisionTitle = document.getElementById("decision-title");
  var errorBox = document.getElementById("error");
  var hand = document.getElementById("hand");
  var myToken = document.getElementById("my-token");
  var autopilotButton = document.getElementById("autopilot");
  var log = document.getElementById("log");
  var talk = document.getElementById("talk");
  var watchingBox = document.getElementById("watching");
  var accusePanel = document.getElementById("accuse-panel");
  var accuseToggle = document.getElementById("accuse-toggle");
  var accuseBody = document.getElementById("accuse-body");
  var accuseHint = document.getElementById("accuse-hint");
  var sayForm = document.getElementById("say-form");
  var sayText = document.getElementById("say-text");
  var sayCount = document.getElementById("say-count");
  var typingLine = document.getElementById("typing");
  var seatsBox = document.getElementById("seats");
  var notepad = document.getElementById("notepad");
  var svg = document.querySelector("svg.board");
  /* The Engraved screen's parts (10e); all absent under Legacy. */
  var screen = document.getElementById("screen");
  var stage = document.getElementById("stage");
  var over = document.getElementById("over");
  var beatBox = document.getElementById("beat");
  var talkOver = document.getElementById("talk-over");
  var endPlate = document.getElementById("end-plate");
  var tabStrip = document.getElementById("tabs");

  var SVG_NS = "http://www.w3.org/2000/svg";
  var since = 0;
  var timer = null;
  var busy = false;
  var current = data;
  var renderedKey = null;
  var receivedAt = Date.now();
  var accuseFields = null;
  var accuseButton = null;
  var firstRender = true;

  /* suspect -> its circle on the board, and its initial (10f), looked up once. */
  var tokens = {};
  var initials = {};
  Array.prototype.forEach.call(document.querySelectorAll(".board-token"), function (circle) {
    tokens[circle.getAttribute("data-suspect")] = circle;
  });
  Array.prototype.forEach.call(document.querySelectorAll(".board-initial"), function (text) {
    initials[text.getAttribute("data-suspect")] = text;
  });

  function el(tag, className, text) {
    var e = document.createElement(tag);
    if (className) e.className = className;
    if (text !== undefined && text !== null) e.textContent = String(text);
    return e;
  }

  function cardName(card) {
    return String(card).replace("_", " ");
  }

  function seatSpec(seat) {
    var seats = current.seats || [];
    for (var i = 0; i < seats.length; i += 1) {
      if (seats[i].seat === seat) return seats[i];
    }
    return null;
  }

  function post(url, fields) {
    var body = new URLSearchParams();
    body.set("csrf", csrf);
    Object.keys(fields || {}).forEach(function (key) {
      body.set(key, fields[key]);
    });
    return fetch(url, {
      method: "POST",
      body: body,
      credentials: "same-origin",
      headers: { "Accept": "application/json" }
    }).then(handle);
  }

  function get(url) {
    return fetch(url, { credentials: "same-origin", headers: { "Accept": "application/json" } }).then(handle);
  }

  /* An expired session answers with a redirect to the login page, and a
     stale CSRF token with an HTML 400; either way the page must start
     over rather than parse HTML as JSON. */
  function handle(response) {
    var type = response.headers.get("content-type") || "";
    if (response.redirected || type.indexOf("application/json") < 0) {
      window.location.reload();
      return new Promise(function () {});
    }
    return response.json().then(function (payload) {
      if (!response.ok) {
        var err = new Error(payload.error || "Something went wrong.");
        err.payload = payload;
        throw err;
      }
      return payload;
    });
  }

  /* --- sound (10g) ---------------------------------------------------- */

  /* The cue for a batch of new events: the loudest one only, so a poll
     that brings a move, a suggestion and its refutation makes one sound,
     not three on top of each other. `static/sound.js` does the playing
     and the muting; without it, or muted, this does nothing. */
  var CUE_RANK = { accent: 3, refute: 2, turn: 1, tick: 0 };

  function cue(names) {
    if (!window.cludeSound || !names.length) return;
    var best = null;
    names.forEach(function (name) {
      if (name && (best === null || CUE_RANK[name] > CUE_RANK[best])) best = name;
    });
    if (best) window.cludeSound.play(best);
  }

  /* --- rendering ------------------------------------------------------ */

  function showError(message) {
    if (!errorBox) return;
    errorBox.textContent = message || "";
    errorBox.hidden = !message;
  }

  /* The certainty tag (Phase 9h): the seat's heading takes its colour
     from `--certainty`, 0 (clueless) to 1 (certain), and says the number
     on hover. Left plain when the server sent none. */
  function tag(h2, certainty) {
    if (certainty === null || certainty === undefined) return h2;
    var c = Math.max(0, Math.min(1, Number(certainty)));
    h2.className = (h2.className ? h2.className + " " : "") + "tag";
    h2.style.setProperty("--certainty", c.toFixed(3));
    h2.title = "certainty " + Math.round(c * 100) + "%";
    return h2;
  }

  /* Tokens move by their centre; an initial (10f) by a CSS transform,
     which unlike a text element's x and y can be transitioned, so the
     letter glides with its disc. */
  function moveTokens(points) {
    Object.keys(points || {}).forEach(function (suspect) {
      var circle = tokens[suspect];
      if (!circle) return;
      circle.setAttribute("cx", points[suspect][0]);
      circle.setAttribute("cy", points[suspect][1]);
      var letter = initials[suspect];
      if (letter) letter.style.transform = "translate(" + points[suspect][0] + "px, " + points[suspect][1] + "px)";
    });
  }

  /* The board says where everyone is (plan 12): "Mustard in the Hall,
     you in the corridor", rewritten with every payload. */
  function labelBoard(payload) {
    if (!svg || !payload.where) return;
    var mine = payload.me ? payload.me.token : null;
    var parts = Object.keys(payload.where).sort().map(function (token) {
      return (token === mine ? "you" : token) + " in " + payload.where[token];
    });
    svg.setAttribute("aria-label", "The board: " + parts.join(", ") + ".");
  }

  /* The seat now thinking wears a dashed ring on the board (10e, the
     board rank's one mark), drawn once and moved with its token. */
  var thinkingRing = null;

  function markThinking(payload) {
    if (!engraved || !svg) return;
    var w = payload.waiting;
    var spec = w && !payload.pending && !payload.finished ? seatSpec(w.seat) : null;
    var circle = spec ? tokens[spec.token] : null;
    if (!circle) {
      if (thinkingRing) thinkingRing.setAttribute("visibility", "hidden");
      return;
    }
    if (!thinkingRing) {
      thinkingRing = document.createElementNS(SVG_NS, "circle");
      thinkingRing.setAttribute("class", "board-thinking");
      svg.appendChild(thinkingRing);
    }
    thinkingRing.setAttribute("cx", circle.getAttribute("cx"));
    thinkingRing.setAttribute("cy", circle.getAttribute("cy"));
    thinkingRing.setAttribute("r", Number(circle.getAttribute("r") || 8.6) + 3.5);
    thinkingRing.setAttribute("visibility", "visible");
  }

  /* --- the Record and Talk (plan 3.3, 10d) ----------------------------- */

  /* Table talk and the Record are the same event stream on the wire; the
     server says which panel each belongs to (`panel`): every remark -- a
     person's line, a character's aside on its turn, a model seat's
     off-turn reaction -- goes to Talk, and the moves, suggestions and
     accusations to the Record. */
  var talkTurns = {};
  var lastRecordTurn = null;

  function recordLine(event) {
    var li = el("li", "kind-" + event.kind, event.text);
    li.setAttribute("data-index", event.i);
    li.setAttribute("data-turn", event.turn);
    if (engraved) {
      /* The turn number sits in the margin once per turn (the stylesheet
         prints `data-turn` on a turn's first line), with a hairline
         between turns. Kept as a running value: a batch's lines are
         made before any of them is in the list. */
      if (lastRecordTurn !== event.turn) li.className += " turn-start";
      lastRecordTurn = event.turn;
      if (talkTurns[event.turn]) addPip(li, event.turn);
    }
    return li;
  }

  /* A balloon (plan 3.3): the speaker's name over the line, their colour
     on the tail, yours on the right. */
  function balloon(event) {
    var about = event.about ? " about-" + event.about : "";
    if (!engraved) {
      var plain = el("li", "kind-" + event.kind + about, event.text);
      plain.setAttribute("data-index", event.i);
      return plain;
    }
    var spec = seatSpec(event.seat);
    var mine = !!(current.me && event.seat === current.me.seat);
    var li = el("li", "kind-" + event.kind + about + " balloon"
      + (mine ? " mine" : "") + (event.about === "reaction" ? " reaction" : ""));
    li.setAttribute("data-index", event.i);
    li.setAttribute("data-turn", event.turn);
    if (spec) li.setAttribute("data-suspect", spec.token.toLowerCase());
    var speaker = el("span", "speaker", mine ? "You" : (spec ? spec.name : ""));
    speaker.appendChild(el("span", "when", "turn " + event.turn));
    li.appendChild(speaker);
    li.appendChild(el("span", "said", event.line !== null && event.line !== undefined ? event.line : event.text));
    return li;
  }

  /* The speech pip (plan 3.3): a record line on a turn that had talk
     gets a mark that opens Talk at that turn -- the only coupling
     between the two panels. */
  function addPip(li, turn) {
    if (!li || li.querySelector(".pip-talk")) return;
    var pip = el("button", "pip-talk", "●");
    pip.type = "button";
    pip.title = "Table talk on turn " + turn;
    pip.setAttribute("aria-label", "Table talk on turn " + turn);
    pip.addEventListener("click", function () {
      setTab("talk");
      var said = talk ? talk.querySelector('li[data-turn="' + turn + '"]') : null;
      if (!said) return;
      said.scrollIntoView({ block: "nearest" });
      said.classList.remove("flash");
      void said.offsetWidth;
      said.classList.add("flash");
    });
    li.appendChild(pip);
  }

  function append(list, items, emptyText) {
    if (!list) return 0;
    var placeholder = list.querySelector(".placeholder");
    items.forEach(function (li) {
      if (placeholder) {
        list.removeChild(placeholder);
        placeholder = null;
      }
      list.appendChild(li);
    });
    if (!list.children.length) list.appendChild(el("li", "placeholder note", emptyText));
    if (items.length) list.scrollTop = list.scrollHeight;
    return items.length;
  }

  /* Adds the new events to their panels; returns what was new, split
     by panel, for the beat, the badges and the sound. */
  function appendEvents(events) {
    var fresh = (events || []).filter(function (event) { return event.i >= since; });
    var said = [];
    var played = [];
    fresh.forEach(function (event) {
      var panel = event.panel || (event.kind === "remark" ? "talk" : "record");
      (panel === "talk" ? said : played).push(event);
    });
    append(log, played.map(recordLine), "The cards are dealt. Nobody has moved yet.");
    append(talk, said.map(balloon), "Nobody has said anything yet.");
    if (engraved) {
      said.forEach(function (event) {
        if (talkTurns[event.turn]) return;
        talkTurns[event.turn] = true;
        addPip(log && log.querySelector('li.turn-start[data-turn="' + event.turn + '"]'), event.turn);
      });
    }
    return { said: said, played: played };
  }

  /* How long the seat the table waits on has left before the floor bot
     plays its turn (Phase 9h): the server's count at the last payload
     plus the time since, so the line ticks without a request. */
  function secondsLeft(payload) {
    var w = payload.waiting;
    if (!w || w.model || w.autopilot || !payload.timeout) return null;
    var elapsed = (w.seconds || 0) + (Date.now() - receivedAt) / 1000;
    return Math.max(0, Math.ceil(payload.timeout - elapsed));
  }

  function statusText(payload) {
    if (payload.broken) return "This table is broken: " + payload.broken;
    if (payload.over) {
      var who = payload.over.winner ? payload.over.winner + " wins." : "Nobody wins.";
      var e = payload.over.envelope;
      var ending = who + " It was " + e[0] + " with the " + cardName(e[1]) + " in the " + e[2] + ".";
      if (payload.wrapping_up && payload.debriefs) {
        ending += " " + payload.debriefs.pending[0] + " is writing up notes on the game.";
      } else if (payload.debriefs && payload.debriefs.done && payload.debriefs.done.length) {
        ending += " Notes written by " + payload.debriefs.done.join(", ") + ".";
      }
      return ending;
    }
    if (payload.pending) {
      switch (payload.pending.kind) {
        case "movement": return "Your move.";
        case "suggestion": return "You are in the " + payload.pending.room + ". Make a suggestion?";
        case "accusation": return "Accuse, or pass?";
        case "card_to_show": return payload.pending.shown_to_name + " named cards you hold. Show one.";
        default: return "Your decision.";
      }
    }
    if (payload.waiting) {
      var w = payload.waiting;
      var what = { movement: "move", suggestion: "suggest", accusation: "decide whether to accuse", card_to_show: "show a card" }[w.kind] || "decide";
      if (w.no_model) return w.name + " is an LLM character, but this server has no key; the table cannot go on.";
      if (w.model && w.refused) return w.name + "'s LLM budget is spent; its headless method plays on.";
      if (w.model) return w.name + " is thinking.";
      return "Waiting for " + w.name + " to " + what + (w.autopilot ? " (on autopilot)" : "") + ".";
    }
    if (payload.chatter) return "The table is talking.";
    if (payload.work) return "The table is playing.";
    return "";
  }

  /* The status line, then the time-out clock (Phase 9h) as its own
     element: red, and bright red for the last ten seconds (David,
     2026-09-29). Only the clock is rewritten each second. */
  var clock = null;

  function renderClock(payload) {
    var left = (payload.over || payload.broken) ? null : secondsLeft(payload);
    if (left === null) {
      if (clock && clock.parentNode) clock.parentNode.removeChild(clock);
      clock = null;
      return;
    }
    var mine = payload.waiting.seat === (payload.me || {}).seat;
    if (!clock) {
      clock = el("span", "clock-line");
      clock.appendChild(el("span", "clock"));
      clock.appendChild(document.createTextNode(""));
    }
    if (clock.parentNode !== status) {
      status.appendChild(document.createTextNode(" "));
      status.appendChild(clock);
    }
    var seconds = clock.firstChild;
    seconds.textContent = left + " s left";
    seconds.className = "clock" + (left <= 10 ? " urgent" : "");
    clock.lastChild.textContent = mine ? " before the floor bot moves for you." : ".";
  }

  function renderStatus(payload) {
    if (!status) return;
    status.textContent = statusText(payload);
    clock = null;
    if (screen) status.className = "status" + (payload.pending ? " yours" : payload.over ? " over" : "");
    renderClock(payload);
    if (payload.over && payload.over.replay && !payload.pending) {
      var a = el("a", null, "Open the replay");
      a.id = "replay-link";
      a.href = payload.over.replay;
      status.appendChild(document.createTextNode(" "));
      status.appendChild(a);
    }
  }

  function clearTargets() {
    if (!svg) return;
    var old = svg.querySelector("#targets");
    if (old) old.parentNode.removeChild(old);
  }

  function optionText(option) {
    if (option.move === "stay") return "Stay where you are";
    if (option.move === "secret_passage") return "Secret passage to the " + option.to;
    if (typeof option.to === "string") return "Enter the " + option.to;
    return "Corridor, row " + option.to.row + ", column " + option.to.col;
  }

  function answer(dataForAnswer) {
    if (busy) return;
    busy = true;
    showError("");
    post(urls.answer, { seq: current.pending ? current.pending.seq : -1, since: since, data: JSON.stringify(dataForAnswer) })
      .then(function (payload) {
        busy = false;
        render(payload);
        schedule();
      })
      .catch(function (err) {
        busy = false;
        showError(err.message);
        if (engraved && decision) {
          /* A refused answer shakes the decision once (plan 10). */
          decision.classList.remove("refused");
          void decision.offsetWidth;
          decision.classList.add("refused");
        }
        schedule(1000);
      });
  }

  /* "So-and-so is typing" at the other seats (Phase 9h): while the box
     holds text the page tells the server so every 4 s, and once more
     when it is emptied; sending the line clears it server-side. A ping
     is fire-and-forget -- the next poll brings back who else is typing. */
  var TYPING_PING = 4000;
  var lastPing = 0;
  var pingedOn = false;

  function pingTyping(on) {
    if (!urls.typing) return;
    var now = Date.now();
    if (on && pingedOn && now - lastPing < TYPING_PING) return;
    if (!on && !pingedOn) return;
    pingedOn = on;
    lastPing = now;
    post(urls.typing, { on: on ? "1" : "0" }).catch(function () {});
  }

  /* The say box (plan 7, 10d): a counter past 200 characters, the box
     itself stopping at 240 (the server's cap too). */
  var SAY_MAX = 240;
  var SAY_COUNT_FROM = 200;

  function countSay() {
    if (!sayCount || !sayText) return;
    var n = (sayText.value || "").length;
    sayCount.hidden = n <= SAY_COUNT_FROM;
    sayCount.textContent = n + " / " + SAY_MAX;
    sayCount.className = "count" + (n >= SAY_MAX ? " over" : "");
  }

  if (sayForm) {
    sayText.addEventListener("input", function () {
      pingTyping(!!(sayText.value || "").trim());
      countSay();
    });
    sayForm.addEventListener("submit", function (event) {
      event.preventDefault();
      var text = (sayText.value || "").trim();
      if (!text || busy) return;
      busy = true;
      pingedOn = false;
      post(urls.say, { text: text, since: since })
        .then(function (payload) {
          sayText.value = "";
          countSay();
          showError("");
          render(payload);
          schedule(300);
        })
        .catch(function (err) { showError(err.message); })
        .then(function () { busy = false; });
    });
  }

  /* One name at a time under the talk: "Ann is typing...", and with
     several on the way the line cycles through them every 2 s. */
  var typingNames = [];
  var typingIndex = 0;
  var typingTimer = null;

  function showTyping() {
    if (!typingLine) return;
    if (!typingNames.length) {
      typingLine.hidden = true;
      typingLine.textContent = "";
      if (typingTimer) { window.clearInterval(typingTimer); typingTimer = null; }
      return;
    }
    typingIndex = typingIndex % typingNames.length;
    typingLine.textContent = typingNames[typingIndex] + " is typing…";
    typingLine.hidden = false;
    if (typingNames.length > 1 && !typingTimer) {
      typingTimer = window.setInterval(function () {
        typingIndex = (typingIndex + 1) % Math.max(1, typingNames.length);
        showTyping();
      }, 2000);
    } else if (typingNames.length <= 1 && typingTimer) {
      window.clearInterval(typingTimer);
      typingTimer = null;
    }
  }

  function renderTyping(payload) {
    var names = payload.typing || [];
    if (names.join("|") !== typingNames.join("|")) {
      typingNames = names.slice();
      typingIndex = 0;
    }
    showTyping();
  }

  function select(name, items, label, value) {
    var wrap = el("label", "field", label + " ");
    var s = el("select");
    s.name = name;
    items.forEach(function (item) {
      var o = el("option", null, cardName(item));
      o.value = item;
      s.appendChild(o);
    });
    if (value && items.indexOf(value) >= 0) s.value = value;
    wrap.appendChild(s);
    return { wrap: wrap, select: s };
  }

  /* What the decision panel's dropdowns are set to right now, by name, so
     a rebuild puts them back rather than silently reverting to the first
     option under someone mid-choice. */
  function keptValues() {
    var kept = {};
    if (!decision) return kept;
    Array.prototype.forEach.call(decision.querySelectorAll("select"), function (s) {
      if (s.name) kept[s.name] = s.value;
    });
    return kept;
  }

  var SUSPECTS = ["Scarlett", "Mustard", "White", "Green", "Peacock", "Plum"];
  var WEAPONS = ["Candlestick", "Knife", "Lead_Pipe", "Revolver", "Rope", "Wrench"];
  var ROOMS = ["Kitchen", "Ballroom", "Conservatory", "Billiard", "Library", "Study", "Hall", "Lounge", "Dining"];

  /* The panel is rebuilt only when the decision itself changes.
     `seq` counts answers, not entries, so table talk and bot work leave
     it alone -- which is what stops a poll landing mid-choice from
     wiping the dropdowns under the player. */
  function decisionKey(pending) {
    if (pending) return pending.kind + "#" + pending.seq;
    if (current.over) return "over";
    return current.waiting ? "waiting#" + current.waiting.seat + current.waiting.kind : "none";
  }

  /* One choice button (plan 7): the words, and under Engraved a second
     line in the gauge face -- a room's distances, a card's "one of your
     cards" -- wrapping rather than cut. */
  function choiceButton(text, small, className) {
    var button = el("button", className || null);
    button.type = "button";
    button.appendChild(document.createTextNode(text));
    if (engraved && small) button.appendChild(el("small", null, small));
    return button;
  }

  /* A lit destination on the board: a disc under Legacy; under Engraved
     a square the size of the cell, a room's larger and dashed (plan 8),
     pulsing once as it appears. Either way one per button, clickable. */
  function target(option) {
    var shape;
    if (engraved) {
      var size = option.size || 24;
      shape = document.createElementNS(SVG_NS, "rect");
      shape.setAttribute("class", "board-target lit" + (typeof option.to === "string" ? " room" : ""));
      shape.setAttribute("x", (option.x - size / 2).toFixed(1));
      shape.setAttribute("y", (option.y - size / 2).toFixed(1));
      shape.setAttribute("width", size);
      shape.setAttribute("height", size);
    } else {
      shape = document.createElementNS(SVG_NS, "circle");
      shape.setAttribute("class", "board-target");
      shape.setAttribute("cx", option.x);
      shape.setAttribute("cy", option.y);
      shape.setAttribute("r", 9);
    }
    var tip = document.createElementNS(SVG_NS, "title");
    tip.textContent = optionText(option) + (option.distances ? " - from there: " + option.distances : "");
    shape.appendChild(tip);
    shape.addEventListener("click", function () {
      answer({ move: option.move, to: option.to });
    });
    return shape;
  }

  function renderMove(pending, buttons) {
    decisionTitle.textContent = "Your move";
    var group = null;
    if (svg) {
      group = document.createElementNS(SVG_NS, "g");
      group.setAttribute("id", "targets");
    }
    /* Under Engraved the rooms (and a passage, and staying) come first as
       a stack, then the corridor squares as a compact grid by row and
       column: a six on the corridor offers seventeen of them (10a). */
    var squares = engraved ? el("div", "options squares") : null;
    pending.options.forEach(function (option) {
      var corridor = typeof option.to !== "string" && option.move !== "stay" && option.move !== "secret_passage";
      var button;
      if (engraved && corridor) {
        button = choiceButton(option.to.row + " · " + option.to.col, "", "quiet");
        button.setAttribute("aria-label", optionText(option));
      } else {
        button = choiceButton(optionText(option), engraved && option.distances ? option.distances : "",
          option.move === "secret_passage" ? "passage" : null);
      }
      if (option.distances) button.title = "From there: " + option.distances;
      button.addEventListener("click", function () {
        answer({ move: option.move, to: option.to });
      });
      (engraved && corridor ? squares : buttons).appendChild(button);
      if (group) group.appendChild(target(option));
    });
    if (group) svg.appendChild(group);
    decision.appendChild(el("p", "note", "Click a highlighted square or room on the board, or a button."));
    decision.appendChild(buttons);
    if (squares && squares.children.length) {
      decision.appendChild(el("p", "note", "Or a corridor square, row · column:"));
      decision.appendChild(squares);
    }
  }

  function renderDecision(pending) {
    if (!decision) return;
    var key = decisionKey(pending);
    if (key === renderedKey) return;
    renderedKey = key;
    var kept = keptValues();
    while (decision.firstChild) decision.removeChild(decision.firstChild);
    clearTargets();
    if (!pending) {
      decisionTitle.textContent = current.over ? "Game over" : "Not your decision";
      if (current.over && current.over.replay) {
        var a = el("a", engraved ? "choice primary" : null, "Open the replay");
        a.href = current.over.replay;
        if (engraved) {
          a.appendChild(el("small", null, "every seat, cards face up"));
          var wrap = el("div", "options stack");
          wrap.appendChild(a);
          var lobby = el("a", "choice quiet", "Back to the lobby");
          lobby.href = "/";
          wrap.appendChild(lobby);
          decision.appendChild(wrap);
        } else {
          decision.appendChild(a);
        }
      } else {
        decision.appendChild(el("p", "note", current.waiting ? statusText(current) : "Wait for your turn."));
      }
      return;
    }
    var buttons = el("div", "options" + (engraved ? " stack" : ""));
    if (pending.kind === "movement") {
      renderMove(pending, buttons);
    } else if (pending.kind === "suggestion") {
      decisionTitle.textContent = "Suggest, in the " + pending.room;
      var suspect = select("suspect", SUSPECTS, "Suspect", kept.suspect);
      var weapon = select("weapon", WEAPONS, "Weapon", kept.weapon);
      decision.appendChild(suspect.wrap);
      decision.appendChild(weapon.wrap);
      var go = choiceButton("Suggest", "", "primary");
      go.addEventListener("click", function () {
        answer({ suspect: suspect.select.value, weapon: weapon.select.value });
      });
      var pass = choiceButton("No suggestion", "", "quiet");
      pass.addEventListener("click", function () { answer(null); });
      buttons.className = "options";
      buttons.appendChild(go);
      buttons.appendChild(pass);
      decision.appendChild(buttons);
    } else if (pending.kind === "accusation") {
      decisionTitle.textContent = "Accuse, or pass?";
      var skip = choiceButton("Pass", "", null);
      skip.addEventListener("click", function () { answer(null); });
      buttons.appendChild(skip);
      decision.appendChild(el("p", "note", "Pass unless you are sure: a wrong accusation ends your game, though you still show cards. To accuse, open the Accuse panel."));
      decision.appendChild(buttons);
    } else if (pending.kind === "card_to_show") {
      decisionTitle.textContent = "Show a card to " + pending.shown_to_name;
      pending.candidates.forEach(function (card) {
        var button = choiceButton(cardName(card), "one of your cards", engraved ? "primary" : null);
        button.addEventListener("click", function () { answer({ card: card }); });
        buttons.appendChild(button);
      });
      decision.appendChild(buttons);
      if (engraved) decision.appendChild(el("p", "note", "Only the cards that disprove it are offered; only " + pending.shown_to_name + " will see which one."));
    }
  }

  /* The Accuse panel is built once, at startup, and the render loop
     never rebuilds it -- only enables or disables its button. That is
     what makes a half-filled accusation survive everything happening at
     the table: you can set it up on turn 3 and leave it there. Under
     the rules you may only accuse at the accusation question, so the
     button stays disabled until that decision is yours. */
  function buildAccuse() {
    if (!accuseBody || !accuseToggle) return;
    var suspect = select("suspect", SUSPECTS, "Suspect");
    var weapon = select("weapon", WEAPONS, "Weapon");
    var room = select("room", ROOMS, "Room");
    accuseBody.appendChild(suspect.wrap);
    accuseBody.appendChild(weapon.wrap);
    accuseBody.appendChild(room.wrap);
    accuseFields = { suspect: suspect.select, weapon: weapon.select, room: room.select };

    accuseButton = el("button", "warn", "Accuse");
    accuseButton.type = "button";
    accuseButton.addEventListener("click", function () {
      if (accuseButton.disabled || busy) return;
      var text = accuseFields.suspect.value
        + " with the " + cardName(accuseFields.weapon.value)
        + " in the " + accuseFields.room.value;
      if (window.confirm("Accuse " + text + "? A wrong accusation puts you out of the game.")) {
        answer({
          suspect: accuseFields.suspect.value,
          weapon: accuseFields.weapon.value,
          room: accuseFields.room.value
        });
        setAccuseOpen(false);
      }
    });
    var close = el("button", "quiet", "Close");
    close.type = "button";
    close.addEventListener("click", function () { setAccuseOpen(false); });

    var buttons = el("div", "options");
    buttons.appendChild(accuseButton);
    buttons.appendChild(close);
    accuseBody.appendChild(buttons);

    accuseToggle.addEventListener("click", function () {
      setAccuseOpen(accuseBody.hidden);
    });
    setAccuseOpen(false);
  }

  function setAccuseOpen(open) {
    if (!accuseBody || !accuseToggle) return;
    accuseBody.hidden = !open;
    accuseToggle.setAttribute("aria-expanded", open ? "true" : "false");
  }

  function renderAccuse(pending) {
    if (!accuseButton) return;
    var live = !!(pending && pending.kind === "accusation");
    accuseButton.disabled = !live;
    if (accusePanel) accusePanel.className = "panel accuse-panel" + (live ? " live" : "");
    if (accuseHint) {
      accuseHint.textContent = live
        ? "This is the moment: accuse, or Pass in the decision panel."
        : "You can accuse at the end of your turn. Set your three cards here whenever you like; they will keep.";
    }
  }

  function renderHand(me) {
    if (!hand || !me) return;
    while (hand.firstChild) hand.removeChild(hand.firstChild);
    var shown = me.shown || {};
    me.hand.forEach(function (card) {
      /* A card you have shown is ticked, never removed (plan 7): the
         other seat knows it now, and so should you at a glance. */
      var seen = Object.prototype.hasOwnProperty.call(shown, card);
      var chip = el("li", "card-chip" + (seen ? " shown" : ""), cardName(card));
      if (seen) chip.title = "shown to " + shown[card];
      hand.appendChild(chip);
    });
    setBadge("hand", me.hand.length);
    if (myToken) myToken.textContent = "(" + me.token + (me.active ? "" : ", out") + ")";
    var strikesLine = document.getElementById("strikes");
    if (strikesLine) {
      var n = me.strikes || 0;
      strikesLine.hidden = !n;
      strikesLine.textContent = n
        ? "The floor bot has played " + n + (n === 1 ? " turn" : " turns in a row") + " for you after the time-out; at three it keeps your seat until you take it back."
        : "";
    }
    if (autopilotButton) {
      autopilotButton.textContent = me.autopilot ? "Take my seat back" : "Let the floor bot play for me";
      autopilotButton.onclick = function () {
        post(urls.autopilot, { seat: me.seat, on: me.autopilot ? "0" : "1" })
          .then(function (payload) { render(payload); schedule(); })
          .catch(function (err) { showError(err.message); });
      };
    }
  }

  function seatWho(spec) {
    if (spec.kind === "llm") return "LLM";
    if (spec.kind === "character") return "headless";
    if (spec.kind === "floor") return "floorbot";
    if (spec.me) return "you";
    return spec.name !== spec.token ? spec.name.replace(spec.token + " (", "").replace(/\)$/, "") : "";
  }

  /* Who else is at the table, for someone playing at it: public facts
     and nothing more (plan 3.2). The deduction bars are for someone
     watching -- at a real table nobody can see how close another player
     is to solving it -- so the server sends no readings to a seated
     viewer and this draws the roster instead (David, 2026-09-22): the
     name, a character's method (back by David's call, D8), how many
     cards the seat holds, whether it is in, out or on autopilot, the
     certainty tag (9h), and a mark on the seat the table waits on. */
  function renderRoster(payload) {
    var acting = payload.waiting ? payload.waiting.seat : (payload.pending ? payload.pending.seat : null);
    (payload.seats || []).forEach(function (spec) {
      var article = el("article", "seat compact roster"
        + (spec.active ? "" : " out") + (spec.me ? " mine" : "") + (spec.seat === acting ? " acting" : ""));
      article.setAttribute("data-seat", spec.seat);
      if (engraved) {
        seatsBox.appendChild(chip(article, spec, spec.seat === acting, payload));
        return;
      }
      var h2 = el("h2");
      h2.appendChild(el("span", "pip suspect-" + spec.token.toLowerCase()));
      h2.appendChild(document.createTextNode(" " + spec.token + " "));
      var who = seatWho(spec);
      if (who) h2.appendChild(el("span", "who", "(" + who + ")"));
      article.appendChild(tag(h2, spec.certainty));
      var facts = [];
      if (spec.method) facts.push(spec.method);
      if (spec.cards) facts.push(spec.cards + (spec.cards === 1 ? " card" : " cards"));
      if (!spec.active) facts.push("out, accused wrongly");
      if (spec.autopilot) facts.push("autopilot");
      else if (spec.strikes) facts.push("timed out ×" + spec.strikes);
      if (spec.seat === acting && spec.active) facts.push(spec.me ? "your decision" : "deciding");
      if (facts.length) article.appendChild(el("p", "method", facts.join(" · ")));
      var bar = costBar(payload, spec.seat);
      if (bar) article.appendChild(bar);
      seatsBox.appendChild(article);
    });
  }

  /* A seat on the Engraved rail (10a, 10e): the pip with the token's
     initial, the name on its certainty, the method's short form (the
     one-liner on hover, D8), and one word for its state. */
  var INITIALS = { Scarlett: "S", Mustard: "M", White: "W", Green: "G", Peacock: "Pe", Plum: "Pl" };

  function chip(article, spec, acting, payload) {
    article.appendChild(el("span", "pip suspect-" + spec.token.toLowerCase(), INITIALS[spec.token] || spec.token.charAt(0)));
    article.appendChild(tag(el("h2", null, spec.token), spec.certainty));
    if (spec.method) {
      var method = el("span", "method", spec.method_short || spec.method);
      method.title = spec.method;
      article.appendChild(method);
    }
    var state;
    if (!spec.active) state = "out";
    else if (acting) state = spec.me ? "your turn" : (payload.waiting && payload.waiting.model ? "thinking" : "deciding");
    else if (spec.autopilot) state = "autopilot";
    else if (spec.strikes) state = "timed out ×" + spec.strikes;
    else state = seatWho(spec);
    var line = el("span", "state", state);
    if (acting && spec.active && !spec.me) line.appendChild(el("span", "dots", "…"));
    article.appendChild(line);
    if (spec.cards) article.appendChild(el("span", "cards", spec.cards + (spec.cards === 1 ? " card" : " cards")));
    var bar = costBar(payload, spec.seat);
    if (bar) article.appendChild(bar);
    return article;
  }

  /* The one bar a seat's tab keeps for someone playing (Phase 9g): its
     share of what the table has spent with Claude, the model seats'
     calls and the logbook entries after the game. Only on a table with
     model seats; a seat that cannot spend -- a person, the chat seat, a
     floorbot, a headless character -- reads 0%. Solid rather than pale:
     a cost is a fact, not a belief. Engraved hides it (D9). */
  function costBar(payload, seat) {
    if (!payload.llm) return null;
    var total = Number(payload.llm.spent || 0);
    var dollars = Number((payload.llm.seats || {})[String(seat)] || 0);
    var share = total > 0 ? dollars / total : 0;
    var gauge = el("div", "gauge cost");
    gauge.appendChild(el("span", "gname", "cost"));
    var bar = el("span", "sure");
    var fill = el("span", "sure-fill");
    fill.style.width = (share * 100).toFixed(1) + "%";
    bar.appendChild(fill);
    bar.title = "$" + dollars.toFixed(2) + " of $" + total.toFixed(2) + " spent with Claude";
    gauge.appendChild(bar);
    gauge.appendChild(el("span", "pct", Math.round(share * 100) + "%"));
    return gauge;
  }

  /* Who is watching without a seat. The line is absent unless somebody
     is there, so an empty gallery says nothing at all. */
  function renderWatching(payload) {
    if (!watchingBox) return;
    var names = payload.watching || [];
    watchingBox.hidden = !names.length;
    if (!names.length) return;
    watchingBox.textContent = (names.length === 1 ? "Watching: " : "Watching (" + names.length + "): ")
      + names.join(", ");
  }

  function renderSeats(payload) {
    if (!seatsBox) return;
    while (seatsBox.firstChild) seatsBox.removeChild(seatsBox.firstChild);
    if (screen) seatsBox.classList.toggle("readings", !!payload.readings);
    if (!payload.readings) {
      renderRoster(payload);
      return;
    }
    var seatsByIndex = {};
    (payload.seats || []).forEach(function (s) { seatsByIndex[s.seat] = s; });
    (payload.readings || []).forEach(function (r) {
      var seat = seatsByIndex[r.seat] || {};
      var article = el("article", "seat compact" + (r.active ? "" : " out") + (seat.me ? " mine" : ""));
      article.setAttribute("data-seat", r.seat);
      var h2 = el("h2");
      h2.appendChild(el("span", "pip suspect-" + r.suspect.toLowerCase()));
      h2.appendChild(document.createTextNode(" " + r.suspect + " "));
      if (seat.kind === "llm" || seat.kind === "character") {
        h2.appendChild(el("span", "who", seat.kind === "llm" ? "(LLM)" : "(headless)"));
      } else if (r.label !== r.suspect) {
        h2.appendChild(el("span", "who", "(" + (seat.kind === "floor" ? "floorbot" : r.label) + (seat.me ? ", you" : "") + ")"));
      }
      h2.appendChild(el("span", "placed", r.placed + "/" + r.total));
      article.appendChild(tag(h2, r.certainty !== undefined ? r.certainty : seat.certainty));
      var method = r.method || (seat.kind === "human" ? "a person" : r.label);
      article.appendChild(el("p", "method", method + (r.active ? "" : " · out, accused wrongly") + (seat.autopilot ? " · autopilot" : "")));
      r.groups.forEach(function (g) {
        var gauge = el("div", "gauge" + (g.solved ? " solved" : ""));
        gauge.appendChild(el("span", "gname", g.name));
        var cells = el("span", "cells");
        cells.title = g.placed + " of " + g.size + " placed";
        for (var i = 0; i < g.size; i += 1) cells.appendChild(el("span", "cell" + (i < g.placed ? " on" : "")));
        gauge.appendChild(cells);
        if (g.confidence !== null && g.confidence !== undefined) {
          var sure = el("span", "sure");
          var fill = el("span", "sure-fill");
          fill.style.width = (g.confidence * 100).toFixed(1) + "%";
          sure.appendChild(fill);
          sure.title = "its best guess, " + Math.round(g.confidence * 100) + "% sure";
          gauge.appendChild(sure);
          gauge.appendChild(el("span", "pct", Math.round(g.confidence * 100) + "%"));
        } else {
          gauge.appendChild(el("span", "sure none"));
          gauge.appendChild(el("span", "pct note", "–"));
        }
        article.appendChild(gauge);
      });
      var bar = costBar(payload, r.seat);
      if (bar) article.appendChild(bar);
      seatsBox.appendChild(article);
    });
  }

  function renderNotepad(payload) {
    if (!notepad || !payload.notepad) return;
    while (notepad.firstChild) notepad.removeChild(notepad.firstChild);
    var seats = payload.seats || [];
    var head = el("tr");
    head.appendChild(el("th", null, "card"));
    seats.forEach(function (s) { head.appendChild(el("th", null, s.token.slice(0, 3))); });
    head.appendChild(el("th", null, "env"));
    notepad.appendChild(head);
    var lastCategory = null;
    payload.notepad.forEach(function (row) {
      if (row.category !== lastCategory) {
        var divider = el("tr", "category");
        var th = el("th", null, row.category);
        th.colSpan = seats.length + 2;
        divider.appendChild(th);
        notepad.appendChild(divider);
        lastCategory = row.category;
      }
      var tr = el("tr", row.holder === null ? "open" : (row.holder === "envelope" ? "placed solved" : "placed"));
      tr.appendChild(el("td", "card", cardName(row.card)));
      seats.forEach(function (s) {
        var cell;
        if (row.holder === s.seat) cell = el("td", "holder", "■");
        else if (row.holder === null && row.possible.indexOf(s.seat) >= 0) cell = el("td", "maybe", "·");
        else cell = el("td", "no", "");
        tr.appendChild(cell);
      });
      var env;
      if (row.holder === "envelope") env = el("td", "holder envelope", "■");
      else if (row.holder === null && row.envelope) env = el("td", "maybe", "·");
      else env = el("td", "no", "");
      tr.appendChild(env);
      notepad.appendChild(tr);
    });
  }

  /* --- the rail's tabs (plan 6, 10e) ---------------------------------- */

  /* On a phone the rail is a tab strip -- Talk, Record, Hand, Notes --
     with one panel open beneath; wider screens show every panel and the
     stylesheet hides the strip. Each tab says what it holds back: a
     count of unread lines on Talk, a dot on Record. The tab is
     remembered on this device; the page works without it. */
  var TAB_KEY = "clude.table.tab";
  var unreadTalk = 0;

  /* The tab button first, then its mark: `#screen` carries a
     `data-tab` too, so a bare `[data-tab=...] .badge` would match every
     badge under the screen once that tab was open. */
  function badgeOf(name) {
    var tab = tabStrip ? tabStrip.querySelector('.tab[data-tab="' + name + '"]') : null;
    return tab ? tab.querySelector(".badge, .dot") : null;
  }

  function setBadge(name, value) {
    var badge = badgeOf(name);
    if (!badge) return;
    badge.hidden = !value;
    if (badge.className === "badge") badge.textContent = value ? String(value) : "";
  }

  function currentTab() {
    return screen ? screen.getAttribute("data-tab") : null;
  }

  function setTab(name) {
    if (!screen || !tabStrip) return;
    if (!tabStrip.querySelector('[data-tab="' + name + '"]')) return;
    screen.setAttribute("data-tab", name);
    Array.prototype.forEach.call(tabStrip.querySelectorAll(".tab"), function (button) {
      var on = button.getAttribute("data-tab") === name;
      button.classList.toggle("active", on);
      button.setAttribute("aria-pressed", on ? "true" : "false");
    });
    var panel = screen.querySelector('.col-side > [data-tab="' + name + '"]');
    if (panel && panel.tagName === "DETAILS") panel.open = true;
    if (name === "talk") { unreadTalk = 0; setBadge("talk", 0); }
    if (name === "record") setBadge("record", 0);
    try { window.localStorage.setItem(TAB_KEY, name); } catch (e) { /* private window */ }
  }

  function noteUnread(fresh) {
    if (!tabStrip || firstRender) return;
    if (fresh.said.length && currentTab() !== "talk") {
      unreadTalk += fresh.said.length;
      setBadge("talk", unreadTalk);
    }
    if (fresh.played.length && currentTab() !== "record") setBadge("record", 1);
  }

  if (tabStrip) {
    tabStrip.addEventListener("click", function (event) {
      var button = event.target.closest ? event.target.closest(".tab") : null;
      if (button) setTab(button.getAttribute("data-tab"));
    });
    var remembered = null;
    try { remembered = window.localStorage.getItem(TAB_KEY); } catch (e) { remembered = null; }
    setTab(remembered || currentTab() || "record");
  }

  /* --- the stage and the focus ladder (plan 3.1, 10e) ------------------ */

  /* The server sends the ranks it can see (`focus`: show, end, move,
     decide, board). This lays the two it cannot over `board`: a beat,
     the narration caption for 2.2 s after a suggestion or an
     accusation arrives, and talk, the last two balloons for 6 s after a
     line. A decision of the viewer's locks both out, so the stage never
     changes under their hand -- except for the accusation's impact
     frame, which outranks all but a card to show. Esc ends either early. */
  var BEAT_MS = 2200;
  var TALK_MS = 6000;
  var beat = null;
  var talkUntil = 0;
  var focusTimer = null;

  function focusFor(payload, now) {
    var f = payload.focus || "board";
    if (f === "show" || f === "end") return f;
    if (beat && beat.until > now && beat.event.kind === "accusation") return "beat";
    if (f !== "board") return f;
    if (beat && beat.until > now) return "beat";
    if (talkUntil > now) return "talk";
    return "board";
  }

  function caption(kicker, text, seat, kind) {
    while (beatBox.firstChild) beatBox.removeChild(beatBox.firstChild);
    beatBox.appendChild(el("span", "turn", kicker));
    beatBox.appendChild(document.createTextNode(text));
    var spec = seat === null || seat === undefined ? null : seatSpec(seat);
    if (spec) beatBox.setAttribute("data-suspect", spec.token.toLowerCase());
    else beatBox.removeAttribute("data-suspect");
    beatBox.className = "beat" + (kind ? " " + kind : "");
    beatBox.setAttribute("aria-live", kind === "accusation" ? "assertive" : "polite");
    beatBox.hidden = false;
  }

  function fillStage(focus, payload) {
    if (!over) return;
    var dim = focus === "show" || focus === "end" || focus === "beat" || focus === "talk";
    stage.classList.toggle("dimmed", dim);
    over.hidden = !dim;
    over.className = "over" + (focus === "talk" ? " bottom" : "");
    beatBox.hidden = true;
    if (talkOver) talkOver.hidden = focus !== "talk";
    if (endPlate) endPlate.hidden = focus !== "end";
    if (focus === "show" && payload.pending) {
      caption("Show a card", payload.pending.shown_to_name + " named cards you hold: "
        + payload.pending.candidates.map(cardName).join(", ") + ".", payload.pending.shown_to, "suggestion");
    } else if (focus === "beat" && beat) {
      caption("Turn " + beat.event.turn + " · " + beat.event.kind, beat.event.text, beat.event.seat, beat.event.kind);
    } else if (focus === "end" && endPlate && payload.over) {
      var e = payload.over.envelope;
      var envelope = document.getElementById("envelope");
      while (envelope.firstChild) envelope.removeChild(envelope.firstChild);
      envelope.appendChild(document.createTextNode(e[0]));
      envelope.appendChild(el("small", null, "with the"));
      envelope.appendChild(document.createTextNode(cardName(e[1])));
      envelope.appendChild(el("small", null, "in the"));
      envelope.appendChild(document.createTextNode(e[2]));
      document.getElementById("winner").textContent = payload.over.winner
        ? payload.over.winner + " wins on turn " + payload.turns + "."
        : "Nobody wins: every accusation was wrong.";
    } else if (focus === "talk" && talkOver && talk) {
      while (talkOver.firstChild) talkOver.removeChild(talkOver.firstChild);
      var said = talk.querySelectorAll("li.balloon");
      for (var i = Math.max(0, said.length - 2); i < said.length; i += 1) talkOver.appendChild(said[i].cloneNode(true));
    }
  }

  /* A panel cut (plan 11): the stage clips in from the right at
     `--dur-cut`, never a crossfade; nothing moves with motion off. */
  function cut() {
    if (!stage) return;
    stage.classList.remove("cut");
    void stage.offsetWidth;
    stage.classList.add("cut");
  }

  function applyFocus() {
    if (!screen) return;
    if (focusTimer) { window.clearTimeout(focusTimer); focusTimer = null; }
    var now = Date.now();
    var focus = focusFor(current, now);
    var was = screen.getAttribute("data-focus");
    if (was !== focus) {
      screen.setAttribute("data-focus", focus);
      if (!firstRender) cut();
    }
    fillStage(focus, current);
    var next = Math.min(beat && beat.until > now ? beat.until : Infinity, talkUntil > now ? talkUntil : Infinity);
    if (next !== Infinity) focusTimer = window.setTimeout(applyFocus, next - now + 20);
  }

  /* The one impact frame (plan 4, 11): an accusation lands, the board
     flashes to ink and the caption in the hero size. */
  function impact() {
    if (!stage) return;
    stage.classList.remove("impact");
    void stage.offsetWidth;
    stage.classList.add("impact");
  }

  function noteStage(fresh) {
    if (!screen || firstRender) return;
    var now = Date.now();
    var loud = null;
    fresh.played.forEach(function (event) {
      if (event.kind === "suggestion" || event.kind === "accusation") loud = event;
    });
    if (loud) {
      beat = { event: loud, until: now + BEAT_MS };
      if (loud.kind === "accusation") impact();
    }
    if (fresh.said.length) talkUntil = now + TALK_MS;
  }

  document.addEventListener("keydown", function (event) {
    if (event.key !== "Escape" || !screen) return;
    if ((beat && beat.until > Date.now()) || talkUntil > Date.now()) {
      beat = null;
      talkUntil = 0;
      applyFocus();
    }
  });

  /* --- one payload ----------------------------------------------------- */

  var lastPendingKey = null;

  function render(payload) {
    current = payload;
    receivedAt = Date.now();
    if (title) title.textContent = "Turn " + payload.turns;
    moveTokens(payload.tokens);
    labelBoard(payload);
    var fresh = appendEvents(payload.events);
    since = Math.max(since, payload.n_events || 0);
    renderStatus(payload);
    var spend = document.getElementById("spend");
    if (spend) spend.textContent = spendText(payload);
    renderDecision(payload.pending);
    renderAccuse(payload.pending);
    renderHand(payload.me);
    renderWatching(payload);
    renderTyping(payload);
    renderSeats(payload);
    renderNotepad(payload);
    markThinking(payload);
    noteUnread(fresh);
    noteStage(fresh);
    applyFocus();
    /* Sound (10g): one cue per batch of new events, and the turn cue
       when a decision newly becomes the viewer's. Silent on the first
       paint and on every reload, which is also a first paint. */
    var pendingKey = payload.pending ? payload.pending.kind + "#" + payload.pending.seq : null;
    if (!firstRender) {
      var cues = fresh.played.map(function (event) { return event.cue; });
      if (pendingKey && pendingKey !== lastPendingKey) cues.push("turn");
      cue(cues);
    }
    lastPendingKey = pendingKey;
    firstRender = false;
  }

  /* --- polling and work ---------------------------------------------- */

  function spendText(payload) {
    if (!payload.llm) return "";
    var refused = payload.llm.refused || {};
    var out = "Model spend $" + Number(payload.llm.spent || 0).toFixed(2) + " of $" + Number(payload.llm.budget || 0).toFixed(2) + ".";
    Object.keys(refused).forEach(function (seat) { out += " " + refused[seat] + "."; });
    return out;
  }

  function interval() {
    if (current.finished && !current.work) return 0;
    if (current.work) return 1500;
    if (current.typing && current.typing.length) return 3000;
    if (current.pending) return 10000;
    return 4000;
  }

  function tick() {
    timer = null;
    if (document.hidden) { schedule(15000); return; }
    var request;
    /* A finished table still needs work while it wraps up: each debrief
       runs inside a /work request from whoever has the page open. */
    if (current.work && (!current.finished || current.wrapping_up)) {
      request = post(urls.work, { since: since });
    } else {
      request = get(urls.poll + "?since=" + since);
    }
    request
      .then(function (payload) {
        render(payload);
        schedule();
      })
      .catch(function (err) {
        showError(err.message);
        schedule(5000);
      });
  }

  /* The next poll lands at the deadline when the table waits on a
     person (Phase 9h): the floor bot plays only inside a /work request,
     so whichever page sees the time run out -- the stalling player's own
     included -- posts for it rather than waiting a whole interval. */
  function untilDeadline() {
    var left = secondsLeft(current);
    if (left === null) return null;
    return Math.max(500, left * 1000 + 250);
  }

  function schedule(delay) {
    if (timer) window.clearTimeout(timer);
    var wait = delay !== undefined ? delay : interval();
    if (!wait) return;
    var deadline = delay === undefined ? untilDeadline() : null;
    if (deadline !== null && deadline < wait) wait = deadline;
    timer = window.setTimeout(tick, wait);
  }

  /* The clock ticks once a second without a request. */
  window.setInterval(function () {
    if (status && current && secondsLeft(current) !== null) renderClock(current);
  }, 1000);

  document.addEventListener("visibilitychange", function () {
    if (!document.hidden) schedule(200);
  });

  Array.prototype.forEach.call(document.querySelectorAll("details.panel"), function (panel) {
    panel.addEventListener("toggle", function () {
      if (!panel.open) return;
      var list = panel.querySelector("ol");
      if (list) list.scrollTop = list.scrollHeight;
    });
  });

  buildAccuse();
  render(data);
  schedule(current.work ? 300 : undefined);
})();
