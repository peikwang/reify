import type { ReactElement, ReactNode } from "react";

const PAPER = "#f2efe6";
const GREEN = "#1e5c40";

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

function WebsiteArt() {
  return (
    <ArtFrame>
      <rect x="26" y="30" width="268" height="180" rx="16" fill="#fffdf8" stroke="#d8d3c6" />
      <rect x="26" y="30" width="268" height="28" rx="16" fill="#f7f5ef" />
      <rect x="26" y="46" width="268" height="12" fill="#f7f5ef" />
      <circle cx="42" cy="44" r="3" fill="#c9c4b6" />
      <circle cx="53" cy="44" r="3" fill="#c9c4b6" />
      <circle cx="64" cy="44" r="3" fill="#c9c4b6" />
      <rect x="44" y="72" width="120" height="114" rx="10" fill={GREEN} />
      <circle cx="144" cy="92" r="30" fill="#4c8164" opacity="0.85" />
      <rect x="60" y="82" width="48" height="4" rx="2" fill="#cfe2d6" opacity="0.7" />
      <rect x="60" y="96" width="80" height="11" rx="4" fill="#f7f5ef" />
      <rect x="60" y="113" width="60" height="11" rx="4" fill="#f7f5ef" />
      <rect x="60" y="136" width="48" height="3" rx="1.5" fill="#b6c9bb" />
      <rect x="60" y="144" width="58" height="3" rx="1.5" fill="#b6c9bb" />
      <rect x="60" y="160" width="42" height="12" rx="6" fill="#f7f5ef" />
      <rect x="180" y="72" width="94" height="6" rx="3" fill="#e6e1d5" />
      <rect x="180" y="86" width="72" height="6" rx="3" fill="#e6e1d5" />
      <rect x="180" y="108" width="94" height="34" rx="7" fill="#f1eee5" />
      <rect x="180" y="150" width="42" height="4" rx="2" fill="#c9c4b6" />
      <rect x="180" y="160" width="58" height="4" rx="2" fill="#ded9cc" />
    </ArtFrame>
  );
}

function GameArt() {
  const grid = Array.from({ length: 8 }, (_, index) => index * 32 + 24);
  return (
    <ArtFrame background="#0d1a13">
      <g stroke="#2b5a40" strokeWidth="1" opacity="0.55">
        {grid.map((value) => (
          <line key={`v${value}`} x1={value} y1="0" x2={value} y2="240" />
        ))}
        {grid.map((value) => (
          <line key={`h${value}`} x1="0" y1={value} x2="320" y2={value} />
        ))}
      </g>
      <circle cx="238" cy="62" r="36" fill="#3f7453" opacity="0.6" />
      <circle cx="238" cy="62" r="18" fill="#9fd95e" opacity="0.35" />
      <path
        d="M56 154 L88 154 L88 122 L120 122 L120 90 L152 90 L152 122 L184 122"
        fill="none"
        stroke="#c7ff5e"
        strokeWidth="10"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <circle cx="184" cy="122" r="7" fill="#d9ff8a" />
      <circle cx="56" cy="154" r="7" fill="#d9ff8a" />
      <circle cx="238" cy="62" r="5" fill="#c7ff5e" />
      <rect x="24" y="24" width="44" height="4" rx="2" fill="#5a8f6c" />
      <rect x="24" y="34" width="28" height="3" rx="1.5" fill="#345c46" />
      <rect x="252" y="24" width="44" height="4" rx="2" fill="#5a8f6c" />
      <rect x="252" y="34" width="20" height="3" rx="1.5" fill="#345c46" />
    </ArtFrame>
  );
}

