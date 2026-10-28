// Anonymous colour distributions support camera-cut association; these are
// not a gender classifier and cannot establish a real person's identity.
class VideoAppearanceDescriptor {
  static measure(points, rgba, width, height) {
    if (!rgba || !points?.[24] || width * height * 4 !== rgba.length) return null;
    const shoulderY = (points[11].y + points[12].y) / 2, hipY = (points[23].y + points[24].y) / 2;
    const cx = (points[11].x + points[12].x) / 2;
    const half = Math.max(.01, Math.abs(points[11].x - points[12].x) * .4);
    const noseY = points[0].y, torso = hipY - shoulderY;
    if (!(torso > .025)) return null;
    const bands = [[noseY - torso * .18, noseY + torso * .08, .7],
      [noseY + torso * .08, shoulderY, .65], [shoulderY, shoulderY + torso * .55, 1], [shoulderY + torso * .55, hipY, .8]];
    const result = [];
    for (const [top, bottom, scale] of bands) {
      const hist = Array(24).fill(0); let count = 0;
      const x0 = Math.max(0, Math.floor((cx - half * scale) * width)), x1 = Math.min(width, Math.ceil((cx + half * scale) * width));
      const y0 = Math.max(0, Math.floor(top * height)), y1 = Math.min(height, Math.ceil(bottom * height));
      for (let y = y0; y < y1; y++) for (let x = x0; x < x1; x++) {
        const at = (y * width + x) * 4;
        for (let channel = 0; channel < 3; channel++) hist[channel * 8 + Math.min(7, rgba[at + channel] >> 5)]++;
        count++;
      }
      if (!count) return null;
      result.push(...hist.map(v => v / count));
    }
    // Each of the 12 band/channel histograms has unit mass.
    return result;
  }
  static distance(a, b) {
    if (!a || !b || a.length !== b.length) return Infinity;
    // L1 distance is at most 2 per histogram, hence 24 overall.
    return a.reduce((sum, v, i) => sum + Math.abs(v - b[i]), 0) / 24;
  }
  static average(values) {
    const valid = values.filter(Boolean); if (!valid.length) return null;
    return valid[0].map((_, i) => valid.reduce((sum, row) => sum + row[i], 0) / valid.length);
  }
}
