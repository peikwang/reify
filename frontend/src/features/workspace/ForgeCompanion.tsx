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
        <ellipse cx="60" cy="110" rx="32" ry="6" fill="rgba(23,37,28,.10)" />
        <g className="breath">
          <path
            className="tail"
            d="M30 94 q-15 -5 -12 -20 q9 2 15 9"
            fill="none"
            stroke={INK}
            strokeWidth="5.5"
            strokeLinecap="round"
          />
          <ellipse cx="60" cy="84" rx="32" ry="27" fill={FUR} stroke={INK} strokeWidth="2.5" />
          <ellipse cx="45" cy="101" rx="9" ry="6.5" fill={FUR} stroke={INK} strokeWidth="2" />
          <ellipse cx="75" cy="101" rx="9" ry="6.5" fill={FUR} stroke={INK} strokeWidth="2" />
          <g className="head">
            <path className="ear l" d="M38 33 q-7 -18 5 -22 q9 5 9 18" fill={FUR} stroke={INK} strokeWidth="2.5" />
            <path className="ear r" d="M82 33 q7 -18 -5 -22 q-9 5 -9 18" fill={FUR} stroke={INK} strokeWidth="2.5" />
            <path d="M55 22 q5 -9 10 0" fill="none" stroke={INK} strokeWidth="2" strokeLinecap="round" />
            <circle cx="60" cy="47" r="25" fill={FUR} stroke={INK} strokeWidth="2.5" />
            <g className="face-default">
              <g className="eye l">
                <circle cx="51" cy="45" r="5.2" fill={INK} />
                <circle cx="52.8" cy="43.2" r="1.7" fill="#fff" />
                <circle cx="49.6" cy="47" r="0.9" fill="#fff" />
              </g>
              <g className="eye r">
                <circle cx="69" cy="45" r="5.2" fill={INK} />
                <circle cx="70.8" cy="43.2" r="1.7" fill="#fff" />
                <circle cx="67.6" cy="47" r="0.9" fill="#fff" />
              </g>
              <path d="M54 57 q6 5 12 0" fill="none" stroke={INK} strokeWidth="2" strokeLinecap="round" />
            </g>
            <g className="face-happy">
              <path d="M45 47 q5 -6 10 0" fill="none" stroke={INK} strokeWidth="2.2" strokeLinecap="round" />
              <path d="M65 47 q5 -6 10 0" fill="none" stroke={INK} strokeWidth="2.2" strokeLinecap="round" />
              <path d="M52 54 q8 9 16 0" fill="none" stroke={INK} strokeWidth="2.2" strokeLinecap="round" />
              <path d="M57 59 q3 4 6 0" fill="#e88a8a" />
            </g>
            <circle cx="42" cy="54" r="3.8" fill="#f3c0b2" opacity=".85" />
            <circle cx="78" cy="54" r="3.8" fill="#f3c0b2" opacity=".85" />
            <ellipse cx="60" cy="51" rx="3.1" ry="2.3" fill={INK} />
          </g>
          <path d="M43 69 q17 8 34 0 l-2 8 q-15 6 -30 0 z" fill={GREEN} opacity=".95" />
          <circle cx="60" cy="77" r="3.2" fill={SPARK} />
          <ellipse className="arm l" cx="35" cy="80" rx="7.5" ry="9.5" fill={FUR} stroke={INK} strokeWidth="2" />
          <g className="hammer">
            <ellipse className="arm r" cx="85" cy="80" rx="7.5" ry="9.5" fill={FUR} stroke={INK} strokeWidth="2" />
            <rect x="91" y="72" width="4" height="18" rx="2" fill="#8a6b45" />
            <rect x="85" y="66" width="17" height="9" rx="3" fill={GREEN} />
          </g>
        </g>
        <g data-prop="thought">
          <circle cx="95" cy="24" r="10" fill="#fff" stroke={GREEN} strokeWidth="1.6" />
          <circle cx="85" cy="34" r="3" fill={GREEN} />
          <circle cx="80" cy="39" r="1.8" fill={GREEN} />
          <text x="95" y="28" textAnchor="middle" fontSize="9" fill={GREEN} fontFamily="var(--mono)">
            ?
          </text>
        </g>
        <g data-prop="anvil">
          <path d="M76 100 h28 v5 h-9 v6 h-10 v-6 h-9 z" fill="#454d46" stroke={INK} strokeWidth="2" strokeLinejoin="round" />
          <path d="M76 100 h28" stroke="#6b746c" strokeWidth="2" strokeLinecap="round" />
        </g>
        <g data-prop="sparks" stroke={SPARK} strokeWidth="2.4" strokeLinecap="round" fill="none">
          <path d="M96 92 l4 -5" />
          <path d="M101 97 l6 -2" />
          <path d="M90 89 l2 -6" />
        </g>
        <g data-prop="heart">
          <path d="M96 34 q-5 -6 -9 -2 q-3 3 0 6 l9 8 l9 -8 q3 -3 0 -6 q-4 -4 -9 2 z" fill="#e88a8a" opacity=".95" />
        </g>
        <g data-prop="oven">
          <path d="M12 98 q0 -21 17 -21 q17 0 17 21 z" fill="#3a2a1c" stroke={INK} strokeWidth="2" />
          <path className="oven-glow" d="M20 98 q0 -13 9 -13 q9 0 9 13 z" fill={SPARK} opacity=".55" />
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
