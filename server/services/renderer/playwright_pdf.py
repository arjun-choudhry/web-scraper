from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright

from server.services.auth.auth_strategy import AuthStrategy, NoAuthStrategy
from server.services.renderer.browser_context_factory import create_browser_context
from server.services.renderer.render_config import RenderConfig


def _prepare_page_for_capture(page) -> None:
    # Trigger lazy-loaded assets and stabilize layout before printing.
    page.evaluate(
        """
        () => {
          document.querySelectorAll('img[loading="lazy"]').forEach((img) => {
            img.loading = "eager";
          });
          document.querySelectorAll("img[data-src], source[data-src]").forEach((el) => {
            const ds = el.getAttribute("data-src");
            if (ds && !el.getAttribute("src")) {
              el.setAttribute("src", ds);
            }
          });
        }
        """
    )
    
    # Scroll to bottom multiple times to trigger all lazy loading
    page.evaluate(
        """
        async () => {
          let lastHeight = 0;
          let currentHeight = Math.max(
            document.body ? document.body.scrollHeight : 0,
            document.documentElement ? document.documentElement.scrollHeight : 0
          );
          
          // Keep scrolling until page height stabilizes
          while (currentHeight > lastHeight) {
            lastHeight = currentHeight;
            let y = 0;
            while (y < currentHeight) {
              window.scrollTo(0, y);
              y += 500;
              await new Promise((resolve) => setTimeout(resolve, 150));
            }
            await new Promise((resolve) => setTimeout(resolve, 500));
            currentHeight = Math.max(
              document.body ? document.body.scrollHeight : 0,
              document.documentElement ? document.documentElement.scrollHeight : 0
            );
          }
        }
        """
    )
    
    # Wait for network to be idle with longer timeout
    try:
        page.wait_for_load_state("networkidle", timeout=60000)
    except Exception:
        # If networkidle times out, continue anyway
        pass
    
    # Additional wait for any remaining content
    page.wait_for_timeout(2000)
    
    # Scroll to bottom again after initial load to catch any late-loading content
    page.evaluate(
        """
        async () => {
          let lastHeight = 0;
          let currentHeight = Math.max(
            document.body ? document.body.scrollHeight : 0,
            document.documentElement ? document.documentElement.scrollHeight : 0
          );
          
          // Keep scrolling until page height stabilizes
          while (currentHeight > lastHeight) {
            lastHeight = currentHeight;
            let y = 0;
            while (y < currentHeight) {
              window.scrollTo(0, y);
              y += 500;
              await new Promise((resolve) => setTimeout(resolve, 150));
            }
            await new Promise((resolve) => setTimeout(resolve, 500));
            currentHeight = Math.max(
              document.body ? document.body.scrollHeight : 0,
              document.documentElement ? document.documentElement.scrollHeight : 0
            );
          }
        }
        """
    )
    
    page.evaluate(
        """
        async () => {
          const images = Array.from(document.images || []);
          await Promise.all(images.map((img) => {
            if (img.complete) return Promise.resolve();
            return new Promise((resolve) => {
              img.addEventListener("load", resolve, { once: true });
              img.addEventListener("error", resolve, { once: true });
            });
          }));
        }
        """
    )
    
    # Final wait for images to load
    page.wait_for_timeout(1000)
    
    # Force full page height to prevent cutoff
    page.evaluate(
        """
        () => {
          const body = document.body;
          const html = document.documentElement;
          if (body) {
            body.style.minHeight = body.scrollHeight + 'px';
            body.style.height = 'auto';
          }
          if (html) {
            html.style.minHeight = html.scrollHeight + 'px';
            html.style.height = 'auto';
          }
        }
        """
    )
    
    # Inject CSS to handle very long pages
    page.add_style_tag(
        content="""
        @media print {
          html, body {
            max-height: none !important;
            overflow: visible !important;
          }
        }
        """
    )


def _inject_print_styles(page) -> None:
    # Remove sticky/fixed overlays and use print-friendly pagination.
    page.add_style_tag(
        content="""
        @page {
          size: A4 landscape;
          margin: 0;
        }
        @media print {
          html, body {
            height: auto !important;
            min-height: auto !important;
            max-height: none !important;
            overflow: visible !important;
          }
          * {
            -webkit-print-color-adjust: exact !important;
            print-color-adjust: exact !important;
          }
          img, svg, canvas {
            max-width: 100% !important;
            height: auto !important;
          }
          table, figure, pre, blockquote {
            break-inside: avoid !important;
            page-break-inside: avoid !important;
          }
          thead { display: table-header-group !important; }
          tfoot { display: table-footer-group !important; }
          [style*="position:sticky"],
          [style*="position: fixed"],
          .sticky,
          .fixed,
          header[style*="position"],
          footer[style*="position"] {
            position: static !important;
            top: auto !important;
            bottom: auto !important;
          }
        }
        """
    )
    
    # Force full page height to prevent cutoff
    page.evaluate(
        """
        () => {
          const body = document.body;
          const html = document.documentElement;
          if (body) {
            body.style.minHeight = body.scrollHeight + 'px';
            body.style.height = 'auto';
          }
          if (html) {
            html.style.minHeight = html.scrollHeight + 'px';
            html.style.height = 'auto';
          }
        }
        """
    )


