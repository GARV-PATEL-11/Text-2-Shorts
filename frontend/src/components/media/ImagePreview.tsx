// Images: a box with a fixed ratio (no layout shift), a skeleton while loading, a clear state when the image is
// missing, and full screen on the same page: a lightbox that fills the window and sharpens to the full-size render.
import { useEffect, useRef, useState } from "react";
import { Dialog, Heading, Modal as AriaModal, ModalOverlay } from "react-aria-components";
import { type Fit, type Ratio, RATIOS } from "../../config/media";
import { Button } from "../ui/Button";
import { Close, Expand, Shrink } from "../ui/icons";

/** The picture itself, not interactive (safe inside a radio card's label). */
export function MediaImage({ src, alt, ratio = "16/9", fit = "contain" }: { src: string; alt: string; ratio?: Ratio; fit?: Fit }) {
  const [state, setState] = useState<"loading" | "ready" | "broken">("loading");
  return (
    <span className={`media media--${state}`} style={{ aspectRatio: RATIOS[ratio] }}>
      {state !== "broken" ? (
        <img src={src} alt={alt} loading="lazy" style={{ objectFit: fit }} onLoad={() => setState("ready")} onError={() => setState("broken")} />
      ) : (
        <span className="media__state">No Image</span>
      )}
    </span>
  );
}

/** The browser's own full screen for an element, and whether it is on. */
export function useFullScreen() {
  const [on, setOn] = useState(false);
  useEffect(() => {
    const changed = () => setOn(document.fullscreenElement !== null);
    document.addEventListener("fullscreenchange", changed);
    return () => document.removeEventListener("fullscreenchange", changed);
  }, []);
  const toggle = (element: HTMLElement | null) => {
    if (document.fullscreenElement) void document.exitFullscreen();
    else void element?.requestFullscreen().catch(() => undefined);
  };
  return { on, toggle, supported: typeof document !== "undefined" && document.fullscreenEnabled };
}

/** Full screen on this page: the picture takes 80% of the window, the rest is frosted glass over the page. With
 * `fullSrc` (the 2560×1440 render) the preview shows at once, a note thanks you for waiting while the sharp one is
 * rendered, and it is swapped in when it arrives. Esc, Close or a click on the glass returns. */
export function Lightbox({ isOpen, onOpenChange, src, fullSrc, alt, caption }: {
  isOpen: boolean; onOpenChange: (open: boolean) => void; src: string; fullSrc?: string; alt: string; caption?: string;
}) {
  const frame = useRef<HTMLDivElement>(null);
  const screen = useFullScreen();
  const [sharp, setSharp] = useState<"loading" | "ready" | "failed">("loading");
  useEffect(() => setSharp("loading"), [fullSrc, isOpen]);
  const change = (open: boolean) => {
    if (!open && document.fullscreenElement) void document.exitFullscreen();
    onOpenChange(open);
  };
  const quality = !fullSrc ? null : sharp === "ready" ? "2560 × 1440" : sharp === "failed" ? "Preview Size" : "Sharpening…";
  return (
    <ModalOverlay className="overlay overlay--lightbox" isOpen={isOpen} onOpenChange={change} isDismissable>
      <AriaModal className="lightbox">
        <Dialog className="lightbox__dialog" aria-label={alt}>
          {({ close }) => (
            <div className="lightbox__frame" ref={frame}>
              <div className="lightbox__bar">
                <div className="lightbox__titles">
                  <Heading slot="title" className="lightbox__title">{alt}</Heading>
                  {caption ? <p className="lightbox__caption">{caption}</p> : null}
                </div>
                {quality ? <span className="badge" aria-live="polite">{quality}</span> : null}
                {screen.supported ? (
                  <Button variant="secondary" size="sm" icon={screen.on ? <Shrink /> : <Expand />} onPress={() => screen.toggle(frame.current)}>
                    {screen.on ? "Exit Full Screen" : "Full Screen"}
                  </Button>
                ) : null}
                <Button variant="secondary" size="sm" icon={<Close />} onPress={close} label="Close" />
              </div>
              <div className="lightbox__stage" onClick={(event) => event.target === event.currentTarget && close()}>
                <div className="lightbox__picture">
                  <img src={fullSrc && sharp === "ready" ? fullSrc : src} alt="" className={fullSrc && sharp === "loading" ? "is-soft" : undefined} />
                  {fullSrc && sharp === "loading" ? (
                    <div className="lightbox__wait" role="status">
                      <span className="spinner" aria-hidden="true" />
                      <span><strong>Rendering at 2560 × 1440</strong></span>
                    </div>
                  ) : null}
                  {sharp === "failed" ? <div className="lightbox__wait" role="status"><span>Full Size Did Not Render: Showing the Preview</span></div> : null}
                </div>
                {fullSrc && sharp === "loading" ? (
                  <img className="lightbox__loader" src={fullSrc} alt="" onLoad={() => setSharp("ready")} onError={() => setSharp("failed")} />
                ) : null}
              </div>
            </div>
          )}
        </Dialog>
      </AriaModal>
    </ModalOverlay>
  );
}

/** A Full Screen button opening the lightbox; it sits beside whatever shows the image. */
export function ExpandImage({ src, fullSrc, alt, caption }: { src: string; fullSrc?: string; alt: string; caption?: string }) {
  const [open, setOpen] = useState(false);
  return (
    <>
      <button className="media__expand" type="button" onClick={() => setOpen(true)} aria-label={`Full screen: ${alt}`} title="Full Screen">
        <Expand />
      </button>
      <Lightbox isOpen={open} onOpenChange={setOpen} src={src} fullSrc={fullSrc} alt={alt} caption={caption} />
    </>
  );
}

/** A picture that opens full screen. */
export function ImagePreview({ src, fullSrc, alt, caption, ratio = "16/9", fit = "contain" }: {
  src: string; fullSrc?: string; alt: string; caption?: string; ratio?: Ratio; fit?: Fit;
}) {
  return (
    <figure className="media-frame">
      <MediaImage src={src} alt={alt} ratio={ratio} fit={fit} />
      <ExpandImage src={src} fullSrc={fullSrc} alt={alt} caption={caption} />
      {caption ? <figcaption className="media-frame__caption">{caption}</figcaption> : null}
    </figure>
  );
}
