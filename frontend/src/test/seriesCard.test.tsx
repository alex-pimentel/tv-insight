import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import { SeriesCard } from "../components/SeriesCard";
import type { SeriesCard as SeriesCardModel } from "../api/types";

function card(overrides: Partial<SeriesCardModel> = {}): SeriesCardModel {
  return {
    id: 7,
    name: "Dark",
    year: 2017,
    poster_url: "https://example.test/dark.jpg",
    poster_thumbnail_url: "https://example.test/dark-thumb.jpg",
    genres: ["Drama", "Mystery"],
    status: "Ended",
    rating: 8.4,
    network: "Netflix",
    language: "German",
    ...overrides,
  };
}

function renderCard(series: SeriesCardModel) {
  return render(
    <MemoryRouter>
      <SeriesCard series={series} />
    </MemoryRouter>,
  );
}

describe("SeriesCard", () => {
  it("links to the series detail route", () => {
    renderCard(card());
    expect(screen.getByTestId("series-card")).toHaveAttribute("href", "/series/7");
  });

  it("renders the small poster from the API result, with an accessible empty alt", () => {
    const { container } = renderCard(card());
    const image = container.querySelector("img");

    expect(image).not.toBeNull();
    expect(image).toHaveAttribute("src", "https://example.test/dark-thumb.jpg");
    expect(image).toHaveAttribute("alt", "");
  });

  it("falls back to the original when the API did not publish a thumbnail", () => {
    const { container } = renderCard(card({ poster_thumbnail_url: null }));
    const image = container.querySelector("img");

    expect(image).toHaveAttribute("src", "https://example.test/dark.jpg");
  });

  it("falls back to a placeholder when there is no poster at all", () => {
    const { container } = renderCard(
      card({ poster_url: null, poster_thumbnail_url: null }),
    );

    expect(container.querySelector("img")).toBeNull();
    expect(screen.getByText("🎬")).toBeInTheDocument();
  });

  it("shows year, network and rating together", () => {
    renderCard(card());
    expect(screen.getByText("2017 · Netflix · ★ 8.4")).toBeInTheDocument();
  });

  it("degrades the metadata line when values are missing", () => {
    renderCard(card({ year: null, network: null, rating: null }));
    expect(screen.getByText("—")).toBeInTheDocument();
  });

  it("omits the rating when it is absent", () => {
    renderCard(card({ rating: null }));
    expect(screen.getByText("2017 · Netflix")).toBeInTheDocument();
  });

  it("shows at most three genres", () => {
    renderCard(card({ genres: ["A", "B", "C", "D", "E"] }));

    const tags = screen.getAllByRole("listitem");
    expect(tags.map((tag) => tag.textContent)).toEqual(["A", "B", "C"]);
  });

  it("does not render a genre list when there are none", () => {
    renderCard(card({ genres: [] }));
    expect(screen.queryByRole("listitem")).not.toBeInTheDocument();
  });
});