def _normalize_layout_before_pdf(page) -> None:
    # Some sites keep content under sticky headers or apply transform offsets.
    page.evaluate(
        """
        () => {
          const all = Array.from(document.querySelectorAll("*"));
          const chromeRegex = /(nav|menu|sidebar|drawer|header|footer|modal|popup|cookie|consent|banner)/i;
          for (const el of all) {
            const style = window.getComputedStyle(el);
            if (style.position === "fixed" || style.position === "sticky") {
              const rect = el.getBoundingClientRect();
              const vw = Math.max(window.innerWidth, 1);
              const vh = Math.max(window.innerHeight, 1);
              const idAndClass = `${el.id || ""} ${el.className || ""}`;
              const tagName = (el.tagName || "").toLowerCase();
              const isLargeSidebar = rect.width > vw * 0.18 && rect.height > vh * 0.55;
              const isTopBar = rect.height > 40 && rect.height < vh * 0.25 && rect.width > vw * 0.6 && rect.top <= 40;
              const isLikelyChrome = chromeRegex.test(idAndClass) || chromeRegex.test(tagName);
              const isLikelyOverlay = rect.width > vw * 0.45 && rect.height < vh * 0.35 && rect.top < vh * 0.2;

              if (
                isLargeSidebar ||
                isTopBar ||
                (isLikelyChrome && isLikelyOverlay)
              ) {
                el.style.setProperty("display", "none", "important");
              } else {
                el.style.setProperty("position", "static", "important");
                el.style.setProperty("top", "auto", "important");
                el.style.setProperty("left", "auto", "important");
                el.style.setProperty("right", "auto", "important");
                el.style.setProperty("bottom", "auto", "important");
              }
            }
            if (style.transform && style.transform !== "none") {
              const m = style.transform.match(/matrix\\(([^)]+)\\)/);
              if (m) {
                const parts = m[1].split(",").map((v) => parseFloat(v.trim()));
                const ty = parts.length >= 6 ? parts[5] : 0;
                if (Number.isFinite(ty) && ty < 0) {
                  el.style.setProperty("transform", "none", "important");
                }
              }
            }
          }

          const body = document.body;
          const html = document.documentElement;
          if (body) {
            body.style.setProperty("margin-top", "0", "important");
            body.style.setProperty("margin-left", "0", "important");
            body.style.setProperty("margin-right", "0", "important");
            body.style.setProperty("padding-top", "0", "important");
            body.style.setProperty("padding-left", "0", "important");
            body.style.setProperty("padding-right", "0", "important");
            body.style.setProperty("overflow", "visible", "important");
          }
          if (html) {
            html.style.setProperty("margin-top", "0", "important");
            html.style.setProperty("margin-left", "0", "important");
            html.style.setProperty("margin-right", "0", "important");
            html.style.setProperty("padding-top", "0", "important");
            html.style.setProperty("padding-left", "0", "important");
            html.style.setProperty("padding-right", "0", "important");
            html.style.setProperty("overflow", "visible", "important");
          }

          window.scrollTo(0, 0);
        }
        """
    )


