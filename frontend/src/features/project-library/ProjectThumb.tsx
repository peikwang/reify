import { useEffect, useState } from "react";

interface ProjectThumbProps {
  url: string;
  revision: number;
  title: string;
}

export function ProjectThumb({ url, revision, title }: ProjectThumbProps) {
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    setLoaded(false);
  }, [url, revision]);

  const src = url + (url.includes("?") ? "&" : "?") + "v=" + revision;

  return (
    <div className={"project-thumb" + (loaded ? " loaded" : "")} aria-hidden="true">
      <iframe
        src={src}
        title={title + " 缩略图"}
        loading="lazy"
        tabIndex={-1}
        sandbox="allow-scripts"
        scrolling="no"
        onLoad={() => setLoaded(true)}
      />
      <span className="project-thumb-shade" />
    </div>
  );
}
