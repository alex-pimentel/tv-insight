import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { CommentForm } from "../components/CommentForm";
import { ProgressBar } from "../components/ProgressBar";
import { SeasonAccordion } from "../components/SeasonAccordion";
import { seasons } from "../test/fixtures";

describe("ProgressBar", () => {
  it("exposes its value to assistive technology", () => {
    render(<ProgressBar value={0.25} label="Overall progress" />);

    const bar = screen.getByRole("progressbar", { name: "Overall progress" });
    expect(bar).toHaveAttribute("aria-valuenow", "25");
    expect(screen.getByText("25% watched")).toBeInTheDocument();
  });

  it("clamps out of range values", () => {
    render(<ProgressBar value={1.8} label="Clamped" />);
    expect(screen.getByRole("progressbar", { name: "Clamped" })).toHaveAttribute(
      "aria-valuenow",
      "100",
    );
  });
});

describe("CommentForm", () => {
  it("keeps the submit button disabled until there is text", async () => {
    render(<CommentForm onSubmit={vi.fn()} />);
    const button = screen.getByRole("button", { name: /post comment/i });

    expect(button).toBeDisabled();
    await userEvent.type(screen.getByLabelText(/your comment/i), "Nice");
    expect(button).toBeEnabled();
  });

  it("submits the trimmed text and clears the field", async () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    render(<CommentForm onSubmit={onSubmit} />);

    await userEvent.type(screen.getByLabelText(/your comment/i), "  Great show  ");
    await userEvent.click(screen.getByRole("button", { name: /post comment/i }));

    expect(onSubmit).toHaveBeenCalledWith("Great show");
    expect(screen.getByLabelText(/your comment/i)).toHaveValue("");
  });

  it("surfaces a failure and keeps the text so it is not lost", async () => {
    const onSubmit = vi.fn().mockRejectedValue(new Error("Network down"));
    render(<CommentForm onSubmit={onSubmit} />);

    await userEvent.type(screen.getByLabelText(/your comment/i), "Hello");
    await userEvent.click(screen.getByRole("button", { name: /post comment/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Network down");
    expect(screen.getByLabelText(/your comment/i)).toHaveValue("Hello");
  });

  it("does not submit blank input", async () => {
    const onSubmit = vi.fn();
    render(<CommentForm onSubmit={onSubmit} />);

    await userEvent.type(screen.getByLabelText(/your comment/i), "   ");
    expect(screen.getByRole("button", { name: /post comment/i })).toBeDisabled();
    expect(onSubmit).not.toHaveBeenCalled();
  });
});

describe("SeasonAccordion", () => {
  function renderAccordion(
    seasonList = seasons(),
    onToggleWatched = vi.fn(),
  ) {
    return render(
      <MemoryRouter>
        <SeasonAccordion
          seriesId={1}
          seasons={seasonList}
          onToggleWatched={onToggleWatched}
        />
      </MemoryRouter>,
    );
  }

  it("renders every season with its progress", () => {
    renderAccordion(seasons([101]));

    expect(screen.getAllByTestId("season")).toHaveLength(2);
    expect(screen.getByRole("button", { name: /Season 1/ })).toHaveTextContent("1/2");
  });

  it("expands the first season by default and toggles the others", async () => {
    renderAccordion();

    const first = screen.getByRole("button", { name: /Season 1/ });
    const second = screen.getByRole("button", { name: /Season 2/ });

    expect(first).toHaveAttribute("aria-expanded", "true");
    expect(second).toHaveAttribute("aria-expanded", "false");

    await userEvent.click(second);
    expect(second).toHaveAttribute("aria-expanded", "true");
  });

  it("reports a checkbox change with the episode", async () => {
    const onToggleWatched = vi.fn();
    renderAccordion(seasons(), onToggleWatched);

    await userEvent.click(screen.getByLabelText("Mark S01E01 Episode 1 as watched"));

    expect(onToggleWatched).toHaveBeenCalledWith(
      expect.objectContaining({ id: 101 }),
      true,
    );
  });

  it("links each episode to its detail page", () => {
    renderAccordion();
    expect(screen.getByRole("link", { name: "Episode 1" })).toHaveAttribute(
      "href",
      "/series/1/episodes/101",
    );
  });

  it("shows a message when the series has no episodes", () => {
    renderAccordion([]);
    expect(screen.getByText(/no episodes published yet/i)).toBeInTheDocument();
  });
});
