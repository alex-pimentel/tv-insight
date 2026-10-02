import { describe, expect, it } from "vitest";
import { findEpisode, overallProgress, withEpisodeWatched } from "../lib/progress";
import { seasons } from "../test/fixtures";

describe("withEpisodeWatched", () => {
  it("marks an episode and recomputes that season's counters", () => {
    const updated = withEpisodeWatched(seasons(), 101, true);

    expect(findEpisode(updated, 101)?.watched).toBe(true);
    expect(updated[0].watched).toBe(1);
    expect(updated[0].progress).toBe(0.5);
    expect(updated[1].watched).toBe(0);
  });

  it("unmarks an episode", () => {
    const updated = withEpisodeWatched(seasons([101, 102]), 101, false);

    expect(updated[0].watched).toBe(1);
    expect(updated[0].progress).toBe(0.5);
  });

  it("does not touch seasons that do not contain the episode", () => {
    const original = seasons();
    const updated = withEpisodeWatched(original, 201, true);

    expect(updated[0]).toBe(original[0]);
  });

  it("returns an unchanged structure for an unknown episode", () => {
    const updated = withEpisodeWatched(seasons(), 999, true);
    expect(overallProgress(updated)).toEqual({ watched: 0, total: 4, progress: 0 });
  });
});

describe("overallProgress", () => {
  it("aggregates across seasons", () => {
    expect(overallProgress(seasons([101, 201]))).toEqual({
      watched: 2,
      total: 4,
      progress: 0.5,
    });
  });

  it("does not divide by zero", () => {
    expect(overallProgress([])).toEqual({ watched: 0, total: 0, progress: 0 });
  });
});

describe("findEpisode", () => {
  it("returns undefined for an unknown id", () => {
    expect(findEpisode(seasons(), 999)).toBeUndefined();
  });
});
