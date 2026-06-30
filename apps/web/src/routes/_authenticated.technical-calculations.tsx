import { createFileRoute } from "@tanstack/react-router";

import { TechnicalCalculations } from "../components/technical/technical-calculations";

export const Route = createFileRoute("/_authenticated/technical-calculations")({
  head: () => ({ meta: [{ title: "Teknik Hesaplamalar — Bomaksan" }] }),
  component: TechnicalCalculations,
});
