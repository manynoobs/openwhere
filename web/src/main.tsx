import { createRoot } from "react-dom/client";
import App from "./App";
import "./styles.css";

// No StrictMode: its double mount tears down the first map mid-load, and the cancelled
// tile requests leave holes in the shared pmtiles cache.
createRoot(document.getElementById("root")!).render(<App />);
