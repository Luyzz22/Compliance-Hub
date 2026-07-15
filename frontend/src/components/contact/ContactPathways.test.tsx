import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ContactPathways } from "./ContactPathways";

describe("ContactPathways", () => {
  it("prepares a controlled direct email without collecting form data", () => {
    const { container } = render(<ContactPathways />);

    fireEvent.click(screen.getByRole("button", { name: /Security Review/ }));

    const link = screen.getByRole("link", { name: "Nachricht vorbereiten" });
    expect(link.getAttribute("href")).toContain("mailto:kontakt@complywithai.de");
    expect(link.getAttribute("href")).toContain(
      "subject=Compliance%20Hub%20%E2%80%93%20Security%20Review",
    );
    expect(container.querySelector("form")).toBeNull();
    expect(screen.getByText(/speichert keine Formulardaten/)).toBeTruthy();
  });
});
