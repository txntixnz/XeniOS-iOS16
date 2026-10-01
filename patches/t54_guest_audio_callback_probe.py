#!/usr/bin/env python3
"""T54: read-only wall-time probe around Xbox audio guest callback.

No decoder/scheduler/PCM changes. Emits one summary per 1000 callbacks
to separate a slow guest callback from PHASE playback-side instability.
"""
from pathlib import Path
p54 = Path("src/xenia/apu/audio_system.cc")
s54 = p54.read_text()
def replace54(old, new, label):
    global s54
    count = s54.count(old)
    assert count == 1, f"T54 {label}: expected exactly one match, got {count}"
    s54 = s54.replace(old, new, 1)

replace54('#include <cstring>\n',
          '#include <cstring>\n#include <chrono>\n', "chrono")

replace54('''  // Main run loop.
  while (worker_running_) {''',
'''  // T54 only: wall-time spent in the Xbox guest audio callback.
  // These counters belong exclusively to Audio Worker's own thread.
  uint64_t t54_callback_count = 0;
  uint64_t t54_callback_busy_us = 0;
  uint64_t t54_callback_max_us = 0;
  uint64_t t54_callback_gt5333us = 0;
  uint64_t t54_callback_gt10ms = 0;
  uint64_t t54_callback_gt25ms = 0;
  uint64_t t54_probe_start_us = 0;
  auto t54_micros = []() -> uint64_t {
    return static_cast<uint64_t>(
        std::chrono::duration_cast<std::chrono::microseconds>(
            std::chrono::steady_clock::now().time_since_epoch()).count());
  };

  // Main run loop.
  while (worker_running_) {''', "timing state")

replace54('''      if (client_callback) {
        SCOPE_profile_cpu_i("apu", "xe::apu::AudioSystem->client_callback");
        uint64_t args[] = {client_callback_arg};
        processor_->Execute(worker_thread_->thread_state(), client_callback,
                            args, xe::countof(args));
      }''',
'''      if (client_callback) {
        const uint64_t t54_start_us = t54_micros();
        if (!t54_probe_start_us) t54_probe_start_us = t54_start_us;
        SCOPE_profile_cpu_i("apu", "xe::apu::AudioSystem->client_callback");
        uint64_t args[] = {client_callback_arg};
        processor_->Execute(worker_thread_->thread_state(), client_callback,
                            args, xe::countof(args));
        const uint64_t t54_end_us = t54_micros();
        const uint64_t t54_duration_us = t54_end_us - t54_start_us;
        ++t54_callback_count;
        t54_callback_busy_us += t54_duration_us;
        if (t54_duration_us > t54_callback_max_us)
          t54_callback_max_us = t54_duration_us;
        if (t54_duration_us > 5333) ++t54_callback_gt5333us;
        if (t54_duration_us > 10000) ++t54_callback_gt10ms;
        if (t54_duration_us > 25000) ++t54_callback_gt25ms;
        if (t54_callback_count == 1000) {
          XELOGI("[GUEST-AUDIO-DIAG] client={} calls=1000 "
                 "window_ms={} busy_ms={} max_callback_ms={:.2f} "
                 "gt5_33ms={} gt10ms={} gt25ms={}",
                 index, (t54_end_us - t54_probe_start_us) / 1000,
                 t54_callback_busy_us / 1000,
                 static_cast<double>(t54_callback_max_us) / 1000.0,
                 t54_callback_gt5333us, t54_callback_gt10ms,
                 t54_callback_gt25ms);
          t54_callback_count = 0;
          t54_callback_busy_us = 0;
          t54_callback_max_us = 0;
          t54_callback_gt5333us = 0;
          t54_callback_gt10ms = 0;
          t54_callback_gt25ms = 0;
          t54_probe_start_us = 0;
        }
      }''', "callback timing")

p54.write_text(s54)
print("T54 guest audio callback timing patched.")
