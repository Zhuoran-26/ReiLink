import React from "react";
import { createRoot } from "react-dom/client";

import { App } from "./App";
import { OverlayApp } from "./OverlayApp";
import { isOverlayRendererLocation } from "./overlayRoute";
import "./styles/tokens.css";
import "./styles/themes.css";
import "./styles.css";
import "./styles/base.css";
import "./components/ui/ui.css";
import "./components/rei/rei.css";
import "./app/shell.css";

const isOverlayRenderer = isOverlayRendererLocation(window.location);

createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    {isOverlayRenderer ? <OverlayApp /> : <App />}
  </React.StrictMode>
);
