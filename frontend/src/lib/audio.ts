/**
 * Offline Procedural Tactical Audio Synthesizer (Web Audio API)
 * Synthesizes crisp military sentry chirps and perimeter breach alarms
 * without requiring any external audio files.
 */

let audioCtx: AudioContext | null = null;
let isAudioMuted: boolean = false;

function getAudioContext(): AudioContext | null {
  if (typeof window === "undefined") return null;
  if (!audioCtx) {
    const AudioContextClass = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
    if (AudioContextClass) {
      audioCtx = new AudioContextClass();
    }
  }
  if (audioCtx && audioCtx.state === "suspended") {
    audioCtx.resume();
  }
  return audioCtx;
}

export function isMuted(): boolean {
  if (typeof window !== "undefined") {
    const stored = localStorage.getItem("ibvap_audio_muted");
    if (stored !== null) isAudioMuted = stored === "true";
  }
  return isAudioMuted;
}

export function setMuted(muted: boolean) {
  isAudioMuted = muted;
  if (typeof window !== "undefined") {
    localStorage.setItem("ibvap_audio_muted", muted ? "true" : "false");
  }
}

/**
 * Sonar Ping / Alert Chime: Crisp military 880Hz -> 440Hz tone
 */
export function playSonarPing() {
  if (isMuted()) return;
  const ctx = getAudioContext();
  if (!ctx) return;

  try {
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();

    osc.type = "sine";
    osc.frequency.setValueAtTime(880, ctx.currentTime);
    osc.frequency.exponentialRampToValueAtTime(440, ctx.currentTime + 0.18);

    gain.gain.setValueAtTime(0.15, ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.22);

    osc.connect(gain);
    gain.connect(ctx.destination);

    osc.start(ctx.currentTime);
    osc.stop(ctx.currentTime + 0.23);
  } catch {
    // AudioContext permission issue before user interaction
  }
}

/**
 * Critical Breach Siren: Pulsed high-intensity military tactical alarm
 */
export function playBreachAlarm() {
  if (isMuted()) return;
  const ctx = getAudioContext();
  if (!ctx) return;

  try {
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();

    osc.type = "sawtooth";
    osc.frequency.setValueAtTime(750, ctx.currentTime);
    osc.frequency.linearRampToValueAtTime(950, ctx.currentTime + 0.12);
    osc.frequency.linearRampToValueAtTime(750, ctx.currentTime + 0.24);

    gain.gain.setValueAtTime(0.2, ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.005, ctx.currentTime + 0.35);

    osc.connect(gain);
    gain.connect(ctx.destination);

    osc.start(ctx.currentTime);
    osc.stop(ctx.currentTime + 0.36);
  } catch {
    // ignore
  }
}
