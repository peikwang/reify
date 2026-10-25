import type { ReactElement, ReactNode } from "react";

const PAPER = "#f2efe6";
const GREEN = "#1e5c40";
const SOFT = "#4c8164";
const LINE = "#d8d3c6";
const SPARK = "#e8a33d";
const INK = "#17251c";
const FUR = "#fdfbf4";

function ArtFrame({ children, background = PAPER }: { children: ReactNode; background?: string }) {
  return (
    <svg
      className="template-art-svg"
      viewBox="0 0 320 240"
      role="presentation"
      focusable="false"
    >
      <rect width="320" height="240" fill={background} />
      {children}
    </svg>
  );
}

function PetMini({ x, y, s = 1 }: { x: number; y: number; s?: number }) {
  return (
    <g className="pet-mini" transform={`translate(${x} ${y}) scale(${s})`}>
      <path d="M-9 -8 q-3 -8 2 -10 q4 2 4 8" fill={FUR} stroke={INK} strokeWidth="1.6" />
      <path d="M9 -8 q3 -8 -2 -10 q-4 2 -4 8" fill={FUR} stroke={INK} strokeWidth="1.6" />
      <circle cx="0" cy="0" r="12" fill={FUR} stroke={INK} strokeWidth="1.6" />
      <circle cx="-4" cy="-1" r="2" fill={INK} />
      <circle cx="4" cy="-1" r="2" fill={INK} />
      <path d="M-3 4 q3 3 6 0" fill="none" stroke={INK} strokeWidth="1.4" strokeLinecap="round" />
    </g>
  );
}

function WebsiteArt() {
  return (
    <ArtFrame>
      <g transform="translate(0 20)">
        <path d="M60 60 h200 l14 26 h-228 z" fill={GREEN} stroke={INK} strokeWidth="2" />
        <g stroke={FUR} strokeWidth="3">
          {Array.from({ length: 7 }, (_, i) => (
            <line key={i} x1={74 + i * 28} y1="62" x2={68 + i * 28} y2="84" />
          ))}
        </g>
        <rect x="74" y="86" width="172" height="86" rx="6" fill="#fffdf8" stroke={LINE} strokeWidth="2" />
        <rect x="88" y="100" width="70" height="8" rx="4" fill={SOFT} />
        <rect x="88" y="116" width="110" height="6" rx="3" fill={LINE} />
        <rect x="88" y="132" width="46" height="16" rx="8" fill={GREEN} />
        <rect x="176" y="100" width="52" height="48" rx="6" fill="#eef2ea" stroke={LINE} />
        <PetMini x={268} y={150} />
      </g>
    </ArtFrame>
  );
}

function GameArt() {
  return (
    <ArtFrame background="#0d1a13">
      <g transform="translate(0 20)">
        <g stroke="#2b5a40" opacity="0.5">
          {[40, 120, 200, 280].map((x) => (
            <line key={`v${x}`} x1={x} y1="0" x2={x} y2="200" />
          ))}
          {[50, 120].map((y) => (
            <line key={`h${y}`} x1="0" y1={y} x2="320" y2={y} />
          ))}
        </g>
        <rect x="96" y="46" width="128" height="108" rx="12" fill="#12241a" stroke="#3f7453" strokeWidth="2" />
        <rect x="110" y="60" width="100" height="62" rx="6" fill="#0a140e" stroke="#9fd95e" strokeWidth="1.4" />
        <rect x="120" y="98" width="10" height="10" fill="#9fd95e" />
        <rect x="176" y="70" width="8" height="8" fill={SPARK} />
        <circle cx="126" cy="138" r="7" fill="#3f7453" />
        <circle cx="194" cy="138" r="5" fill={SPARK} />
        <circle cx="180" cy="138" r="5" fill="#9fd95e" />
        <PetMini x={60} y={150} s={1.1} />
      </g>
    </ArtFrame>
  );
}

function ImageArt() {
  return (
    <ArtFrame>
      <g transform="translate(0 20)">
        <line x1="40" y1="36" x2="280" y2="36" stroke={LINE} strokeWidth="2" />
        <rect x="52" y="42" width="70" height="54" rx="4" fill="#fffdf8" stroke={INK} strokeWidth="2" />
        <path d="M58 88 l18 -22 l14 14 l12 -16 l14 24 z" fill={SOFT} />
        <circle cx="70" cy="56" r="5" fill={SPARK} />
        <rect x="136" y="58" width="70" height="54" rx="4" fill="#fffdf8" stroke={INK} strokeWidth="2" />
        <circle cx="171" cy="85" r="16" fill={GREEN} />
        <path d="M142 106 q29 -18 58 0" fill="none" stroke={SOFT} strokeWidth="3" />
        <rect x="220" y="42" width="54" height="70" rx="4" fill="#fffdf8" stroke={INK} strokeWidth="2" />
        <path d="M228 100 q19 -34 38 0" fill={SOFT} opacity="0.7" />
        <circle cx="247" cy="62" r="6" fill={SPARK} />
        <PetMini x={96} y={164} s={0.95} />
      </g>
    </ArtFrame>
  );
}

