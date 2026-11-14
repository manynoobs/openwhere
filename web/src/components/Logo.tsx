/** The OpenWhere mark: a map pin (where) whose head holds a shop awning (open). */
export function LogoMark({ size = 22 }: { size?: number }) {
  return (
    <svg className="logomark" width={size} height={(size * 62) / 48} viewBox="0 0 48 62" aria-hidden="true">
      <path
        d="M24 2C12.4 2 3 11.3 3 22.8c0 8.2 4.8 14.5 10.3 19.5 4.4 4 7.8 9.2 10.7 17.7 2.9-8.5 6.3-13.7 10.7-17.7C40.2 37.3 45 31 45 22.8 45 11.3 35.6 2 24 2z"
        fill="var(--ink)"
      />
      <rect x="12.5" y="16" width="23" height="15" rx="2.5" fill="var(--glass-solid)" />
      <path
        d="M10.5 15.2c0-1.8 1.4-3.2 3.2-3.2h20.6c1.8 0 3.2 1.4 3.2 3.2v1.3a3.4 3.4 0 0 1-6.8 0 3.4 3.4 0 0 1-6.7 0 3.4 3.4 0 0 1-6.7 0 3.4 3.4 0 0 1-6.8 0z"
        fill="#3FBF6F"
      />
      <rect x="20.5" y="22.5" width="7" height="8.5" rx="1.2" fill="var(--ink)" />
    </svg>
  );
}