function ImageArt() {
  return (
    <ArtFrame>
      <rect x="34" y="54" width="148" height="122" rx="10" fill="#d9ceb8" transform="rotate(-5 108 115)" />
      <rect x="88" y="36" width="160" height="132" rx="10" fill="#fffdf8" stroke="#d8d3c6" transform="rotate(3 168 102)" />
      <rect x="96" y="44" width="144" height="116" rx="8" fill="#cfe0d2" transform="rotate(3 168 102)" />
      <circle cx="206" cy="78" r="19" fill="#e8b98a" />
      <path d="M96 142 L134 98 L164 128 L186 106 L240 148 L240 160 L96 160Z" fill="#3f6d57" />
      <path d="M96 150 L124 126 L150 148 L176 124 L240 154 L240 160 L96 160Z" fill="#285040" />
      <rect x="32" y="190" width="56" height="4" rx="2" fill="#c9c4b6" />
      <rect x="32" y="200" width="38" height="3" rx="1.5" fill="#ded9cc" />
    </ArtFrame>
  );
}

function VideoArt() {
  return (
    <ArtFrame background="#1c1714">
      <rect x="24" y="46" width="272" height="144" rx="14" fill="#2b211c" stroke="#4a372d" />
      <rect x="42" y="64" width="76" height="108" rx="8" fill="#5e3a30" />
      <rect x="122" y="64" width="76" height="108" rx="8" fill="#3f2a23" />
      <rect x="202" y="64" width="76" height="108" rx="8" fill="#5e3a30" />
      <circle cx="160" cy="118" r="29" fill="#f0a37f" />
      <path d="M153 104 L174 118 L153 132Z" fill="#1c1714" />
      <rect x="42" y="52" width="10" height="6" rx="2" fill="#7c5646" />
      <rect x="62" y="52" width="10" height="6" rx="2" fill="#7c5646" />
      <rect x="82" y="52" width="10" height="6" rx="2" fill="#7c5646" />
      <rect x="102" y="52" width="10" height="6" rx="2" fill="#7c5646" />
      <rect x="42" y="180" width="10" height="6" rx="2" fill="#7c5646" />
      <rect x="62" y="180" width="10" height="6" rx="2" fill="#7c5646" />
      <rect x="82" y="180" width="10" height="6" rx="2" fill="#7c5646" />
      <rect x="102" y="180" width="10" height="6" rx="2" fill="#7c5646" />
      <path d="M24 208 H296" stroke="#4a372d" strokeWidth="3" strokeLinecap="round" />
      <path d="M24 208 H148" stroke="#f0a37f" strokeWidth="3" strokeLinecap="round" />
      <circle cx="148" cy="208" r="5" fill="#f0a37f" />
      <rect x="24" y="26" width="44" height="4" rx="2" fill="#8b6553" />
      <rect x="252" y="26" width="44" height="4" rx="2" fill="#8b6553" />
    </ArtFrame>
  );
}

function ResumeArt() {
  return (
    <ArtFrame background="#eee7da">
      <rect x="82" y="26" width="156" height="188" rx="10" fill="#fffdf8" stroke="#ddd7c9" transform="rotate(-3 160 120)" />
      <circle cx="122" cy="70" r="18" fill="#d8cdb7" />
      <rect x="150" y="56" width="62" height="6" rx="3" fill="#2d382f" />
      <rect x="150" y="68" width="44" height="4" rx="2" fill="#b8b1a2" />
      <line x1="100" y1="100" x2="220" y2="100" stroke="#ddd7c9" strokeWidth="1.5" />
      <rect x="100" y="114" width="34" height="4" rx="2" fill={GREEN} />
      <rect x="100" y="126" width="86" height="4" rx="2" fill="#d5cfc0" />
      <rect x="100" y="136" width="72" height="4" rx="2" fill="#d5cfc0" />
      <rect x="100" y="154" width="34" height="4" rx="2" fill={GREEN} />
      <rect x="100" y="166" width="92" height="4" rx="2" fill="#d5cfc0" />
      <rect x="100" y="176" width="66" height="4" rx="2" fill="#d5cfc0" />
      <rect x="100" y="186" width="48" height="4" rx="2" fill="#d5cfc0" />
      <circle cx="208" cy="178" r="14" fill="#d8e5d9" />
      <path d="M202 178 L207 183 L216 172" fill="none" stroke={GREEN} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    </ArtFrame>
  );
}

