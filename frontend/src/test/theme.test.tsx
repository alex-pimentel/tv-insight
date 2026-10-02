import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { ThemeToggle, applyTheme, readTheme } from "../components/ThemeToggle";

describe("ThemeToggle", () => {
  beforeEach(() => {
    document.documentElement.classList.remove("dark");
    localStorage.clear();
  });

  afterEach(() => {
    document.documentElement.classList.remove("dark");
    localStorage.clear();
  });

  it("starts from the theme already applied to the document", () => {
    document.documentElement.classList.add("dark");
    render(<ThemeToggle />);

    expect(screen.getByTestId("theme-toggle")).toHaveTextContent("dark");
    expect(screen.getByTestId("theme-toggle")).toHaveAttribute("aria-pressed", "true");
  });

  it("switches to light and back", async () => {
    document.documentElement.classList.add("dark");
    render(<ThemeToggle />);

    await userEvent.click(screen.getByTestId("theme-toggle"));

    expect(document.documentElement.classList.contains("dark")).toBe(false);
    expect(screen.getByTestId("theme-toggle")).toHaveTextContent("light");

    await userEvent.click(screen.getByTestId("theme-toggle"));

    expect(document.documentElement.classList.contains("dark")).toBe(true);
    expect(screen.getByTestId("theme-toggle")).toHaveTextContent("dark");
  });

  it("labels the action with the theme it will switch to", () => {
    document.documentElement.classList.add("dark");
    render(<ThemeToggle />);

    expect(screen.getByRole("button", { name: /switch to light theme/i })).toBeInTheDocument();
  });

  it("persists the choice", async () => {
    render(<ThemeToggle />);

    await userEvent.click(screen.getByTestId("theme-toggle"));

    expect(localStorage.getItem("tv-insight-theme")).toBe("dark");
    expect(readTheme()).toBe("dark");
  });
});

describe("theme helpers", () => {
  beforeEach(() => {
    document.documentElement.classList.remove("dark");
    localStorage.clear();
  });

  it("readTheme reflects the class, not storage", () => {
    expect(readTheme()).toBe("light");
    applyTheme("dark");
    expect(readTheme()).toBe("dark");
  });

  it("applyTheme survives storage being unavailable", () => {
    const original = Object.getOwnPropertyDescriptor(window, "localStorage");
    Object.defineProperty(window, "localStorage", {
      configurable: true,
      get() {
        throw new Error("blocked");
      },
    });

    try {
      // Must not throw: the class still applies for the session.
      expect(() => applyTheme("dark")).not.toThrow();
      expect(document.documentElement.classList.contains("dark")).toBe(true);
    } finally {
      if (original) Object.defineProperty(window, "localStorage", original);
    }
  });
});
