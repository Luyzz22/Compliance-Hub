import { describe, expect, it } from "vitest";

import { browserCsrfHeaders } from "./clientSessionHeaders";

describe("browser session headers", () => {
  it("extracts only the named CSRF cookie", () => {
    expect(browserCsrfHeaders("other=x; ch_csrf=token%2Dvalue; final=y")).toEqual({
      "x-csrf-token": "token-value",
    });
    expect(browserCsrfHeaders("ch_session=opaque")).toEqual({});
    expect(browserCsrfHeaders("ch_csrf=%E0%A4%A")).toEqual({});
  });
});