def _remove_empty_layout_columns(page) -> None:
    # Generic pruning: remove wide columns that contain almost no real content.
    page.evaluate(
        """
        () => {
          const vw = Math.max(window.innerWidth, 1);
          const vh = Math.max(window.innerHeight, 1);

          const hasMeaningfulContent = (el) => {
            const text = (el.innerText || "").replace(/\\s+/g, " ").trim();
            const textLen = text.length;
            const mediaCount = el.querySelectorAll(
              "img, picture, svg, canvas, table, video, iframe, pre, code, blockquote, ul, ol"
            ).length;
            const headingCount = el.querySelectorAll("h1, h2, h3, h4, h5, h6").length;
            const paragraphCount = el.querySelectorAll("p, li").length;
            return textLen >= 60 || mediaCount > 0 || headingCount > 0 || paragraphCount >= 2;
          };

          const informationalDescendantCount = (el) => {
            return el.querySelectorAll(
              "p, li, h1, h2, h3, h4, h5, h6, article, section, img, picture, svg, canvas, table, figure, pre, code, blockquote, video, iframe"
            ).length;
          };

          const parents = Array.from(document.querySelectorAll("*")).filter((parent) => {
            const style = window.getComputedStyle(parent);
            if (style.display === "none") return false;
            if (style.display === "flex") {
              return (style.flexDirection || "row").startsWith("row");
            }
            if (style.display === "grid") {
              const cols = (style.gridTemplateColumns || "").trim();
              return cols.split(" ").filter(Boolean).length >= 2;
            }
            return false;
          });

          for (const parent of parents) {
            const rectParent = parent.getBoundingClientRect();
            if (rectParent.width < vw * 0.45 || rectParent.height < vh * 0.3) continue;

            const children = Array.from(parent.children).filter((child) => {
              const r = child.getBoundingClientRect();
              if (r.width < vw * 0.08) return false;
              if (r.height < vh * 0.2) return false;
              const cs = window.getComputedStyle(child);
              return cs.display !== "none" && cs.visibility !== "hidden";
            });

            if (children.length < 2) continue;

            const removable = [];
            for (const child of children) {
              const r = child.getBoundingClientRect();
              const childStyle = window.getComputedStyle(child);
              const text = (child.innerText || "").replace(/\\s+/g, " ").trim();
              const textLen = text.length;
              const infoDescendants = informationalDescendantCount(child);
              const isColumnWidth = r.width >= vw * 0.10 && r.width <= vw * 0.48;
              const isTallColumn = r.height >= vh * 0.4;
              const isMostlyEmpty =
                !hasMeaningfulContent(child) &&
                child.querySelectorAll("input, button, select, textarea").length <= 1;
              const hasLowVisualStructure =
                infoDescendants <= 1 &&
                textLen < 30 &&
                child.childElementCount <= 6;
              const isLikelySpacerColumn =
                isColumnWidth &&
                isTallColumn &&
                isMostlyEmpty &&
                hasLowVisualStructure &&
                childStyle.position !== "fixed" &&
                childStyle.position !== "sticky";

              if (isLikelySpacerColumn) {
                removable.push(child);
              }
            }

            if (removable.length == 0 || removable.length >= children.length) continue;
            for (const node of removable) {
              node.style.setProperty("display", "none", "important");
              node.style.setProperty("width", "0", "important");
              node.style.setProperty("min-width", "0", "important");
              node.style.setProperty("margin", "0", "important");
              node.style.setProperty("padding", "0", "important");
            }
          }
        }
        """
    )


def safe_filename_for_url(url: str, index: int) -> str:
    parsed = urlparse(url)
    host = (parsed.hostname or "page").replace(".", "_")
    path = parsed.path.strip("/").replace("/", "_") or "home"
    name = f"{index:02d}_{host}_{path}.pdf"
    return "".join(ch for ch in name if ch.isalnum() or ch in {"_", "-", "."})


def render_url_to_pdf(
    *,
    url: str,
    output_dir: Path,
    index: int,
    config: RenderConfig | None = None,
    auth_strategy: AuthStrategy | None = None,
) -> str:
    cfg = config or RenderConfig()
    auth = auth_strategy or NoAuthStrategy()

    output_dir.mkdir(parents=True, exist_ok=True)
    filename = safe_filename_for_url(url, index)
    output_path = output_dir / filename

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-extensions",
                "--no-sandbox",
                "--disable-dev-shm-usage",
            ],
        )
        context = create_browser_context(browser)
        page = context.new_page()
        auth.apply(page)
        page.goto(url, wait_until=cfg.page_load_state, timeout=cfg.navigation_timeout_ms)
        page.emulate_media(media="screen")
        _prepare_page_for_capture(page)
        _inject_print_styles(page)
        _normalize_layout_before_pdf(page)
        _remove_empty_layout_columns(page)
        content_width = page.evaluate(
            """
            () => {
              const body = document.body;
              const html = document.documentElement;
              const widths = [
                body ? body.scrollWidth : 0,
                body ? body.offsetWidth : 0,
                html ? html.clientWidth : 0,
                html ? html.scrollWidth : 0,
                html ? html.offsetWidth : 0,
              ];
              return Math.max(...widths, 1200);
            }
            """
        )
        content_width = int(content_width)
        landscape = True
        printable_width_px = 1040
        scale = min(0.92, max(0.60, printable_width_px / max(content_width, 1)))
        
        # Scroll to top before generating PDF
        page.evaluate("() => window.scrollTo(0, 0)")
        page.wait_for_timeout(300)
        
        page.pdf(
            path=str(output_path),
            format="A4",
            landscape=landscape,
            scale=scale,
            print_background=cfg.print_background,
            display_header_footer=False,
            prefer_css_page_size=False,
            margin={"top": "0", "right": "0", "bottom": "0", "left": "0"},
        )
        context.close()
        browser.close()

    return filename
