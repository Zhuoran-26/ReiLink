import React from "react";
import { createRoot } from "react-dom/client";

import { App } from "./App";
import { OverlayApp } from "./OverlayApp";
import "./styles.css";

const isOverlayRenderer = new URLSearchParams(window.location.search).get("overlay") === "1";

createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    {isOverlayRenderer ? <OverlayApp /> : <App />}
  </React.StrictMode>
);
