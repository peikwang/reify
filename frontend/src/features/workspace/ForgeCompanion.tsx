import { COMPANION_COPY, type CompanionStage } from "./companion";

const INK = "#17251c";
const FUR = "#fdfbf4";
const GREEN = "#1e5c40";
const SOFT = "#4c8164";
const SPARK = "#e8a33d";

export function ForgeCompanion({ stage }: { stage: CompanionStage }) {
  const copy = COMPANION_COPY[stage];
  return (
    <div className="companion" data-stage={stage}>
      <svg
        className="pet"
        viewBox="0 0 120 120"
        role="img"
        aria-label={"锻兽：" + copy.label}
      >
        <ellipse cx="60" cy="108" rx="30" ry="6" fill="rgba(23,37,28,.10)" />
        <g className="breath">
          <path
            className="tail"
            d="M32 92 q-14 -4 -12 -18 q8 2 14 8"
            fill="none"
            stroke={INK}
            strokeWidth="5"
            strokeLinecap="round"
          />
          <ellipse cx="60" cy="82" rx="30" ry="26" fill={FUR} stroke={INK} strokeWidth="2.5" />
          <ellipse cx="46" cy="98" rx="8" ry="6" fill={FUR} stroke={INK} strokeWidth="2" />
          <ellipse cx="74" cy="98" rx="8" ry="6" fill={FUR} stroke={INK} strokeWidth="2" />
          <g className="head">
            <path className="ear l" d="M40 34 q-6 -16 4 -20 q8 4 8 16" fill={FUR} stroke={INK} strokeWidth="2.5" />
            <path className="ear r" d="M80 34 q6 -16 -4 -20 q-8 4 -8 16" fill={FUR} stroke={INK} strokeWidth="2.5" />
            <circle cx="60" cy="46" r="24" fill={FUR} stroke={INK} strokeWidth="2.5" />
            <g className="eye l">
              <circle cx="51" cy="45" r="4.6" fill={INK} />
              <circle cx="52.6" cy="43.4" r="1.4" fill="#fff" />
            </g>
            <g className="eye r">
              <circle cx="69" cy="45" r="4.6" fill={INK} />
              <circle cx="70.6" cy="43.4" r="1.4" fill="#fff" />
            </g>
            <circle cx="44" cy="53" r="3.4" fill="#f3c9b6" opacity=".8" />
            <circle cx="76" cy="53" r="3.4" fill="#f3c9b6" opacity=".8" />
            <ellipse cx="60" cy="51" rx="3" ry="2.2" fill={INK} />
            <path
              className="mouth"
              d="M54 57 q6 5 12 0"
              fill="none"
              stroke={INK}
              strokeWidth="2"
              strokeLinecap="round"
            />
          </g>
          <ellipse className="arm l" cx="36" cy="76" rx="7" ry="9" fill={FUR} stroke={INK} strokeWidth="2" />
          <g className="hammer">
            <ellipse className="arm r" cx="84" cy="76" rx="7" ry="9" fill={FUR} stroke={INK} strokeWidth="2" />
            <rect x="86" y="58" width="4" height="16" rx="2" fill="#8a6b45" />
            <rect x="80" y="52" width="16" height="9" rx="3" fill={GREEN} />
          </g>
        </g>
        <g data-prop="thought">
          <circle cx="94" cy="22" r="10" fill="#fff" stroke={GREEN} strokeWidth="1.6" />
          <circle cx="84" cy="32" r="3" fill={GREEN} />
          <circle cx="79" cy="37" r="1.8" fill={GREEN} />
          <text x="94" y="26" textAnchor="middle" fontSize="9" fill={GREEN} fontFamily="var(--mono)">
            ?
          </text>
        </g>
        <g data-prop="sparks" stroke={SPARK} strokeWidth="2.4" strokeLinecap="round" fill="none">
          <path d="M96 66 l4 -5" />
          <path d="M102 72 l6 -2" />
          <path d="M92 60 l2 -6" />
        </g>
        <g data-prop="oven">
          <path d="M14 96 q0 -20 16 -20 q16 0 16 20 z" fill="#3a2a1c" stroke={INK} strokeWidth="2" />
          <path className="oven-glow" d="M22 96 q0 -12 8 -12 q8 0 8 12 z" fill={SPARK} opacity=".55" />
        </g>
        <g data-prop="artifact">
          <rect x="86" y="30" width="24" height="30" rx="3" fill="#fff" stroke={GREEN} strokeWidth="2" />
          <rect x="90" y="36" width="16" height="3" rx="1.5" fill={SOFT} />
          <rect x="90" y="42" width="12" height="3" rx="1.5" fill="#c9d6cb" />
          <rect x="90" y="48" width="14" height="3" rx="1.5" fill="#c9d6cb" />
        </g>
        <g data-prop="sweat">
          <path d="M86 30 q4 6 0 9 q-4 -3 0 -9" fill="#7fb3d5" />
        </g>
      </svg>
      <p className="companion-label">{copy.label}</p>
      <p className="companion-say">{copy.say}</p>
    </div>
  );
}
