/* Sound effects (Phase 10g, docs/phase10-plan.md 11.1).
 *
 * Six short cues, self-hosted under static/sounds/ and made by
 * scripts/make_sounds.py: `tick` (a move, or a suggestion nobody could
 * disprove), `refute` (a suggestion somebody disproved), `turn` (a
 * decision just became yours), `accent` (an accusation, the end), and
 * since 2026-10-01 `door` (a token going into a room through a door)
 * and `passage` (one taking a secret passage). No music.
 *
 * The rules, all kept here or by the pages that call `play`:
 * - Muted until the viewer turns it on; the toggle and the volume are
 *   remembered on this device. A page with no storage, or a browser
 *   that refuses to play, goes on silently.
 * - A cue follows only an event the viewer can already see on the
 *   screen, and never says more than its line does.
 * - One cue per event: the pages cue only what is new since their last
 *   paint, so a poll, a reload, a first paint or a hand on the replay's
 *   scrubber makes no sound; a batch of events makes one sound, its
 *   loudest; and a cue within `GAP_MS` of another is dropped unless it
 *   outranks it, so fast replay playback does not rattle.
 * - Automated runs stay silent, since nothing turns it on.
 *
 * `window.cludeSound.played` lists every cue actually sent to the
 * speaker, which is what the browser tests read.
 */
(function () {
  "use strict";

  var KEY_ON = "clude.sound.on";
  var KEY_VOLUME = "clude.sound.volume";
  var NAMES = ["tick", "turn", "refute", "accent", "door", "passage"];
  var RANK = { tick: 0, door: 1, passage: 1, turn: 2, refute: 3, accent: 4 };
  var GAP_MS = 150;
  var DEFAULT_VOLUME = 0.6;

  var script = document.currentScript;
  var base = script && script.src ? script.src.replace(/sound\.js(\?.*)?$/, "sounds/") : "/static/sounds/";

  function read(key) {
    try { return window.localStorage.getItem(key); } catch (e) { return null; }
  }

  function write(key, value) {
    try { window.localStorage.setItem(key, value); } catch (e) { /* private window */ }
  }

  var on = read(KEY_ON) === "1";
  var stored = Number(read(KEY_VOLUME));
  var volume = read(KEY_VOLUME) !== null && isFinite(stored) ? Math.max(0, Math.min(1, stored)) : DEFAULT_VOLUME;
  var clips = {};
  var lastAt = 0;
  var lastRank = -1;
  var played = [];

  function clip(name) {
    if (!clips[name] && typeof window.Audio === "function") {
      var audio = new window.Audio(base + name + ".wav");
      audio.preload = "auto";
      clips[name] = audio;
    }
    return clips[name];
  }

  /* Plays `name` if sound is on and it is not drowned by the gap rule;
     returns whether it was sent to the speaker. */
  function play(name) {
    if (!on || !Object.prototype.hasOwnProperty.call(RANK, name)) return false;
    var now = Date.now();
    if (now - lastAt < GAP_MS && RANK[name] <= lastRank) return false;
    lastAt = now;
    lastRank = RANK[name];
    played.push(name);
    try {
      var audio = clip(name);
      if (!audio) return true;
      audio.volume = volume;
      audio.currentTime = 0;
      var promise = audio.play();
      if (promise && promise.catch) promise.catch(function () {});
    } catch (e) { /* no audio here; the screen carries on */ }
    return true;
  }

  var toggle = document.getElementById("sound-toggle");
  var slider = document.getElementById("sound-volume");

  function show() {
    if (toggle) {
      toggle.textContent = on ? "Sound on" : "Sound off";
      toggle.setAttribute("aria-pressed", on ? "true" : "false");
    }
    if (slider) {
      slider.hidden = !on;
      slider.value = String(Math.round(volume * 100));
    }
  }

  function setOn(value) {
    on = !!value;
    write(KEY_ON, on ? "1" : "0");
    if (on) NAMES.forEach(clip);
    show();
  }

  function setVolume(value) {
    volume = Math.max(0, Math.min(1, Number(value) || 0));
    write(KEY_VOLUME, String(volume));
    show();
  }

  if (toggle) {
    toggle.addEventListener("click", function () {
      setOn(!on);
      /* The click is the gesture a browser wants before it plays
         anything; a tick says it worked. */
      if (on) { lastAt = 0; play("tick"); }
    });
  }
  if (slider) {
    slider.addEventListener("input", function () { setVolume(Number(slider.value) / 100); });
    slider.addEventListener("change", function () { lastAt = 0; play("tick"); });
  }
  show();

  window.cludeSound = {
    play: play,
    setOn: setOn,
    setVolume: setVolume,
    isOn: function () { return on; },
    played: played
  };

  /* Watch moves a turn per page (Phase 8.1): the page names its newest
     cue and a key for it, and the cue plays once -- not on a reload,
     not when the page is opened again later. */
  var marked = document.querySelector("[data-cue-key]");
  if (marked) {
    var key = "clude.cued." + marked.getAttribute("data-cue-key");
    var seen = null;
    try { seen = window.sessionStorage.getItem(key); } catch (e) { seen = "1"; }
    var navigation = window.performance && performance.getEntriesByType ? performance.getEntriesByType("navigation")[0] : null;
    var reloaded = navigation && navigation.type === "reload";
    if (!seen && !reloaded && marked.getAttribute("data-cue")) play(marked.getAttribute("data-cue"));
    try { window.sessionStorage.setItem(key, "1"); } catch (e) { /* nothing to remember with */ }
  }
})();