function VideoArt() {
  return (
    <ArtFrame background="#101812">
      <g transform="translate(0 20)">
        <rect x="60" y="46" width="200" height="86" rx="8" fill="#0a140e" stroke="#3f7453" strokeWidth="2" />
        <path d="M146 74 l34 15 l-34 15 z" fill="#9fd95e" />
        <g transform="rotate(-8 60 46)">
          <rect x="58" y="30" width="204" height="18" rx="4" fill="#17251c" stroke="#3f7453" />
          <g fill="#9fd95e">
            {Array.from({ length: 6 }, (_, i) => (
              <rect key={i} x={70 + i * 32} y="33" width="14" height="12" transform="skewX(-18)" />
            ))}
          </g>
        </g>
        <rect x="60" y="146" width="200" height="10" rx="5" fill="#17251c" />
        <rect x="60" y="146" width="120" height="10" rx="5" fill={SPARK} />
        <circle cx="180" cy="151" r="7" fill={FUR} stroke={INK} />
        <PetMini x={288} y={168} s={0.9} />
      </g>
    </ArtFrame>
  );
}

function ResumeArt() {
  const tilt = "rotate(-3 130 105)";
  return (
    <ArtFrame background="#eee7da">
      <g transform="translate(0 20)">
        <rect x="70" y="30" width="120" height="150" rx="6" fill="#fffdf8" stroke={LINE} strokeWidth="2" transform={tilt} />
        <circle cx="104" cy="58" r="12" fill={SOFT} transform={tilt} />
        <rect x="124" y="50" width="52" height="7" rx="3" fill={INK} opacity="0.75" transform={tilt} />
        <rect x="86" y="84" width="88" height="5" rx="2.5" fill={LINE} transform={tilt} />
        <rect x="86" y="96" width="76" height="5" rx="2.5" fill={LINE} transform={tilt} />
        <rect x="86" y="108" width="84" height="5" rx="2.5" fill={LINE} transform={tilt} />
        <rect x="196" y="60" width="64" height="86" rx="6" fill="#eef2ea" stroke={LINE} />
        <rect x="206" y="72" width="44" height="6" rx="3" fill={SOFT} />
        <rect x="206" y="86" width="36" height="5" rx="2.5" fill={LINE} />
        <rect x="206" y="98" width="40" height="5" rx="2.5" fill={LINE} />
        <circle cx="228" cy="128" r="10" fill="none" stroke={SPARK} strokeWidth="2.4" />
        <PetMini x={250} y={168} s={0.95} />
      </g>
    </ArtFrame>
  );
}

function TravelArt() {
  return (
    <ArtFrame background="#eef2ea">
      <g transform="translate(0 20)">
        <path d="M40 40 l70 -12 l70 12 l70 -12 v132 l-70 12 l-70 -12 l-70 12 z" fill="#fffdf8" stroke={LINE} strokeWidth="2" />
        <path d="M110 28 v132 M180 40 v132" stroke={LINE} strokeWidth="1.4" />
        <path d="M70 140 q40 -50 80 -30 q40 20 90 -40" fill="none" stroke={GREEN} strokeWidth="3" strokeDasharray="7 6" strokeLinecap="round" />
        <circle cx="70" cy="140" r="6" fill={GREEN} />
        <circle cx="240" cy="70" r="6" fill={SPARK} />
        <path d="M240 70 l0 -18 l16 5 l-16 5" fill={SPARK} />
        <PetMini x={150} y={120} />
      </g>
    </ArtFrame>
  );
}

function CodeArt() {
  return (
    <ArtFrame>
      <g transform="translate(0 20)">
        <rect x="56" y="34" width="208" height="132" rx="10" fill="#101812" stroke={INK} strokeWidth="2" />
        <rect x="56" y="34" width="208" height="24" rx="10" fill="#17251c" />
        <circle cx="72" cy="46" r="4" fill="#c2603a" />
        <circle cx="86" cy="46" r="4" fill={SPARK} />
        <circle cx="100" cy="46" r="4" fill={SOFT} />
        <g fontFamily="var(--mono)" fontSize="11">
          <text x="72" y="80" fill="#9fd95e">def</text>
          <text x="100" y="80" fill="#e8efe6">quicksort(xs):</text>
          <text x="84" y="98" fill="#9fb8a5">pivot = xs[0]</text>
          <text x="84" y="116" fill="#9fb8a5">return lo + mid + hi</text>
          <text x="72" y="140" fill={SPARK}>▍</text>
        </g>
        <PetMini x={288} y={168} s={0.9} />
      </g>
    </ArtFrame>
  );
}

const ART: Record<string, () => ReactElement> = {
  website: WebsiteArt,
  game: GameArt,
  image: ImageArt,
  video: VideoArt,
  resume: ResumeArt,
  travel: TravelArt,
  code: CodeArt,
};

export function TemplateArt({ capability }: { capability: string }) {
  const Component = ART[capability] ?? WebsiteArt;
  return <Component />;
}
