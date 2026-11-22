/** hometools streaming player UI — bundle entry point. */
import "./styles/metaPill.css";
import "./styles/root.css";
import "./styles/toolsPanel.css";
import "./styles/modals.css";
import "./styles/playlistCards.css";
import "./styles/playerBar.css";
import "./styles/tableView.css";
import "./styles/trackList.css";
import "./styles/videoOverlay.css";
import { startApp } from "./app";
import { installClickGuard } from "./clickGuard";
import { installHoverPreview } from "./hoverPreview";

installClickGuard();
installHoverPreview({ enabled: !!document.getElementById("player") && document.getElementById("player")!.tagName === "VIDEO" });
startApp();
