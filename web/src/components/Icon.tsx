// A small authored icon set: 1.6px strokes on a 20px grid, drawn to match SF Symbols weight.
const paths = {
  search: <><circle cx="8.5" cy="8.5" r="5.5" /><path d="M12.7 12.7 17 17" /></>,
  play: <path d="M7 4.8v10.4L15.6 10z" fill="currentColor" stroke="none" />,
  pause: <><rect x="5.5" y="4.5" width="3" height="11" rx="1" fill="currentColor" stroke="none" /><rect x="11.5" y="4.5" width="3" height="11" rx="1" fill="currentColor" stroke="none" /></>,
  filter: <><path d="M3.5 5.5h13M6 10h8M8.5 14.5h3" /></>,
  info: <><circle cx="10" cy="10" r="7.2" /><path d="M10 9v4.6" /><circle cx="10" cy="6.4" r="0.5" fill="currentColor" /></>,
  close: <path d="M6 6l8 8M14 6l-8 8" />,
  x: <path d="M7 7l6 6M13 7l-6 6" />,
  chevron: <path d="M8 5.5 12.5 10 8 14.5" />,
  target: <><circle cx="10" cy="10" r="6.5" /><circle cx="10" cy="10" r="2" /><path d="M10 1.5v3M10 15.5v3M1.5 10h3M15.5 10h3" /></>,
  places: <><path d="M10 17s-5-4.6-5-8.5a5 5 0 0 1 10 0c0 3.9-5 8.5-5 8.5z" /><circle cx="10" cy="8.5" r="1.8" /></>,
  pin: <><path d="M10 17v-4.2" /><path d="M6.2 12.8h7.6l-1.3-3.1V4.5h-5v5.2z" /></>,
  compare: <><rect x="3.5" y="4" width="13" height="3" rx="1" /><rect x="3.5" y="8.5" width="9" height="3" rx="1" /><rect x="3.5" y="13" width="11" height="3" rx="1" /></>,
};

export type IconName = keyof typeof paths;

export function Icon({ name, size = 18 }: { name: IconName; size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6"
      strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      {paths[name]}
    </svg>
  );
}