function TravelArt() {
  return (
    <ArtFrame background="#dce8e2">
      <rect x="0" y="120" width="320" height="120" fill="#c5dcd4" />
      <circle cx="244" cy="58" r="25" fill="#f2cf9c" />
      <path d="M0 78 Q60 42 120 74 T240 66 T320 82" fill="none" stroke="#8fb6a7" strokeWidth="1.5" opacity="0.7" />
      <path d="M0 102 Q76 66 142 96 T260 84 T320 100" fill="none" stroke="#8fb6a7" strokeWidth="1.5" opacity="0.55" />
      <path d="M0 128 Q72 98 150 122 T320 112" fill="none" stroke="#8fb6a7" strokeWidth="1.5" opacity="0.4" />
      <path
        d="M58 188 C94 162 116 142 148 148 C180 154 188 122 218 112"
        fill="none"
        stroke="#2f6d75"
        strokeWidth="3"
        strokeDasharray="7 7"
        strokeLinecap="round"
      />
      <circle cx="58" cy="188" r="7" fill="#f7f5ef" stroke="#2f6d75" strokeWidth="3" />
      <path d="M218 92 C206 92 198 102 198 113 C198 128 218 144 218 144 C218 144 238 128 238 113 C238 102 230 92 218 92Z" fill={GREEN} />
      <circle cx="218" cy="112" r="6" fill="#f7f5ef" />
      <path d="M0 196 L52 160 L98 196Z" fill="#2c6d75" opacity="0.75" />
      <path d="M70 202 L132 154 L196 202Z" fill="#3f7d78" opacity="0.65" />
      <rect x="24" y="26" width="52" height="4" rx="2" fill="#f7f5ef" opacity="0.8" />
      <rect x="24" y="36" width="32" height="3" rx="1.5" fill="#eef5f0" opacity="0.7" />
    </ArtFrame>
  );
}

function CodeArt() {
  return (
    <ArtFrame background="#e7edf0">
      <rect x="30" y="36" width="260" height="168" rx="14" fill="#fbfdfd" stroke="#cfdadd" />
      <rect x="30" y="36" width="260" height="28" rx="14" fill="#22535a" />
      <rect x="30" y="50" width="260" height="14" fill="#22535a" />
      <circle cx="46" cy="50" r="3" fill="#9bc3c7" />
      <circle cx="57" cy="50" r="3" fill="#9bc3c7" />
      <circle cx="68" cy="50" r="3" fill="#9bc3c7" />
      <rect x="58" y="82" width="28" height="4" rx="2" fill="#8aa4a8" />
      <rect x="94" y="82" width="82" height="4" rx="2" fill="#2f6d75" />
      <rect x="58" y="94" width="48" height="4" rx="2" fill="#b5c7c9" />
      <rect x="112" y="94" width="96" height="4" rx="2" fill="#7da6a9" />
      <rect x="58" y="106" width="64" height="4" rx="2" fill="#b5c7c9" />
      <rect x="58" y="118" width="36" height="4" rx="2" fill="#8aa4a8" />
      <rect x="100" y="118" width="72" height="4" rx="2" fill="#2f6d75" />
      <rect x="58" y="142" width="22" height="4" rx="2" fill="#8aa4a8" />
      <rect x="86" y="142" width="112" height="4" rx="2" fill="#b5c7c9" />
      <rect x="58" y="154" width="94" height="4" rx="2" fill="#b5c7c9" />
      <rect x="58" y="176" width="7" height="13" fill={GREEN} />
      <path d="M232 84 Q222 84 222 94 V104 Q222 114 212 114 Q222 114 222 124 V134 Q222 144 232 144" fill="none" stroke="#22535a" strokeWidth="4" strokeLinecap="round" />
      <path d="M88 84 Q98 84 98 94 V104 Q98 114 108 114 Q98 114 98 124 V134 Q98 144 88 144" fill="none" stroke="#22535a" strokeWidth="4" strokeLinecap="round" />
      <rect x="24" y="24" width="98" height="4" rx="2" fill="#9fb8bc" />
      <rect x="206" y="24" width="90" height="3" rx="1.5" fill="#c1d2d4" />
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
