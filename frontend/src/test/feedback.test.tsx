import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { ApiError } from "../api/client";
import { CommentList } from "../components/CommentList";
import { ErrorNotice } from "../components/ErrorNotice";
import { Spinner } from "../components/Spinner";
import { comment } from "./fixtures";

describe("ErrorNotice", () => {
  it.each([
    ["ResourceNotFound", /could not find that title/i],
    ["InvalidInput", /not valid/i],
    ["ExternalServiceError", /catalogue is not answering/i],
    ["ProviderUnavailable", /insight service is unavailable/i],
  ])("translates %s into a message a person can act on", (code, expected) => {
    render(<ErrorNotice error={new ApiError(400, code, "detail text")} />);

    expect(screen.getByRole("alert")).toHaveTextContent(expected);
    expect(screen.getByRole("alert")).toHaveTextContent("detail text");
  });

  it("falls back to a generic message for an unknown code", () => {
    render(<ErrorNotice error={new ApiError(500, "SomethingWeird", "boom")} />);
    expect(screen.getByRole("alert")).toHaveTextContent(/something went wrong/i);
  });

  it("accepts a plain Error and a non-Error value", () => {
    const { unmount } = render(<ErrorNotice error={new Error("plain failure")} />);
    expect(screen.getByRole("alert")).toHaveTextContent("plain failure");
    unmount();

    render(<ErrorNotice error="just a string" />);
    expect(screen.getByText(/^just a string$/)).toBeInTheDocument();
  });

  it("offers a retry that calls back and is absent when no handler is given", async () => {
    const onRetry = vi.fn();
    const { unmount } = render(
      <ErrorNotice error={new Error("x")} onRetry={onRetry} />,
    );

    await userEvent.click(screen.getByRole("button", { name: /try again/i }));
    expect(onRetry).toHaveBeenCalledTimes(1);
    unmount();

    render(<ErrorNotice error={new Error("x")} />);
    expect(screen.queryByRole("button", { name: /try again/i })).not.toBeInTheDocument();
  });
});

describe("CommentList", () => {
  it("marks the viewer's own comments", () => {
    render(<CommentList comments={[comment({ mine: true })]} />);
    expect(screen.getByText("you")).toBeInTheDocument();
  });

  it("shows the episode code when the comment belongs to an episode", () => {
    render(<CommentList comments={[comment({ target: "episode", episode_code: "S02E07" })]} />);
    expect(screen.getByText("S02E07")).toBeInTheDocument();
  });

  it("renders the timestamp in a machine readable and human readable form", () => {
    const { container } = render(<CommentList comments={[comment()]} />);

    const time = container.querySelector("time");
    expect(time).toHaveAttribute("datetime", "2024-01-01T12:00:00Z");
    expect(time?.textContent).not.toContain("Invalid");
  });

  it("falls back to the raw value when the timestamp cannot be parsed", () => {
    render(<CommentList comments={[comment({ created_at: "not-a-date" })]} />);
    expect(screen.getByText("not-a-date")).toBeInTheDocument();
  });

  it("shows a configurable empty state", () => {
    render(<CommentList comments={[]} emptyMessage="Nothing here yet" />);
    expect(screen.getByTestId("comments-empty")).toHaveTextContent("Nothing here yet");
  });

  it("shows the default empty state", () => {
    render(<CommentList comments={[]} />);
    expect(screen.getByTestId("comments-empty")).toHaveTextContent("No comments yet.");
  });
});

describe("Spinner", () => {
  it("is announced as a status to assistive technology", () => {
    render(<Spinner label="Thinking…" />);
    expect(screen.getByRole("status")).toHaveTextContent("Thinking…");
  });

  it("defaults its label", () => {
    render(<Spinner />);
    expect(screen.getByRole("status")).toHaveTextContent("Loading");
  });
});
