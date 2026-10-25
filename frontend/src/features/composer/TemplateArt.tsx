import codeArt from "../../assets/templates/code.webp";
import gameArt from "../../assets/templates/game.webp";
import imageArt from "../../assets/templates/image.webp";
import resumeArt from "../../assets/templates/resume.webp";
import travelArt from "../../assets/templates/travel.webp";
import videoArt from "../../assets/templates/video.webp";
import websiteArt from "../../assets/templates/website.webp";

const ART: Record<string, string> = {
  website: websiteArt,
  game: gameArt,
  image: imageArt,
  video: videoArt,
  resume: resumeArt,
  travel: travelArt,
  code: codeArt,
};

export function TemplateArt({ capability }: { capability: string }) {
  const src = ART[capability] ?? websiteArt;
  return (
    <img
      className="template-art-img"
      src={src}
      alt=""
      width={640}
      height={480}
      loading="lazy"
      decoding="async"
    />
  );
}
