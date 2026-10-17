let logoId=0;

// The 700×732 source already has enough pixels for a crisp 2× display.
// Clip the emblem in SVG instead of enlarging or regenerating its Vietnamese text.
export function parishLogo(size=88) {
  const clip='parish-emblem-'+(++logoId);
  return `<svg class="parish-logo" viewBox="0 0 680 680" width="${size}" height="${size}" role="img" aria-label="Logo Giáo xứ Xuân Hoà"><defs><clipPath id="${clip}"><circle cx="340" cy="340" r="340"/></clipPath></defs><image href="assets/logo-xuan-hoa.png" x="-5" y="-14" width="700" height="732" clip-path="url(#${clip})"/></svg>`;
}
