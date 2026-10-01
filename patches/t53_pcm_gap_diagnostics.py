#!/usr/bin/env python3
"""T53: read-only PHASE PCM integrity and pacing probe for iOS 16 PGR3.

Keeps all audio sample content, sampling rates, semaphores and renderer behavior
unchanged. Emits only one aggregate line per 1000 submitted audio buffers.
"""
from pathlib import Path

p = Path("src/xenia/apu/phase/phase_audio_driver.mm")
s = p.read_text()

def replace_one(old, new, label):
    global s
    count = s.count(old)
    assert count == 1, f"T53 {label}: expected one match; got {count}"
    s = s.replace(old, new, 1)

replace_one('#include <chrono>\n', '#include <chrono>\n#include <cmath>\n',
            "cmath include")

replace_one(
    '  std::atomic<uint64_t> frames_completed{0};\n',
    '''  std::atomic<uint64_t> frames_completed{0};
  // T53 completion gaps are collected on the PHASE render callback thread.
  std::atomic<uint64_t> t53_last_completion_us{0};
  std::atomic<uint64_t> t53_completion_gap_over_10ms{0};
  std::atomic<uint64_t> t53_completion_gap_over_25ms{0};
''',
    "shared completion counters")

replace_one(
    '  std::atomic<bool> paused{false};\n',
    '''  std::atomic<bool> paused{false};

  // T53 producer timing and read-only PCM statistics; SubmitFrame is serial.
  uint64_t t53_last_submit_us = 0;
  uint64_t t53_submit_gap_over_10ms = 0;
  uint64_t t53_submit_gap_over_25ms = 0;
  uint64_t t53_submit_gap_max_us = 0;
  uint64_t t53_pcm_nonfinite = 0;
  uint64_t t53_pcm_clip_samples = 0;
  uint64_t t53_pcm_boundary_jumps = 0;
  float t53_pcm_peak = 0.0f;
  float t53_last_channel_samples[6] = {};
  bool t53_have_last_frame = false;
''',
    "producer counters")

replace_one(
    '''  AVAudioPCMBuffer* buf = nil;
  size_t pool_free = 0;''',
    '''  // Read-only timing probe: did the Xbox guest supply the next frame late?
  const uint64_t t53_now_us = static_cast<uint64_t>(
      std::chrono::duration_cast<std::chrono::microseconds>(
          std::chrono::steady_clock::now().time_since_epoch()).count());
  if (d->t53_last_submit_us) {
    const uint64_t gap_us = t53_now_us - d->t53_last_submit_us;
    if (gap_us > 10000) ++d->t53_submit_gap_over_10ms;
    if (gap_us > 25000) ++d->t53_submit_gap_over_25ms;
    if (gap_us > d->t53_submit_gap_max_us)
      d->t53_submit_gap_max_us = gap_us;
  }
  d->t53_last_submit_us = t53_now_us;

  AVAudioPCMBuffer* buf = nil;
  size_t pool_free = 0;''',
    "producer timing")

replace_one(
    '''      out[s_i] = xe::byte_swap(src[s_i]) * vol;
    }
  }

  uint64_t submitted''',
    '''      const float pcm = xe::byte_swap(src[s_i]) * vol;
      out[s_i] = pcm;
      // Observe (never modify) what PHASE actually receives.
      if (!std::isfinite(pcm)) {
        ++d->t53_pcm_nonfinite;
      } else {
        const float amplitude = std::fabs(pcm);
        if (amplitude > d->t53_pcm_peak) d->t53_pcm_peak = amplitude;
        if (amplitude > 1.0f) ++d->t53_pcm_clip_samples;
      }
      if (s_i == 0 && d->t53_have_last_frame &&
          std::isfinite(pcm) &&
          std::isfinite(d->t53_last_channel_samples[ch]) &&
          std::fabs(pcm - d->t53_last_channel_samples[ch]) > 0.75f) {
        ++d->t53_pcm_boundary_jumps;
      }
    }
    d->t53_last_channel_samples[ch] = out[n - 1];
  }
  d->t53_have_last_frame = true;

  uint64_t submitted''',
    "PCM sample observation")

replace_one(
    '''  if ((submitted % kHeartbeatFrames) == 0) {
    XELOGI("PHASEAudioDriver: heartbeat''',
    '''  if ((submitted % kHeartbeatFrames) == 0) {
    XELOGI("[PCM-DIAG] submitted={} producer_gap_gt10ms={} producer_gap_gt25ms={} "
           "producer_max_gap_ms={:.2f} completion_gap_gt10ms={} completion_gap_gt25ms={} "
           "nonfinite={} clipped={} boundary_jumps={} peak={:.3f} outstanding={}",
           submitted, d->t53_submit_gap_over_10ms,
           d->t53_submit_gap_over_25ms,
           static_cast<double>(d->t53_submit_gap_max_us) / 1000.0,
           s.t53_completion_gap_over_10ms.exchange(0, std::memory_order_relaxed),
           s.t53_completion_gap_over_25ms.exchange(0, std::memory_order_relaxed),
           d->t53_pcm_nonfinite, d->t53_pcm_clip_samples,
           d->t53_pcm_boundary_jumps, d->t53_pcm_peak,
           s.outstanding.load(std::memory_order_relaxed));
    d->t53_submit_gap_over_10ms = 0;
    d->t53_submit_gap_over_25ms = 0;
    d->t53_submit_gap_max_us = 0;
    d->t53_pcm_nonfinite = 0;
    d->t53_pcm_clip_samples = 0;
    d->t53_pcm_boundary_jumps = 0;
    d->t53_pcm_peak = 0.0f;
    XELOGI("PHASEAudioDriver: heartbeat''',
    "periodic report")

replace_one(
    '''               (void)condition;
               {
                 std::lock_guard<std::mutex> lock(shared->mutex);''',
    '''               (void)condition;
               const uint64_t callback_us = static_cast<uint64_t>(
                   std::chrono::duration_cast<std::chrono::microseconds>(
                       std::chrono::steady_clock::now().time_since_epoch()).count());
               const uint64_t previous_us =
                   shared->t53_last_completion_us.exchange(
                       callback_us, std::memory_order_relaxed);
               if (previous_us && callback_us > previous_us) {
                 const uint64_t delta_us = callback_us - previous_us;
                 if (delta_us > 10000)
                   shared->t53_completion_gap_over_10ms.fetch_add(
                       1, std::memory_order_relaxed);
                 if (delta_us > 25000)
                   shared->t53_completion_gap_over_25ms.fetch_add(
                       1, std::memory_order_relaxed);
               }
               {
                 std::lock_guard<std::mutex> lock(shared->mutex);''',
    "completion timing")

p.write_text(s)
print("T53 PCM and producer/completion gap diagnostics patched.")
