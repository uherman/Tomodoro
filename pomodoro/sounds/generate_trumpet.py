"""Generate a fun trumpet fanfare WAV file."""
import math
import struct
import wave

SAMPLE_RATE = 44100


def generate_trumpet_tone(freq: float, duration: float, volume: float = 0.5) -> list[float]:
    """Generate a trumpet-like tone using additive synthesis with harmonics."""
    samples = int(SAMPLE_RATE * duration)
    result = []
    # Trumpet harmonic profile (relative amplitudes)
    harmonics = [1.0, 0.8, 0.6, 0.35, 0.2, 0.1]

    for i in range(samples):
        t = i / SAMPLE_RATE
        # Attack-decay-sustain-release envelope
        attack = 0.03
        release = 0.05
        rel_start = duration - release
        if t < attack:
            env = t / attack
        elif t > rel_start:
            env = (duration - t) / release
        else:
            env = 1.0

        # Add slight vibrato (characteristic of brass)
        vibrato = 1.0 + 0.003 * math.sin(2 * math.pi * 5.5 * t)

        sample = 0.0
        for h, amp in enumerate(harmonics, 1):
            sample += amp * math.sin(2 * math.pi * freq * h * vibrato * t)

        # Normalize and apply envelope
        sample = sample / sum(harmonics) * env * volume
        result.append(sample)
    return result


def write_wav(filename: str, samples: list[float]) -> None:
    """Write samples to a WAV file."""
    with wave.open(filename, "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        for s in samples:
            s = max(-1.0, min(1.0, s))
            wf.writeframes(struct.pack("<h", int(s * 32767)))


def generate_fanfare() -> list[float]:
    """Happy ascending trumpet fanfare."""
    notes = [
        (523.25, 0.15),  # C5
        (659.25, 0.15),  # E5
        (783.99, 0.15),  # G5
        (1046.50, 0.40), # C6 (held longer)
    ]
    all_samples: list[float] = []
    gap = [0.0] * int(SAMPLE_RATE * 0.03)
    for freq, dur in notes:
        all_samples.extend(generate_trumpet_tone(freq, dur, volume=0.6))
        all_samples.extend(gap)
    return all_samples


def generate_sad_trumpet() -> list[float]:
    """Sad descending 'wah wah wah waaah' trumpet."""
    notes = [
        (493.88, 0.30),  # B4
        (466.16, 0.30),  # Bb4
        (440.00, 0.30),  # A4
        (311.13, 0.80),  # Eb4 — the long sad ending note
    ]
    all_samples: list[float] = []
    gap = [0.0] * int(SAMPLE_RATE * 0.05)

    for i, (freq, dur) in enumerate(notes):
        is_last = i == len(notes) - 1
        tone = generate_trumpet_tone(freq, dur, volume=0.5)
        if is_last:
            # Add a pitch bend down on the last note for extra sadness
            bend_samples = int(SAMPLE_RATE * dur)
            for j in range(len(tone)):
                t = j / SAMPLE_RATE
                # Bend pitch down by a semitone over the duration
                bend = 1.0 - 0.03 * (t / dur)
                # Also fade out
                fade = 1.0 - 0.5 * (t / dur)
                tone[j] *= fade
        all_samples.extend(tone)
        all_samples.extend(gap)
    return all_samples


def main() -> None:
    import pathlib
    sounds_dir = pathlib.Path(__file__).parent

    fanfare = generate_fanfare()
    out = sounds_dir / "trumpet.wav"
    write_wav(str(out), fanfare)
    print(f"Written to {out}")

    sad = generate_sad_trumpet()
    out_sad = sounds_dir / "sad_trumpet.wav"
    write_wav(str(out_sad), sad)
    print(f"Written to {out_sad}")


if __name__ == "__main__":
    main()
