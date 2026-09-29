/* The table screen (Phase 8.2).
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
 */
(function () {
  "use strict";

  var node = document.getElementById("table-data");
  if (!node) return;
  var data = JSON.parse(node.textContent);
  var urls = data.urls || {};
  var csrfMeta = document.querySelector('meta[name="csrf"]');
  var csrf = csrfMeta ? csrfMeta.getAttribute("content") : "";

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
  var typingLine = document.getElementById("typing");
  var seatsBox = document.getElementById("seats");
  var notepad = document.getElementById("notepad");
  var svg = document.querySelector("svg.board");

  var since = 0;
  var timer = null;
  var busy = false;
  var current = data;
  var renderedKey = null;
  var receivedAt = Date.now();
  var accuseFields = null;
  var accuseButton = null;

  /* suspect -> its circle on the board, looked up once. */
  var tokens = {};
  Array.prototype.forEach.call(document.querySelectorAll(".board-token"), function (circle) {
    tokens[circle.getAttribute("data-suspect")] = circle;
  });

  function el(tag, className, text) {
    var e = document.createElement(tag);
    if (className) e.className = className;
    if (text !== undefined && text !== null) e.textContent = String(text);
    return e;
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

  function moveTokens(points) {
    Object.keys(points || {}).forEach(function (suspect) {
      var circle = tokens[suspect];
      if (!circle) return;
      circle.setAttribute("cx", points[suspect][0]);
      circle.setAttribute("cy", points[suspect][1]);
    });
  }

  /* Table talk and the narration are the same RemarkEvent stream on the
     wire, told apart by kind: every remark -- a person's line, a
     character's aside on its turn, a model seat's off-turn reaction --
     goes to Table Talk, and the moves, suggestions and accusations stay
     in the game log. */
  function appendTo(list, events, emptyText) {
    if (!list) return;
    var placeholder = list.querySelector(".placeholder");
    var added = 0;
    events.forEach(function (event) {
      if (placeholder) {
        list.removeChild(placeholder);
        placeholder = null;
      }
      var className = "kind-" + event.kind + (event.about ? " about-" + event.about : "");
      var li = el("li", className, event.text);
      li.setAttribute("data-index", event.i);
      list.appendChild(li);
      added += 1;
    });
    if (!list.children.length) {
      list.appendChild(el("li", "placeholder note", emptyText));
    }
    if (added) list.scrollTop = list.scrollHeight;
  }

  function appendEvents(events) {
    var fresh = (events || []).filter(function (event) { return event.i >= since; });
    var said = [];
    var played = [];
    fresh.forEach(function (event) {
      (event.kind === "remark" ? said : played).push(event);
    });
    appendTo(log, played, "The cards are dealt. Nobody has moved yet.");
    appendTo(talk, said, "Nobody has said anything yet.");
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

  function clockText(payload) {
    var left = secondsLeft(payload);
    if (left === null) return "";
    return " " + left + " s left" + (payload.waiting.seat === (payload.me || {}).seat ? " before the floor bot moves for you." : ".");
  }

  function statusText(payload) {
    if (payload.broken) return "This table is broken: " + payload.broken;
    if (payload.over) {
      var who = payload.over.winner ? payload.over.winner + " wins." : "Nobody wins.";
      var e = payload.over.envelope;
      var ending = who + " It was " + e[0] + " with the " + e[1] + " in the " + e[2] + ".";
      if (payload.wrapping_up && payload.debriefs) {
        ending += " " + payload.debriefs.pending[0] + " is writing up notes on the game.";
      } else if (payload.debriefs && payload.debriefs.done && payload.debriefs.done.length) {
        ending += " Notes written by " + payload.debriefs.done.join(", ") + ".";
      }
      return ending;
    }
    if (payload.pending) {
      var mine;
      switch (payload.pending.kind) {
        case "movement": mine = "Your move."; break;
        case "suggestion": mine = "You are in the " + payload.pending.room + ". Make a suggestion?"; break;
        case "accusation": mine = "Accuse, or pass?"; break;
        case "card_to_show": mine = payload.pending.shown_to_name + " named cards you hold. Show one."; break;
        default: mine = "Your decision.";
      }
      return mine + clockText(payload);
    }
    if (payload.waiting) {
      var w = payload.waiting;
      var what = { movement: "move", suggestion: "suggest", accusation: "decide whether to accuse", card_to_show: "show a card" }[w.kind] || "decide";
      if (w.no_model) return w.name + " is an LLM character, but this server has no key; the table cannot go on.";
      if (w.model && w.refused) return w.name + "'s LLM budget is spent; its headless method plays on.";
      if (w.model) return w.name + " is thinking.";
      return "Waiting for " + w.name + " to " + what + (w.autopilot ? " (on autopilot)" : "") + "." + clockText(payload);
    }
    if (payload.chatter) return "The table is talking.";
    if (payload.work) return "The table is playing.";
    return "";
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

  if (sayForm) {
    sayText.addEventListener("input", function () {
      pingTyping(!!(sayText.value || "").trim());
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
    typingLine.textContent = typingNames[typingIndex] + " is typing\u2026";
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
      var o = el("option", null, item.replace("_", " "));
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
        var a = el("a", null, "Open the replay");
        a.href = current.over.replay;
        decision.appendChild(a);
      } else {
        decision.appendChild(el("p", "note", current.waiting ? statusText(current) : "Wait for your turn."));
      }
      return;
    }
    var buttons = el("div", "options");
    if (pending.kind === "movement") {
      decisionTitle.textContent = "Your move";
      var group = null;
      if (svg) {
        group = document.createElementNS("http://www.w3.org/2000/svg", "g");
        group.setAttribute("id", "targets");
      }
      pending.options.forEach(function (option) {
        var button = el("button", null, optionText(option));
        button.type = "button";
        if (option.distances) button.title = "From there: " + option.distances;
        button.addEventListener("click", function () {
          answer({ move: option.move, to: option.to });
        });
        buttons.appendChild(button);
        if (group) {
          var circle = document.createElementNS("http://www.w3.org/2000/svg", "circle");
          circle.setAttribute("class", "board-target");
          circle.setAttribute("cx", option.x);
          circle.setAttribute("cy", option.y);
          circle.setAttribute("r", 9);
          var tip = document.createElementNS("http://www.w3.org/2000/svg", "title");
          tip.textContent = optionText(option) + (option.distances ? " - from there: " + option.distances : "");
          circle.appendChild(tip);
          circle.addEventListener("click", function () {
            answer({ move: option.move, to: option.to });
          });
          group.appendChild(circle);
        }
      });
      if (group) svg.appendChild(group);
      decision.appendChild(el("p", "note", "Click a highlighted square or room on the board, or a button."));
      decision.appendChild(buttons);
    } else if (pending.kind === "suggestion") {
      decisionTitle.textContent = "Suggest, in the " + pending.room;
      var suspect = select("suspect", SUSPECTS, "Suspect", kept.suspect);
      var weapon = select("weapon", WEAPONS, "Weapon", kept.weapon);
      decision.appendChild(suspect.wrap);
      decision.appendChild(weapon.wrap);
      var go = el("button", null, "Suggest");
      go.type = "button";
      go.addEventListener("click", function () {
        answer({ suspect: suspect.select.value, weapon: weapon.select.value });
      });
      var pass = el("button", "quiet", "No suggestion");
      pass.type = "button";
      pass.addEventListener("click", function () { answer(null); });
      buttons.appendChild(go);
      buttons.appendChild(pass);
      decision.appendChild(buttons);
    } else if (pending.kind === "accusation") {
      decisionTitle.textContent = "Accuse, or pass?";
      var skip = el("button", null, "Pass");
      skip.type = "button";
      skip.addEventListener("click", function () { answer(null); });
      buttons.appendChild(skip);
      decision.appendChild(el("p", "note", "Pass unless you are sure: a wrong accusation ends your game, though you still show cards. To accuse, open the Accuse panel."));
      decision.appendChild(buttons);
    } else if (pending.kind === "card_to_show") {
      decisionTitle.textContent = "Show a card to " + pending.shown_to_name;
      pending.candidates.forEach(function (card) {
        var button = el("button", null, card.replace("_", " "));
        button.type = "button";
        button.addEventListener("click", function () { answer({ card: card }); });
        buttons.appendChild(button);
      });
      decision.appendChild(buttons);
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
        + " with the " + accuseFields.weapon.value.replace("_", " ")
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
      var chip = el("li", "card-chip" + (seen ? " shown" : ""), card.replace("_", " "));
      if (seen) chip.title = "shown to " + shown[card];
      hand.appendChild(chip);
    });
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
      var h2 = el("h2");
      h2.appendChild(el("span", "pip suspect-" + spec.token.toLowerCase()));
      h2.appendChild(document.createTextNode(" " + spec.token + " "));
      var who = "";
      if (spec.kind === "llm") who = "(LLM)";
      else if (spec.kind === "character") who = "(headless)";
      else if (spec.kind === "floor") who = "(floorbot)";
      else if (spec.me) who = "(you)";
      else if (spec.name !== spec.token) who = "(" + spec.name + ")";
      if (who) h2.appendChild(el("span", "who", who));
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

  /* The one bar a seat's tab keeps for someone playing (Phase 9g): its
     share of what the table has spent with Claude, the model seats'
     calls and the logbook entries after the game. Only on a table with
     model seats; a seat that cannot spend -- a person, the chat seat, a
     floorbot, a headless character -- reads 0%. Solid rather than pale:
     a cost is a fact, not a belief. */
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
      var tr = el("tr", row.holder === null ? "open" : "placed");
      tr.appendChild(el("td", "card", row.card.replace("_", " ")));
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

  function render(payload) {
    current = payload;
    receivedAt = Date.now();
    if (title) title.textContent = "Turn " + payload.turns;
    moveTokens(payload.tokens);
    appendEvents(payload.events);
    since = Math.max(since, payload.n_events || 0);
    if (status) status.textContent = statusText(payload);
    var spend = document.getElementById("spend");
    if (spend) spend.textContent = spendText(payload);
    renderDecision(payload.pending);
    renderAccuse(payload.pending);
    renderHand(payload.me);
    renderWatching(payload);
    renderTyping(payload);
    renderSeats(payload);
    renderNotepad(payload);
    if (payload.over && payload.over.replay && !payload.pending) {
      var link = document.getElementById("replay-link");
      if (!link && status) {
        var a = el("a", null, "Open the replay");
        a.id = "replay-link";
        a.href = payload.over.replay;
        status.appendChild(document.createTextNode(" "));
        status.appendChild(a);
      }
    }
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

  /* The status line's clock ticks once a second without a request. */
  window.setInterval(function () {
    if (status && current && secondsLeft(current) !== null) status.textContent = statusText(current);
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
