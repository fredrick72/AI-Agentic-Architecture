import { useId } from 'react';

interface Props {
  size?: 'sm' | 'lg';
}

export function AthenaLogo({ size = 'sm' }: Props) {
  if (size === 'lg') {
    return (
      <div className="flex flex-col items-center gap-3">
        <OwlIcon className="w-20 h-20" />
        <div>
          <h1 className="text-4xl font-bold tracking-tight text-white">Athena</h1>
          <p className="text-xs text-blue-400 tracking-[0.2em] uppercase text-center mt-0.5">
            Database Intelligence
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex items-center gap-2">
      <OwlIcon className="w-7 h-7" />
      <span className="text-base font-bold text-white tracking-tight">Athena</span>
    </div>
  );
}

function OwlIcon({ className }: { className?: string }) {
  // useId ensures gradient IDs are unique per instance, preventing DOM conflicts
  const uid = useId().replace(/:/g, '');
  const id = (name: string) => `${uid}-${name}`;
  const url = (name: string) => `url(#${id(name)})`;

  return (
    <svg
      className={className}
      viewBox="0 0 64 64"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
    >
      <defs>
        <radialGradient id={id('glow')} cx="50%" cy="50%" r="50%">
          <stop offset="0%" stopColor="#6366f1" />
          <stop offset="100%" stopColor="#6366f1" stopOpacity="0" />
        </radialGradient>
        <linearGradient id={id('body')} x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="#4338ca" />
          <stop offset="100%" stopColor="#1e1b4b" />
        </linearGradient>
        <linearGradient id={id('head')} x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="#4f46e5" />
          <stop offset="100%" stopColor="#312e81" />
        </linearGradient>
        <linearGradient id={id('wing')} x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="#3730a3" />
          <stop offset="100%" stopColor="#1e1b4b" />
        </linearGradient>
        <radialGradient id={id('iris')} cx="40%" cy="40%" r="60%">
          <stop offset="0%" stopColor="#60a5fa" />
          <stop offset="100%" stopColor="#2563eb" />
        </radialGradient>
        <radialGradient id={id('chest')} cx="50%" cy="30%" r="60%">
          <stop offset="0%" stopColor="#818cf8" />
          <stop offset="100%" stopColor="#4338ca" />
        </radialGradient>
      </defs>

      {/* Glow behind */}
      <circle cx="32" cy="30" r="22" fill={url('glow')} opacity="0.3" />

      {/* Body */}
      <ellipse cx="32" cy="38" rx="16" ry="18" fill={url('body')} />

      {/* Wings */}
      <path d="M16 42 C8 36 6 24 12 20 C16 18 20 24 18 30 C17 34 16 38 16 42Z" fill={url('wing')} />
      <path d="M48 42 C56 36 58 24 52 20 C48 18 44 24 46 30 C47 34 48 38 48 42Z" fill={url('wing')} />

      {/* Head */}
      <ellipse cx="32" cy="22" rx="13" ry="12" fill={url('head')} />

      {/* Ear tufts */}
      <path d="M22 13 L20 6 L26 11Z" fill="#6366f1" />
      <path d="M42 13 L44 6 L38 11Z" fill="#6366f1" />

      {/* Left eye */}
      <circle cx="25" cy="22" r="6" fill="white" />
      <circle cx="25" cy="22" r="4" fill={url('iris')} />
      <circle cx="25" cy="22" r="2" fill="#1e1b4b" />
      <circle cx="26.5" cy="20.5" r="0.9" fill="white" />

      {/* Right eye */}
      <circle cx="39" cy="22" r="6" fill="white" />
      <circle cx="39" cy="22" r="4" fill={url('iris')} />
      <circle cx="39" cy="22" r="2" fill="#1e1b4b" />
      <circle cx="40.5" cy="20.5" r="0.9" fill="white" />

      {/* Beak */}
      <path d="M30 27 L32 31 L34 27 Q32 25 30 27Z" fill="#fbbf24" />

      {/* Chest pattern */}
      <ellipse cx="32" cy="40" rx="8" ry="10" fill={url('chest')} opacity="0.6" />

      {/* Feet */}
      <path d="M26 54 L24 58 M26 54 L26 58 M26 54 L28 58" stroke="#fbbf24" strokeWidth="1.5" strokeLinecap="round" />
      <path d="M38 54 L36 58 M38 54 L38 58 M38 54 L40 58" stroke="#fbbf24" strokeWidth="1.5" strokeLinecap="round" />

      {/* Circuit lines on body (data theme) */}
      <line x1="20" y1="38" x2="24" y2="38" stroke="#818cf8" strokeWidth="0.8" opacity="0.7" />
      <line x1="24" y1="38" x2="24" y2="34" stroke="#818cf8" strokeWidth="0.8" opacity="0.7" />
      <circle cx="24" cy="34" r="1" fill="#818cf8" opacity="0.7" />
      <line x1="40" y1="42" x2="44" y2="42" stroke="#818cf8" strokeWidth="0.8" opacity="0.7" />
      <line x1="40" y1="42" x2="40" y2="46" stroke="#818cf8" strokeWidth="0.8" opacity="0.7" />
      <circle cx="40" cy="46" r="1" fill="#818cf8" opacity="0.7" />
    </svg>
  );
}
