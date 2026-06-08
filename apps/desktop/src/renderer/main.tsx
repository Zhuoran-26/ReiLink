import React from "react";
import { createRoot } from "react-dom/client";

import { App } from "./App";
import { OverlayApp } from "./OverlayApp";
import { isOverlayRendererLocation } from "./overlayRoute";
import "./styles.css";

const isOverlayRenderer = isOverlayRendererLocation(window.location);

createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    {isOverlayRenderer ? <OverlayApp /> : <App />}
  </React.StrictMode>
);
