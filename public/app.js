(() => {
  "use strict";
  const storageKey = "little-notes.v1";
  const warning = document.querySelector("#storage-warning");
  let notes = [];
  let removedNote = null;
  let notificationTimer;

  function showWarning(message) {
    warning.textContent = message;
    warning.hidden = false;
  }

  try {
    const stored = JSON.parse(localStorage.getItem(storageKey) || "[]");
    if (
      !Array.isArray(stored) ||
      stored.length > 100 ||
      !stored.every(
        (note) =>
          note &&
          typeof note.id === "string" &&
          typeof note.title === "string" &&
          typeof note.body === "string" &&
          note.title.length <= 80 &&
          note.body.length <= 2000 &&
          Number.isFinite(note.createdAt) &&
          !Number.isNaN(new Date(note.createdAt).getTime()),
      )
    )
      throw new Error("Invalid saved notes");
    notes = stored;
  } catch {
    showWarning(
      "Your saved notes could not be read. Browser storage may be unavailable. Saving a new note will try to start a new notebook.",
    );
  }

  document.querySelectorAll("[data-year]").forEach((element) => {
    element.textContent = new Date().getFullYear();
  });

  function save(nextNotes) {
    try {
      localStorage.setItem(storageKey, JSON.stringify(nextNotes));
      notes = nextNotes;
      warning.hidden = true;
      return true;
    } catch {
      showWarning(
        "This browser couldn’t save your change. Your notes have not been changed. Check that browser storage is available and try again.",
      );
      return false;
    }
  }

  function notify(message, undo = false) {
    const notification = document.querySelector("#notification");
    if (!notification) return;
    clearTimeout(notificationTimer);
    document.querySelector("#notification-text").textContent = message;
    document.querySelector("#undo-delete").hidden = !undo;
    notification.hidden = false;
    if (!undo)
      notificationTimer = setTimeout(() => {
        notification.hidden = true;
      }, 3500);
  }

  function card(note, compact = false) {
    const article = document.createElement("article");
    article.className = "note-card";
    const heading = document.createElement("h3");
    heading.textContent = note.title;
    const body = document.createElement("p");
    body.textContent = note.body;
    const footer = document.createElement("footer");
    const time = document.createElement("time");
    time.dateTime = new Date(note.createdAt).toISOString();
    time.textContent = new Date(note.createdAt).toLocaleDateString(undefined, {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
    footer.append(time);
    if (compact) {
      const link = document.createElement("a");
      link.href = "notes.html";
      link.className = "text-link";
      link.textContent = "Open ↗";
      link.setAttribute("aria-label", `Open notebook to read ${note.title}`);
      footer.append(link);
    } else {
      const button = document.createElement("button");
      button.className = "delete-note";
      button.type = "button";
      button.textContent = "Delete";
      button.setAttribute("aria-label", `Delete note: ${note.title}`);
      button.addEventListener("click", () => {
        const index = notes.findIndex((item) => item.id === note.id);
        if (index === -1) return;
        if (save(notes.filter((item) => item.id !== note.id))) {
          removedNote = { note, index };
          render();
          notify("Note deleted.", true);
          document.querySelector("#undo-delete").focus();
        }
      });
      footer.append(button);
    }
    article.append(heading, body, footer);
    return article;
  }

  function render() {
    const count = `${notes.length} ${notes.length === 1 ? "note" : "notes"}`;
    if (document.body.dataset.page === "home") {
      document.querySelector("#note-count").textContent = notes.length;
      document.querySelector("#note-count-label").textContent = notes.length
        ? `${count} worth coming back to`
        : "notes, ready for a little inspiration";
      if (notes.length) {
        document
          .querySelector("#recent-notes")
          .replaceChildren(
            ...notes.slice(0, 2).map((note) => card(note, true)),
          );
        document.querySelector(".hero .button").firstChild.textContent =
          "Write a new note ";
      }
    } else {
      document.querySelector("#collection-count").textContent = count;
      document
        .querySelector("#notes-grid")
        .replaceChildren(...notes.map((note) => card(note)));
      document.querySelector("#empty-notes").hidden = notes.length > 0;
    }
  }

  const form = document.querySelector("#note-form");
  if (form) {
    const title = form.elements.title;
    const body = form.elements.body;
    const counter = document.querySelector("#character-count");
    body.addEventListener("input", () => {
      counter.textContent = body.value.length.toLocaleString();
    });
    title.addEventListener("input", () => title.setCustomValidity(""));
    body.addEventListener("input", () => body.setCustomValidity(""));
    form.addEventListener("submit", (event) => {
      event.preventDefault();
      title.setCustomValidity(
        title.value.trim() ? "" : "Please give your note a title.",
      );
      body.setCustomValidity(
        body.value.trim() ? "" : "Write something in your note first.",
      );
      if (!form.reportValidity()) return;
      if (notes.length >= 100) {
        showWarning(
          "This little notebook holds 100 notes. Delete a note to make space.",
        );
        return;
      }
      const id = Array.from(
        crypto.getRandomValues(new Uint8Array(16)),
        (byte) => byte.toString(16).padStart(2, "0"),
      ).join("");
      const note = {
        id,
        title: title.value.trim(),
        body: body.value.trim(),
        createdAt: Date.now(),
      };
      if (!save([note, ...notes])) return;
      removedNote = null;
      form.reset();
      counter.textContent = "0";
      render();
      notify("A little thought, safely saved.");
      title.focus();
    });
    document
      .querySelector("#start-note")
      .addEventListener("click", () => title.focus());
    document.querySelector("#undo-delete").addEventListener("click", () => {
      if (!removedNote || notes.length >= 100) return;
      const restored = [...notes];
      restored.splice(
        Math.min(removedNote.index, notes.length),
        0,
        removedNote.note,
      );
      if (save(restored)) {
        removedNote = null;
        render();
        notify("Note restored.");
        title.focus();
      }
    });
  }
  render();
})();
