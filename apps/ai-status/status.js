"use strict";

class AiWorkPage {
  constructor() {
    this.list = document.getElementById("task-list");
    this.status = new Mice.Status("task-status");
    this.signIn = document.getElementById("task-login");
    this.tasks = [];
    this.revision = "";
  }

  text(tag, words, className) {
    const element = document.createElement(tag);
    element.textContent = words;
    if (className) element.className = className;
    return element;
  }

  age(seconds, format) {
    const minutes = Math.max(0, Math.floor((Date.now() / 1000 - seconds) / 60));
    if (minutes < 1) return "Just now";
    if (minutes < 60) return format.format(-minutes, "minute");
    if (minutes < 1440) return format.format(-Math.floor(minutes / 60), "hour");
    return format.format(-Math.floor(minutes / 1440), "day");
  }

  card(task, age) {
    const labels = {working: "In progress", done: "Finished", blocked: "Waiting", stale: "No recent update"};
    const styles = {working: "state-ok", done: "state-ok", blocked: "state-warn", stale: "state-stale"};
    const card = this.text("article", "", "card");
    const heading = this.text("div", "", "task-line");
    heading.append(this.text("h2", task.name || "Untitled task"),
                   this.text("span", labels[task.state], styles[task.state]));
    const detail = this.text("p", "", "task-line mini");
    detail.append(this.text("span", task.agent || "AI not recorded"), this.text("span", age));
    if (task.model) detail.appendChild(this.text("span", task.model, "tech"));
    card.append(heading, detail, this.text("p", task.activity || "No activity recorded."));
    if (task.branch || task.commit) {
      const source = this.text("p", "", "tech mini");
      if (task.branch) source.append(this.text("span", "Branch"), " ", this.text("code", task.branch));
      if (task.branch && task.commit) source.append(" · ");
      if (task.commit) source.append(this.text("span", "Last commit"), " ", this.text("code", task.commit));
      card.appendChild(source);
    }
    return card;
  }

  render() {
    const selected = window.MiceLang ? window.MiceLang.current() : "th";
    const ageFormat = new Intl.RelativeTimeFormat(selected === "off" ? "en" : selected);
    const ages = this.tasks.map(task => this.age(task.updated, ageFormat));
    const revision = JSON.stringify([this.tasks, ages]);
    if (revision === this.revision) return;
    this.revision = revision;
    this.list.replaceChildren(...this.tasks.map((task, i) => this.card(task, ages[i])));
  }

  async refresh() {
    const result = await Mice.Api.get("/api/ai-status", {timeout: 12000});
    const signedOut = result.status === 401;
    const forbidden = result.status === 403;
    this.signIn.hidden = !signedOut && !forbidden;
    if (signedOut || forbidden) {
      this.tasks = [];
      this.status.warn(signedOut ? "Sign in to view AI work." : "Ask a Hub administrator to view AI work.");
    } else if (!result.ok || !Array.isArray(result.data.tasks)) {
      this.status.stale(this.tasks.length ? "Showing the last update. Trying again soon." :
        "Could not load AI work. Trying again soon.");
    } else {
      this.tasks = result.data.tasks;
      const empty = result.data.available ? "There are no AI tasks yet." : "Task files are unavailable on this Hub.";
      this.status.show(this.tasks.length ? "ready" : "empty", this.tasks.length ? "" : empty);
    }
    this.render();
  }

  async start() {
    try {
      await this.refresh();
    } finally {
      window.setTimeout(() => this.start(), 15000);
    }
  }
}

new AiWorkPage().start();
