import { useEffect, useRef, useState } from "react";

interface ProjectThumbProps {
  url: string;
  revision: number;
  title: string;
}

export function ProjectThumb({ url, revision, title }: ProjectThumbProps) {
  const rootRef = useRef<HTMLDivElement>(null);
  const [visible, setVisible] = useState(false);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    setLoaded(false);
  }, [url, revision]);

  useEffect(() => {
    const el = rootRef.current;
    if (!el) return;
    if (typeof IntersectionObserver === "undefined") {
      setVisible(true);
      return;
    }
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries.some((entry) => entry.isIntersecting)) {
          setVisible(true);
          observer.disconnect();
        }
      },
      { rootMargin: "240px" },
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  const src = url + (url.includes("?") ? "&" : "?") + "v=" + revision;

  return (
    <div
      className={"project-thumb" + (loaded ? " loaded" : "")}
      ref={rootRef}
      aria-hidden="true"
    >
      {visible ? (
        <iframe
          src={src}
          title={title + " 缩略图"}
          loading="lazy"
          tabIndex={-1}
          sandbox="allow-scripts"
          scrolling="no"
          onLoad={() => setLoaded(true)}
        />
      ) : null}
      <span className="project-thumb-shade" />
    </div>
  );
}
