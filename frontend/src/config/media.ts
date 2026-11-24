// The media contract: aspect-ratio presets and how a picture fills its box.
export const RATIOS = { "1/1": "1 / 1", "4/3": "4 / 3", "16/9": "16 / 9", "3/2": "3 / 2", "9/16": "9 / 16" } as const;
export type Ratio = keyof typeof RATIOS;
export type Fit = "contain" | "cover";  // contain for generated frames (nothing cropped); cover for thumbnails

export const WAVEFORM_BARS = 72;              // bars per waveform, whatever the clip's length
export const WAVEFORM_MAX_BYTES = 20_000_000; // larger files skip the waveform (decoding holds all samples in memory)
