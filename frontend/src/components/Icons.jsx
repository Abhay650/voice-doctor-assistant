const p = { width: 22, height: 22, viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', strokeWidth: 1.8, strokeLinecap: 'round', strokeLinejoin: 'round', 'aria-hidden': true }
export const PhoneIcon = (props) => (
  <svg {...p} {...props}><path d="M5 4h4l2 5-2.5 1.5a11 11 0 0 0 5 5L15 13l5 2v4a2 2 0 0 1-2 2A16 16 0 0 1 3 6a2 2 0 0 1 2-2Z" /></svg>
)
export const HangIcon = (props) => (
  <svg {...p} {...props}><path d="M3 14.5c5-4 13-4 18 0l-1.5 3-3.5-1v-2.5a9 9 0 0 0-8 0V16.5l-3.5 1Z" /></svg>
)
export const MicIcon = (props) => (
  <svg {...p} {...props}><rect x="9" y="3" width="6" height="11" rx="3" /><path d="M5 11a7 7 0 0 0 14 0M12 18v3" /></svg>
)
export const MicOffIcon = (props) => (
  <svg {...p} {...props}><path d="M3 3l18 18M9 9v2a3 3 0 0 0 5 2.2M15 9.5V6a3 3 0 0 0-5.7-1.3M5 11a7 7 0 0 0 11.3 5.5M19 11a7 7 0 0 1-.7 3M12 18v3" /></svg>
)
export const CheckIcon = (props) => (<svg {...p} {...props}><path d="m5 12.5 4.5 4.5L19 7.5" /></svg>)
export const CrossIcon = (props) => (<svg {...p} {...props}><path d="M6 6l12 12M18 6 6 18" /></svg>)
